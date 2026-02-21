"""Scrape manager for collecting metrics from targets (Prometheus-style)"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

from pymon.config import PyMonConfig, ScrapeConfig, StaticConfig
from pymon.metrics.collector import Counter, Gauge, Histogram, registry
from pymon.metrics.models import Label
from pymon.storage import get_storage


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
    metrics_count: int = 0
    metrics: dict | None = None
    timestamp: datetime | None = None


class ScrapeManager:
    def __init__(self, config: PyMonConfig):
        self.config = config
        self.targets: list[ScrapeTarget] = []
        self._running = False
        self._tasks = []
        
        self.scrape_total = Counter("pymon_scrape_total", "Total scrape attempts")
        self.scrape_success = Counter("pymon_scrape_success_total", "Successful scrapes")
        self.scrape_failures = Counter("pymon_scrape_failures_total", "Failed scrapes")
        self.scrape_duration = Histogram("pymon_scrape_duration_seconds", "Scrape duration")
        self.up_gauge = Gauge("up", "Target availability (1=up, 0=down)")
        self.response_time = Gauge("pymon_response_time_seconds", "Response time in seconds")
        
        self._client = httpx.AsyncClient(timeout=30.0)
        self._build_targets()

    def _build_targets(self):
        for scrape_config in self.config.scrape_configs:
            for static_config in scrape_config.static_configs:
                for target in static_config.targets:
                    self.targets.append(ScrapeTarget(
                        job_name=scrape_config.job_name,
                        target=target,
                        metrics_path=scrape_config.metrics_path,
                        interval=scrape_config.scrape_interval,
                        timeout=scrape_config.scrape_timeout,
                        labels={**static_config.labels, "job": scrape_config.job_name},
                        honor_labels=scrape_config.honor_labels,
                    ))
        
        print(f"ScrapeManager: {len(self.targets)} targets configured")

    async def scrape_target(self, target: ScrapeTarget) -> ScrapeResult:
        result = ScrapeResult(
            target=target,
            success=False,
            timestamp=datetime.now(timezone.utc),
            metrics={}
        )
        
        try:
            if target.target.startswith(("http://", "https://")):
                url = target.target
                if not url.endswith(target.metrics_path):
                    url = url.rstrip("/") + target.metrics_path
            else:
                url = f"http://{target.target}{target.metrics_path}"
            
            start_time = time.time()
            
            response = await self._client.get(
                url,
                timeout=target.timeout,
                follow_redirects=True,
            )
            
            result.latency_ms = (time.time() - start_time) * 1000
            result.status_code = response.status_code
            result.success = response.status_code == 200
            
            if result.success:
                content_type = response.headers.get("content-type", "")
                if "text/plain" in content_type or "application/openmetrics" in content_type:
                    result.metrics = await self._parse_prometheus_response(
                        response.text, target
                    )
                    result.metrics_count = len(result.metrics)
            
        except httpx.TimeoutException:
            result.error = "timeout"
        except httpx.ConnectError:
            result.error = "connection_refused"
        except Exception as e:
            result.error = str(e)[:100]
        
        return result

    async def _parse_prometheus_response(self, content: str, target: ScrapeTarget) -> dict:
        metrics = {}
        storage = get_storage()
        
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            try:
                if "{" in line:
                    name_part, value_part = line.split("{", 1)
                    labels_part, value = value_part.rsplit("}", 1)
                    name = name_part.strip()
                    value = float(value.strip())
                    
                    labels = list(target.labels.items()) if not target.honor_labels else []
                    for label_str in labels_part.split(","):
                        if "=" in label_str:
                            lname, lvalue = label_str.split("=", 1)
                            lvalue = lvalue.strip('"')
                            labels.append((lname.strip(), lvalue))
                else:
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        value = float(parts[1])
                        labels = list(target.labels.items()) if not target.honor_labels else []
                    else:
                        continue
                
                metrics[name] = value
                
                label_objs = [Label(name=k, value=v) for k, v in labels]
                from pymon.metrics.models import MetricType
                registry.register(name, MetricType.GAUGE, "", label_objs)
                registry.set(name, value, label_objs)
                
                from pymon.metrics.models import Metric, MetricType
                metric = Metric(
                    name=name,
                    value=value,
                    metric_type=MetricType.GAUGE,
                    labels=label_objs,
                )
                await storage.write(metric)
                
            except Exception:
                continue
        
        return metrics

    def _update_server_status(self, target: str, metrics: dict, success: bool, error: str = "", server_id: Optional[int] = None):
        import sqlite3
        import os
        
        try:
            db_path = os.getenv("DB_PATH", "pymon.db")
            conn = sqlite3.connect(db_path, timeout=5)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            sid = None
            if server_id:
                sid = server_id
            else:
                server = c.execute("SELECT id FROM servers WHERE host = ? OR host LIKE ?", 
                                  (target, f"{target}%")).fetchone()
                if server:
                    sid = server['id']

            if sid:
                now = datetime.now(timezone.utc).isoformat()
                
                if success:
                    # Parse CPU - support both node_exporter and windows_exporter
                    cpu = metrics.get('node_cpu_percent') or metrics.get('cpu_usage_percent') or 0
                    if not cpu:
                        idle = metrics.get('windows_cpu_time_total_idle', 0)
                        total = metrics.get('windows_cpu_time_total_all', 0)
                        if total > 0:
                            cpu = 100 * (1 - idle / total) if idle < total else 0
                    
                    # Parse Memory - support both node_exporter and windows_exporter
                    memory = metrics.get('node_memory_percent') or metrics.get('memory_usage_percent') or 0
                    if not memory:
                        mem_total = metrics.get('windows_cs_physical_memory_bytes', 0)
                        mem_free = metrics.get('windows_os_physical_memory_free_bytes', 0)
                        if mem_total > 0:
                            memory = 100 * (1 - mem_free / mem_total) if mem_free < mem_total else 0
                    
                    # Parse Disk - support both node_exporter and windows_exporter
                    disk = metrics.get('node_disk_percent') or metrics.get('disk_usage_percent') or 0
                    if not disk:
                        disk_total = metrics.get('windows_logical_disk_size_bytes', 0)
                        disk_free = metrics.get('windows_logical_disk_free_bytes', 0)
                        if disk_total > 0:
                            disk = 100 * (1 - disk_free / disk_total) if disk_free < disk_total else 0
                    
                    network_rx = metrics.get('node_network_receive_bytes') or metrics.get('node_network_receive_bytes_total') or metrics.get('system_network_rx_bytes', 0)
                    network_tx = metrics.get('node_network_transmit_bytes') or metrics.get('node_network_transmit_bytes_total') or metrics.get('system_network_tx_bytes', 0)
                    uptime = metrics.get('node_boot_time_seconds') or metrics.get('system_uptime_seconds') or metrics.get('windows_system_system_up_time', '')
                    disk_info_json = metrics.get('_disk_info_json')
                    
                    c.execute('''UPDATE servers SET 
                        last_check = ?, last_status = 'up',
                        cpu_percent = ?, memory_percent = ?, disk_percent = ?,
                        network_rx = ?, network_tx = ?, uptime = ?, disk_info = ?
                        WHERE id = ?''',
                        (now, cpu, memory, disk, network_rx, network_tx, str(uptime), disk_info_json, sid))
                else:
                    c.execute('''UPDATE servers SET 
                        last_check = ?, last_status = 'down'
                        WHERE id = ?''', (now, sid))
                
                conn.commit()
            
            conn.close()
        except Exception as e:
            print(f"Error updating server status: {e}")

    async def _scrape_loop(self, target: ScrapeTarget):
        while self._running:
            try:
                result = await self.scrape_target(target)
                
                self.scrape_total.inc()
                
                labels = [Label(name="job", value=target.job_name), Label(name="target", value=target.target)]
                
                if result.success:
                    self.scrape_success.inc()
                    self.up_gauge.set(1, labels)
                    self._update_server_status(target.target, result.metrics or {}, True)
                else:
                    self.scrape_failures.inc()
                    self.up_gauge.set(0, labels)
                    self._update_server_status(target.target, {}, False, result.error)
                    print(f"Scrape failed: {target.target} - {result.error}")
                
                self.response_time.set(result.latency_ms / 1000, labels)
                
            except Exception as e:
                print(f"Scrape error for {target.target}: {e}")
                self._update_server_status(target.target, {}, False, str(e))
            
            # Sleep outside try block to avoid issues
            try:
                await asyncio.sleep(target.interval)
            except asyncio.CancelledError:
                break

    def start(self):
        if self._running:
            return
        
        self._running = True
        
        # Use threading instead of asyncio tasks to avoid blocking the main event loop
        import threading
        
        for target in self.targets:
            thread = threading.Thread(target=self._scrape_thread, args=(target,), daemon=True)
            thread.start()
            self._tasks.append(thread)
        
        print(f"ScrapeManager started with {len(self.targets)} targets (threaded)")
    
    def _scrape_thread(self, target: ScrapeTarget):
        """Run scrape loop in a separate thread using synchronous httpx"""
        import httpx
        import time
        from datetime import datetime
        
        client = httpx.Client(timeout=target.timeout)
        
        while self._running:
            try:
                if target.target.startswith(("http://", "https://")):
                    url = target.target
                    if not url.endswith(target.metrics_path):
                        url = url.rstrip("/") + target.metrics_path
                else:
                    url = f"http://{target.target}{target.metrics_path}"
                
                start_time = time.time()
                response = client.get(url)
                latency_ms = (time.time() - start_time) * 1000
                
                self.scrape_total.inc()
                labels = [Label(name="job", value=target.job_name), Label(name="target", value=target.target)]
                
                if response.status_code == 200:
                    self.scrape_success.inc()
                    self.up_gauge.set(1, labels)
                    
                    # Parse metrics - support both node_exporter and windows_exporter
                    metrics = {}
                    cpu_idle_total = 0
                    cpu_all_total = 0
                    disk_info = {}
                    
                    for line in response.text.split("\n"):
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        try:
                            if "{" in line:
                                name_part, rest = line.split("{", 1)
                                labels_part, value_str = rest.rsplit("}", 1)
                                name = name_part.strip()
                                value = float(value_str.strip())
                                
                                # Aggregate CPU idle time from windows_exporter
                                if name == 'windows_cpu_time_total':
                                    if 'mode="idle"' in labels_part:
                                        cpu_idle_total += value
                                    cpu_all_total += value
                                
                                # Collect ALL disks from windows_exporter
                                import re
                                if name == 'windows_logical_disk_free_bytes':
                                    vol_match = re.search(r'volume="([^"]+)"', labels_part)
                                    if vol_match:
                                        vol = vol_match.group(1)
                                        if vol not in disk_info:
                                            disk_info[vol] = {'volume': vol, 'free': 0, 'size': 0}
                                        disk_info[vol]['free'] = value
                                if name == 'windows_logical_disk_size_bytes':
                                    vol_match = re.search(r'volume="([^"]+)"', labels_part)
                                    if vol_match:
                                        vol = vol_match.group(1)
                                        if vol not in disk_info:
                                            disk_info[vol] = {'volume': vol, 'free': 0, 'size': 0}
                                        disk_info[vol]['size'] = value
                                
                                metrics[name] = value
                            else:
                                parts = line.split()
                                if len(parts) >= 2:
                                    name = parts[0]
                                    value = float(parts[1])
                                    metrics[name] = value
                        except:
                            continue
                    
                    # Store aggregated values
                    if cpu_idle_total > 0:
                        metrics['windows_cpu_time_total_idle'] = cpu_idle_total
                        metrics['windows_cpu_time_total_all'] = cpu_all_total
                    
                    # Calculate disk percentages and get C: for main metric
                    disks_list = []
                    for vol, info in disk_info.items():
                        if info['size'] > 0:
                            info['percent'] = 100 * (1 - info['free'] / info['size'])
                            disks_list.append(info)
                            if 'C:' in vol:
                                metrics['windows_logical_disk_free_bytes'] = info['free']
                                metrics['windows_logical_disk_size_bytes'] = info['size']
                    
                    import json
                    metrics['_disk_info_json'] = json.dumps(disks_list) if disks_list else None
                    
                    self._update_server_status(target.target, metrics, True, server_id=target.server_id)
                else:
                    self.scrape_failures.inc()
                    self.up_gauge.set(0, labels)
                    self._update_server_status(target.target, {}, False, f"HTTP {response.status_code}", server_id=target.server_id)
                    print(f"Scrape failed: {target.target} - HTTP {response.status_code}")
                
                self.response_time.set(latency_ms / 1000, labels)
                
            except httpx.TimeoutException:
                self.scrape_failures.inc()
                print(f"Scrape timeout: {target.target}")
                self._update_server_status(target.target, {}, False, "timeout", server_id=target.server_id)
            except httpx.ConnectError:
                self.scrape_failures.inc()
                print(f"Scrape connection refused: {target.target}")
                self._update_server_status(target.target, {}, False, "connection_refused", server_id=target.server_id)
            except Exception as e:
                print(f"Scrape error for {target.target}: {e}")
                self._update_server_status(target.target, {}, False, str(e), server_id=target.server_id)
            
            time.sleep(target.interval)
        
        client.close()

    def stop(self):
        self._running = False
        
        # For threads, we just set the flag and they will exit on next iteration
        for task in self._tasks:
            if hasattr(task, 'cancel'):
                try:
                    task.cancel()
                except:
                    pass
        
        self._tasks.clear()
        print("ScrapeManager stopped")

    async def close(self):
        self.stop()
        if hasattr(self, '_client') and self._client:
            await self._client.aclose()

    def add_server_target(self, server: dict):
        """Add a server from the database as a scrape target"""
        target_str = f"{server['host']}:{server['agent_port']}"
        # Use first scrape config as template if exists
        scrape_config = self.config.scrape_configs[0] if self.config.scrape_configs else None
        
        target = ScrapeTarget(
            job_name="agents",
            target=target_str,
            metrics_path=scrape_config.metrics_path if scrape_config else "/metrics",
            interval=scrape_config.scrape_interval if scrape_config else 60,
            timeout=scrape_config.scrape_timeout if scrape_config else 10,
            labels={"job": "agents", "server": server['name']},
            server_id=server['id'],
            honor_labels=scrape_config.honor_labels if scrape_config else False
        )
        
        # Avoid duplicates
        if not any(t.target == target.target for t in self.targets):
            self.targets.append(target)
            if self._running:
                # Start a new thread for this target if already running
                import threading
                thread = threading.Thread(target=self._scrape_thread, args=(target,), daemon=True)
                thread.start()
                self._tasks.append(thread)
        
        return target

    def remove_target(self, job_name: str, target: str) -> bool:
        for i, t in enumerate(self.targets):
            if t.job_name == job_name and t.target == target:
                self.targets.pop(i)
                return True
        return False

    def list_targets(self) -> list[dict]:
        return [
            {
                "job_name": t.job_name,
                "target": t.target,
                "metrics_path": t.metrics_path,
                "interval": t.interval,
                "labels": t.labels,
            }
            for t in self.targets
        ]
