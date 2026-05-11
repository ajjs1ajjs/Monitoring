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
        
        # Optimization: History Buffer
        self._history_buffer = []
        self._service_history_buffer = []
        self._buffer_lock = asyncio.Lock()
        
        # Prometheus Metrics
        self.scrape_total = Counter("pymon_scrape_total", "Total scrape attempts")
        self.scrape_success = Counter("pymon_scrape_success_total", "Successful scrapes")
        self.scrape_failures = Counter("pymon_scrape_failures_total", "Failed scrapes")
        self.up_gauge = Gauge("up", "Target availability (1=up, 0=down)")
        self.response_time = Gauge("pymon_response_time_seconds", "Response time in seconds")
        
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        
        # Flapping & State
        self._last_states: dict[int, str] = {} # {server_id: status}
        self._flapping_threshold = 3
        self._history_points: dict[int, dict] = {} # {sid: {"cpu": [], "mem": []}}
        
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
        
        self._tasks.append(asyncio.create_task(self._service_monitoring_loop()))
        self._tasks.append(asyncio.create_task(self._flush_buffer_loop()))
        
        logger.info("ScrapeManager started (Enhanced: Services, Maintenance, Flapping)")

    async def stop(self):
        self._running = False
        # Final flush
        await self._flush_history()
        
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._client.aclose()
        logger.info("ScrapeManager stopped")

    async def _load_dynamic_targets(self):
        """Load servers from DB as scrape targets if not in config"""
        db_path = self.config.storage.path
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
                    interval=self.config.global_config.scrape_interval if hasattr(self.config, "global_config") else 15,
                    timeout=self.config.global_config.scrape_timeout if hasattr(self.config, "global_config") else 10,
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
        # Version detection
        version = "unknown"
        
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if "_exporter_build_info{" in line:
                v_match = re.search(r'version="([^"]+)"', line)
                if v_match: version = v_match.group(1)

            try:
                # Basic Prometheus parser
                if "{" in line:
                    name, rest = line.split("{", 1)
                    labels_part, val_str = rest.rsplit("}", 1)
                    name = name.strip()
                    val = float(val_str.strip())
                    metrics[line] = val 
                    metrics[name] = val 
                else:
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics[parts[0]] = float(parts[1])
            except:
                continue
        
        metrics["__version__"] = version
        return metrics

    async def _update_server_status(self, target: ScrapeTarget, result: ScrapeResult, success: bool):
        db_path = self.config.storage.path
        try:
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Find server info
            sid = target.server_id
            if not sid:
                row = c.execute("SELECT id, is_maintenance, flapping_count, last_status FROM servers WHERE host = ?", (target.target.split(':')[0],)).fetchone()
                if row: 
                    sid = row['id']
                    is_maintenance = row['is_maintenance']
                else: is_maintenance = 0
            else:
                row = c.execute("SELECT is_maintenance, flapping_count, last_status FROM servers WHERE id = ?", (sid,)).fetchone()
                is_maintenance = row['is_maintenance'] if row else 0

            now_iso = datetime.now(timezone.utc).isoformat()
            
            if success:
                # Extract core metrics
                m = result.metrics or {}
                version = m.get("__version__", "unknown")
                
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
                             cpu_percent = ?, memory_percent = ?, disk_percent = 0,
                             network_rx = ?, network_tx = ?, disk_info = ?, exporter_version = ?, flapping_count = 0
                             WHERE id = ?""",
                          (now_iso, cpu, mem, rx, tx, json.dumps(disk_info_final), version, sid))
                
                async with self._buffer_lock:
                    self._history_buffer.append((sid, cpu, mem, 0, rx, tx, json.dumps(disk_info_final), now_iso))
                
                if not is_maintenance:
                    await self._detect_anomalies(sid, cpu, mem, target.labels.get("name", target.target))
                    await self._check_alerts(sid, cpu, mem, 0, target.labels.get("name", target.target))
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
                # Flapping detection
                prev_status = self._last_states.get(sid, 'unknown')
                cur_status = 'down'
                if prev_status == 'up' and cur_status == 'down':
                    c.execute("UPDATE servers SET flapping_count = flapping_count + 1 WHERE id = ?", (sid,))
                
                c.execute("UPDATE servers SET last_check = ?, last_status = 'down', error_message = ? WHERE id = ?",
                          (now_iso, result.error, sid))
                
                if not is_maintenance and sid not in self._down_alerted:
                    # Check flapping threshold from DB
                    row = c.execute("SELECT flapping_count FROM servers WHERE id = ?", (sid,)).fetchone()
                    if row and row[0] < self._flapping_threshold:
                        self._down_alerted.add(sid)
                        await self._fire_down_alert(sid, target.labels.get("name", target.target), result.error)

            self._last_states[sid] = 'up' if success else 'down'

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating status: {e}")

    async def _service_monitoring_loop(self):
        """Monitor HTTP/TCP services independently"""
        while self._running:
            db_path = self.config.storage.path
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                services = conn.execute("SELECT * FROM services WHERE enabled = 1").fetchall()
                conn.close()
                
                for s in services:
                    asyncio.create_task(self._check_service(s))
            except: pass
            await asyncio.sleep(60)

    async def _check_service(self, s: sqlite3.Row):
        start = time.time()
        success = False
        error = ""
        resp_time = 0
        
        try:
            if s['check_type'] == 'http':
                resp = await self._client.get(s['target_url'], timeout=s['timeout'])
                success = (resp.status_code < 400)
                resp_time = (time.time() - start) * 1000
                if not success: error = f"HTTP {resp.status_code}"
            else: # TCP
                host_port = s['target_url'].replace('http://', '').replace('https://', '')
                if ':' in host_port:
                    host, port = host_port.split(':')
                else:
                    host, port = host_port, 80
                _, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port)), timeout=s['timeout'])
                writer.close()
                await writer.wait_closed()
                success = True
                resp_time = (time.time() - start) * 1000
        except Exception as e:
            error = str(e)
            resp_time = (time.time() - start) * 1000

        db_path = self.config.storage.path
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.execute("""UPDATE services SET last_status = ?, last_check = ?, last_response_time = ?, 
                            error_message = ? WHERE id = ?""",
                         ('up' if success else 'down', datetime.now(timezone.utc).isoformat(), resp_time, error, s['id']))
            if not success and s['is_maintenance'] == 0:
                await self._fire_down_alert(999000 + s['id'], f"Service: {s['name']}", error)
            
            if s['is_maintenance'] == 0:
                await self._check_service_alerts(s['id'], resp_time, 'up' if success else 'down', s['name'])
            
            async with self._buffer_lock:
                self._service_history_buffer.append((s['id'], 'up' if success else 'down', resp_time, datetime.now(timezone.utc).isoformat()))
            
            conn.commit()
            conn.close()
        except: pass

    async def _flush_buffer_loop(self):
        while self._running:
            await asyncio.sleep(10)
            await self._flush_history()

    async def _flush_history(self):
        async with self._buffer_lock:
            if not self._history_buffer:
                return
            batch = self._history_buffer[:]
            self._history_buffer.clear()
            
        db_path = self.config.storage.path
        try:
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=30)
            c = conn.cursor()
            c.executemany("""INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, 
                             network_rx, network_tx, disk_info, timestamp) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", batch)
            
            c.execute(f"DELETE FROM metrics_history WHERE timestamp < datetime('now', '-{retention_h} hours')")
            
            # Flush service history
            async with self._buffer_lock:
                s_batch = self._service_history_buffer[:]
                self._service_history_buffer.clear()
            
            if s_batch:
                c.executemany("INSERT INTO services_history (service_id, status, response_time, timestamp) VALUES (?, ?, ?, ?)", s_batch)
                c.execute(f"DELETE FROM services_history WHERE timestamp < datetime('now', '-{retention_h} hours')")

            conn.commit()
            conn.close()
            logger.debug(f"Flushed {len(batch)} node and {len(s_batch)} service history records to DB")
        except Exception as e:
            logger.error(f"Failed to flush history buffer: {e}")

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
        db_path = self.config.storage.path
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

    async def _check_service_alerts(self, service_id: int, latency: float, status: str, name: str):
        db_path = self.config.storage.path
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            alerts = conn.execute("SELECT * FROM alerts WHERE enabled = 1 AND (service_id = ? OR (service_id IS NULL AND server_id IS NULL AND metric LIKE 'service_%'))", (service_id,)).fetchall()
            
            notif_row = conn.execute("SELECT config FROM notifications WHERE channel = 'all'").fetchone()
            notif_cfg = json.loads(notif_row[0]) if notif_row else {"enabled": False}
            
            for alert in alerts:
                triggered = False
                val = 0.0
                if alert['metric'] == 'service_latency':
                    val = latency
                    if alert['condition'] == '>': triggered = val > alert['threshold']
                    elif alert['condition'] == '<': triggered = val < alert['threshold']
                elif alert['metric'] == 'service_status':
                    val = 1 if status == 'up' else 0
                    if alert['condition'] == '==': triggered = val == alert['threshold']
                    elif alert['condition'] == '!=': triggered = val != alert['threshold']
                
                if triggered:
                    msg = f"🚨 <b>{alert['name']}</b> on <b>{name}</b>\nValue: {val:.1f}\nThreshold: {alert['threshold']}"
                    if notif_cfg.get('enabled'):
                        dispatcher.dispatch(alert['name'], msg, notif_cfg)
                    
                    conn.execute("INSERT INTO audit_logs (username, action, target, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                                ("system", f"Alert: {alert['name']}", name, f"Value: {val:.1f}", datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Service alert check failed for {name}: {e}")

    async def _detect_anomalies(self, sid: int, cpu: float, mem: float, name: str):
        if sid not in self._history_points:
            self._history_points[sid] = {"cpu": [], "mem": []}
        
        hist = self._history_points[sid]
        
        # Check CPU Anomaly (Spike > 40% over average of last 10 points)
        if len(hist["cpu"]) >= 5:
            avg_cpu = sum(hist["cpu"]) / len(hist["cpu"])
            if cpu > avg_cpu + 40 and cpu > 20: # Must be a significant jump
                await self._fire_anomaly_alert(name, "CPU Spike", f"Jump from {avg_cpu:.1f}% to {cpu:.1f}%")
        
        # Check RAM Anomaly (Sudden increase > 20%)
        if len(hist["mem"]) >= 5:
            avg_mem = sum(hist["mem"]) / len(hist["mem"])
            if mem > avg_mem + 20:
                await self._fire_anomaly_alert(name, "Memory Leak / Surge", f"Jump from {avg_mem:.1f}% to {mem:.1f}%")

        # Update history
        hist["cpu"].append(cpu)
        hist["mem"].append(mem)
        if len(hist["cpu"]) > 15: hist["cpu"].pop(0)
        if len(hist["mem"]) > 15: hist["mem"].pop(0)

    async def _fire_anomaly_alert(self, target_name: str, type: str, details: str):
        logger.warning(f"Anomaly detected on {target_name}: {type} - {details}")
        db_path = self.config.storage.path
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.execute("INSERT INTO audit_logs (username, action, target, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                         ("system", f"Anomaly: {type}", target_name, details, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            conn.close()
        except: pass

    async def _fire_down_alert(self, sid: int, name: str, error: str):
        db_path = self.config.storage.path
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
