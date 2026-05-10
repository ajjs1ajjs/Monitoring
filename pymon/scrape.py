import asyncio
import json
import time
import os
import sqlite3
import re
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any

import httpx

from pymon.config import PyMonConfig
from pymon.metrics.collector import Counter, Gauge, Histogram, registry
from pymon.metrics.models import Label, MetricType, Metric
from pymon.storage import get_storage
from pymon.notifications import dispatcher

logger = logging.getLogger(__name__)

@dataclass
class ScrapeTarget:
    job_name: str
    target: str
    metrics_path: str
    interval: int
    timeout: int
    labels: dict[str, str]
    server_id: Optional[int] = None
    honor_labels: bool = False

@dataclass
class ScrapeResult:
    target: ScrapeTarget
    success: bool
    status_code: int = 0
    latency_ms: float = 0
    error: str = ""
    metrics: dict | None = None
    timestamp: datetime | None = None

class ScrapeManager:
    def __init__(self, config: PyMonConfig):
        self.config = config
        self.targets: list[ScrapeTarget] = []
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._down_alerted: set[int] = set()
        self._prev_metrics: dict[int, dict] = {} # {server_id: {timestamp: float, metrics: dict}}
        
        # Prometheus Metrics
        self.scrape_total = Counter("pymon_scrape_total", "Total scrape attempts")
        self.scrape_success = Counter("pymon_scrape_success_total", "Successful scrapes")
        self.scrape_failures = Counter("pymon_scrape_failures_total", "Failed scrapes")
        self.up_gauge = Gauge("up", "Target availability (1=up, 0=down)")
        self.response_time = Gauge("pymon_response_time_seconds", "Response time in seconds")
        
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._build_targets()

    def _build_targets(self):
        self.targets = []
        for scrape_config in self.config.scrape_configs:
            for static_config in scrape_config.static_configs:
                for target in static_config.targets:
                    self.targets.append(
                        ScrapeTarget(
                            job_name=scrape_config.job_name,
                            target=target,
                            metrics_path=scrape_config.metrics_path,
                            interval=scrape_config.scrape_interval,
                            timeout=scrape_config.scrape_timeout,
                            labels={**static_config.labels, "job": scrape_config.job_name},
                            honor_labels=scrape_config.honor_labels,
                        )
                    )
        logger.info(f"ScrapeManager: {len(self.targets)} targets configured")

    async def start(self):
        if self._running:
            return
        self._running = True
        
        # Also load dynamic targets from DB
        await self._load_dynamic_targets()
        
        for target in self.targets:
            task = asyncio.create_task(self._scrape_loop(target))
            self._tasks.append(task)
        logger.info("ScrapeManager started (Async mode)")

    async def stop(self):
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._client.aclose()
        logger.info("ScrapeManager stopped")

    async def _load_dynamic_targets(self):
        """Load servers from DB as scrape targets if not in config"""
        db_path = os.getenv("DB_PATH", "pymon.db")
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM servers WHERE enabled = 1").fetchall()
            for r in rows:
                target_str = f"{r['host']}:{r['agent_port']}"
                # Avoid duplicates
                if any(t.target == target_str for t in self.targets):
                    continue
                    
                self.targets.append(ScrapeTarget(
                    job_name="dynamic_servers",
                    target=target_str,
                    metrics_path="/metrics",
                    interval=self.config.global_config.scrape_interval,
                    timeout=self.config.global_config.scrape_timeout,
                    labels={"server_id": str(r['id']), "name": r['name']},
                    server_id=r['id']
                ))
            conn.close()
        except Exception as e:
            logger.error(f"Error loading dynamic targets: {e}")

    async def _scrape_loop(self, target: ScrapeTarget):
        while self._running:
            start_time = asyncio.get_event_loop().time()
            try:
                await self.execute_scrape(target)
            except Exception as e:
                logger.error(f"Scrape loop error for {target.target}: {e}")
            
            elapsed = asyncio.get_event_loop().time() - start_time
            sleep_time = max(0, target.interval - elapsed)
            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break

    async def execute_scrape(self, target: ScrapeTarget):
        result = await self.scrape_target(target)
        self.scrape_total.inc()
        
        labels = [Label(name="job", value=target.job_name), Label(name="target", value=target.target)]
        
        if result.success:
            self.scrape_success.inc()
            self.up_gauge.set(1, labels)
            await self._update_server_status(target, result, True)
        else:
            self.scrape_failures.inc()
            self.up_gauge.set(0, labels)
            await self._update_server_status(target, result, False)
            
        self.response_time.set(result.latency_ms / 1000, labels)

    async def scrape_target(self, target: ScrapeTarget) -> ScrapeResult:
        result = ScrapeResult(target=target, success=False, timestamp=datetime.now(timezone.utc), metrics={})
        
        url = target.target
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        if not url.endswith(target.metrics_path):
            url = url.rstrip("/") + target.metrics_path
            
        start_ts = time.time()
        try:
            resp = await self._client.get(url, timeout=target.timeout)
            result.latency_ms = (time.time() - start_ts) * 1000
            result.status_code = resp.status_code
            result.success = (resp.status_code == 200)
            
            if result.success:
                result.metrics = self._parse_metrics(resp.text)
        except Exception as e:
            result.error = str(e)
            result.latency_ms = (time.time() - start_ts) * 1000
            
        return result

    def _parse_metrics(self, text: str) -> dict:
        metrics = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            try:
                # Basic Prometheus parser
                if "{" in line:
                    name, rest = line.split("{", 1)
                    labels_part, val_str = rest.rsplit("}", 1)
                    name = name.strip()
                    val = float(val_str.strip())
                    # We store raw line as key for complex metrics or parse labels
                    # For summary logic, we need specific keys
                    metrics[line] = val # Store full line for regex matching later
                    metrics[name] = val # Also store base name
                else:
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics[parts[0]] = float(parts[1])
            except:
                continue
        return metrics

    async def _update_server_status(self, target: ScrapeTarget, result: ScrapeResult, success: bool):
        db_path = os.getenv("DB_PATH", "pymon.db")
        try:
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Find server_id if not known
            sid = target.server_id
            if not sid:
                row = c.execute("SELECT id FROM servers WHERE host = ?", (target.target.split(':')[0],)).fetchone()
                if row: sid = row['id']
            
            if not sid:
                conn.close()
                return

            now_iso = datetime.now(timezone.utc).isoformat()
            
            if success:
                # Extract core metrics
                m = result.metrics or {}
                
                # CPU Calculation (Handling deltas for node_exporter)
                cpu = self._find_metric(m, ["node_cpu_calculated", "windows_cpu_usage", "cpu_usage"])
                
                if not cpu:
                    # Linux node_exporter (node_cpu_seconds_total)
                    idle_now = self._sum_metrics(m, r'node_cpu_seconds_total{.*mode="idle".*}')
                    total_now = self._sum_metrics(m, r'node_cpu_seconds_total{.*}')
                    
                    # Windows windows_exporter (windows_cpu_time_total)
                    if total_now == 0:
                        idle_now = self._sum_metrics(m, r'windows_cpu_time_total{.*mode="idle".*}')
                        total_now = self._sum_metrics(m, r'windows_cpu_time_total{.*}')

                    if total_now > 0:
                        prev = self._prev_metrics.get(sid)
                        if prev:
                            idle_delta = idle_now - prev.get('idle', 0)
                            total_delta = total_now - prev.get('total', 0)
                            if total_delta > 0:
                                cpu = 100 * (1 - idle_delta / total_delta)
                        
                        # Store for next run
                        self._prev_metrics[sid] = {'idle': idle_now, 'total': total_now}

                mem = self._find_metric(m, ["node_memory_calculated", "windows_memory_usage", "memory_usage"])
                if not mem:
                    total = self._find_metric(m, ["node_memory_MemTotal_bytes", "windows_cs_physical_memory_bytes"])
                    free = self._find_metric(m, ["node_memory_MemAvailable_bytes", "windows_os_physical_memory_free_bytes"])
                    if total > 0: mem = 100 * (1 - free / total)
                
                disk = self._find_metric(m, ["node_disk_calculated", "windows_disk_usage", "disk_usage"])
                
                # Disk Breakdown
                disk_info = {}
                # Node Exporter
                for k, v in m.items():
                    if "node_filesystem_size_bytes" in k:
                        match = re.search(r'mountpoint="([^"]+)"', k)
                        if match:
                            mnt = match.group(1)
                            if not any(x in mnt for x in ["/proc", "/sys", "/dev", "/run", "/var/lib/docker"]):
                                if mnt not in disk_info: disk_info[mnt] = {"volume": mnt, "size": v, "free": 0}
                                else: disk_info[mnt]["size"] = v
                    if "node_filesystem_free_bytes" in k:
                        match = re.search(r'mountpoint="([^"]+)"', k)
                        if match:
                            mnt = match.group(1)
                            if mnt in disk_info: disk_info[mnt]["free"] = v
                # Windows Exporter
                for k, v in m.items():
                    if "windows_logical_disk_size_bytes" in k:
                        match = re.search(r'volume="([^"]+)"', k)
                        if match:
                            vol = match.group(1)
                            if vol not in disk_info: disk_info[vol] = {"volume": vol, "size": v, "free": 0}
                            else: disk_info[vol]["size"] = v
                    if "windows_logical_disk_free_bytes" in k:
                        match = re.search(r'volume="([^"]+)"', k)
                        if match:
                            vol = match.group(1)
                            if vol in disk_info: disk_info[vol]["free"] = v

                # Convert to percent for dashboard
                disk_info_final = []
                for vol, data in disk_info.items():
                    if data["size"] > 0:
                        pct = 100 * (1 - data["free"] / data["size"])
                        disk_info_final.append({"volume": vol, "percent": pct})
                
                if not disk and disk_info_final:
                    disk = sum(d["percent"] for d in disk_info_final) / len(disk_info_final)

                rx = self._sum_metrics(m, r'.*network_receive_bytes.*|.*network_rx_bytes.*')
                tx = self._sum_metrics(m, r'.*network_transmit_bytes.*|.*network_tx_bytes.*')
                
                c.execute("""UPDATE servers SET 
                             last_check = ?, last_status = 'up', error_message = NULL,
                             cpu_percent = ?, memory_percent = ?, disk_percent = ?,
                             network_rx = ?, network_tx = ?, disk_info = ?
                             WHERE id = ?""",
                          (now_iso, cpu, mem, disk, rx, tx, json.dumps(disk_info_final), sid))
                
                # History
                c.execute("""INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, 
                             network_rx, network_tx, disk_info, timestamp) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                          (sid, cpu, mem, disk, rx, tx, json.dumps(disk_info_final), now_iso))
                
                # Check Alerts
                await self._check_alerts(sid, cpu, mem, disk, target.labels.get("name", target.target))
                self._down_alerted.discard(sid)
                
                # Broadcast
                try:
                    from pymon.api.deps import manager
                    if manager.loop:
                        asyncio.run_coroutine_threadsafe(
                            manager.broadcast({"type": "server_update", "server_id": sid, "cpu": cpu, "memory": mem, "status": "up"}),
                            manager.loop
                        )
                except: pass

            else:
                c.execute("UPDATE servers SET last_check = ?, last_status = 'down', error_message = ? WHERE id = ?",
                          (now_iso, result.error, sid))
                if sid not in self._down_alerted:
                    self._down_alerted.add(sid)
                    await self._fire_down_alert(sid, target.labels.get("name", target.target), result.error)

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating status for {target.target}: {e}")

    def _find_metric(self, metrics: dict, keys: list) -> float:
        for k in keys:
            if k in metrics: return metrics[k]
        return 0.0

    def _sum_metrics(self, metrics: dict, pattern: str) -> float:
        total = 0.0
        regex = re.compile(pattern)
        for k, v in metrics.items():
            if regex.match(k):
                total += v
        return total

    async def _check_alerts(self, sid: int, cpu: float, mem: float, disk: float, name: str):
        db_path = os.getenv("DB_PATH", "pymon.db")
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            alerts = conn.execute("SELECT * FROM alerts WHERE enabled = 1 AND (server_id IS NULL OR server_id = ?)", (sid,)).fetchall()
            
            # Load notification config
            notif_row = conn.execute("SELECT config FROM notifications WHERE channel = 'all'").fetchone()
            notif_cfg = json.loads(notif_row[0]) if notif_row else {"enabled": False}
            
            for alert in alerts:
                triggered = False
                val = 0.0
                if alert['metric'] == 'cpu': val = cpu
                elif alert['metric'] == 'memory': val = mem
                elif alert['metric'] == 'disk': val = disk
                
                if alert['condition'] == '>': triggered = val > alert['threshold']
                elif alert['condition'] == '<': triggered = val < alert['threshold']
                elif alert['condition'] == '==': triggered = abs(val - alert['threshold']) < 0.1
                
                if triggered:
                    msg = f"🚨 <b>{alert['name']}</b> triggered on <b>{name}</b>\nValue: {val:.1f}%\nThreshold: {alert['threshold']}%"
                    if notif_cfg.get('enabled'):
                        dispatcher.dispatch(alert['name'], msg, notif_cfg)
                    
                    # Log to audit
                    conn.execute("INSERT INTO audit_logs (username, action, target, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                                ("system", f"Alert: {alert['name']}", name, f"Value: {val:.1f}%", datetime.now(timezone.utc).isoformat()))
            
            # Periodic cleanup: Keep only 7 days of history
            conn.execute("DELETE FROM metrics_history WHERE timestamp < datetime('now', '-7 days')")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Alert check failed for {name}: {e}")

    async def _fire_down_alert(self, sid: int, name: str, error: str):
        db_path = os.getenv("DB_PATH", "pymon.db")
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            notif_row = conn.execute("SELECT config FROM notifications WHERE channel = 'all'").fetchone()
            notif_cfg = json.loads(notif_row[0]) if notif_row else {"enabled": False}
            
            msg = f"🔴 <b>Target DOWN</b>: <b>{name}</b>\nError: {error or 'Connection Timeout'}"
            if notif_cfg.get('enabled'):
                dispatcher.dispatch("Target Down", msg, notif_cfg)
                
            conn.execute("INSERT INTO audit_logs (username, action, target, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                        ("system", "Target Down", name, f"Error: {error}", datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Down alert failed for {name}: {e}")
