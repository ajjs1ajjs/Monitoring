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
    # Processed metrics
    cpu: float = 0
    mem: float = 0
    disk: float = 0
    version: str = "v?"

class ScrapeManager:
    def __init__(self, config: PyMonConfig):
        self.config = config
        self.targets: list[ScrapeTarget] = []
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._down_alerted: set[int] = set()
        self._prev_metrics: dict[int, dict] = {} # {server_id: {timestamp: float, metrics: dict}}
        
        # Batching & Buffers
        self._status_buffer = []
        self._history_buffer = []
        self._status_lock = asyncio.Lock()
        self._buffer_lock = asyncio.Lock()
        
        # Prometheus Metrics
        self.scrape_total = Counter("pymon_scrape_total", "Total scrape attempts")
        self.scrape_success = Counter("pymon_scrape_success_total", "Successful scrapes")
        self.scrape_failures = Counter("pymon_scrape_failures_total", "Failed scrapes")
        self.up_gauge = Gauge("up", "Target availability (1=up, 0=down)")
        self.response_time = Gauge("pymon_response_time_seconds", "Response time in seconds")
        
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self._last_states: dict[int, str] = {}
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

    async def start(self):
        if self._running:
            return
        self._running = True
        
        await self._load_dynamic_targets()
        
        for target in self.targets:
            self._tasks.append(asyncio.create_task(self._scrape_loop(target)))
            
        self._tasks.append(asyncio.create_task(self._flush_status_loop()))
        self._tasks.append(asyncio.create_task(self._flush_buffer_loop()))
        self._tasks.append(asyncio.create_task(self._dynamic_reload_loop()))
        logger.info("ScrapeManager started (Enhanced with Batching)")

    async def stop(self):
        self._running = False
        await self._flush_status_batch()
        await self._flush_history()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._client.aclose()

    async def _dynamic_reload_loop(self):
        while self._running:
            await asyncio.sleep(30)
            await self._load_dynamic_targets()

    async def _load_dynamic_targets(self):
        db_path = self.config.storage.path
        new_count = 0
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM servers WHERE enabled = 1").fetchall()
            for r in rows:
                target_str = f"{r['host']}:{r['agent_port']}"
                if any(t.target == target_str for t in self.targets):
                    continue
                
                new_t = ScrapeTarget(
                    job_name=r['server_group'] or "dynamic",
                    target=target_str,
                    metrics_path="/metrics",
                    interval=60,
                    timeout=10,
                    labels={"server_id": str(r['id']), "name": r['name']},
                    server_id=r['id']
                )
                self.targets.append(new_t)
                new_count += 1
                if self._running:
                    self._tasks.append(asyncio.create_task(self._scrape_loop(new_t)))
            conn.close()
            if new_count > 0: logger.info(f"ScrapeManager: Loaded {new_count} new targets")
        except Exception as e:
            logger.error(f"Reload failed: {e}")

    async def _scrape_loop(self, target: ScrapeTarget):
        while self._running:
            start_time = time.time()
            try:
                await self.execute_scrape(target)
            except Exception as e:
                logger.error(f"Loop error for {target.target}: {e}")
            
            elapsed = time.time() - start_time
            await asyncio.sleep(max(0, target.interval - elapsed))

    async def execute_scrape(self, target: ScrapeTarget):
        result = await self.scrape_target(target)
        self.scrape_total.inc()
        
        lbl = [Label("job", target.job_name), Label("target", target.target)]
        if result.success:
            self.scrape_success.inc()
            self.up_gauge.set(1, lbl)
            # Process metrics for DB
            self._process_result_metrics(result)
        else:
            self.scrape_failures.inc()
            self.up_gauge.set(0, lbl)
            
        await self._queue_status_update(result)
        
        if result.success and result.target.server_id:
            async with self._buffer_lock:
                self._history_buffer.append(result)

    def _process_result_metrics(self, res: ScrapeResult):
        m = res.metrics or {}
        res.version = m.get("__version__", "v?")
        
        # CPU calculation logic
        cpu = self._find_val(m, ["cpu_usage_percent", "windows_cpu_usage", "node_cpu_calculated"])
        if not cpu:
            # Handle node_exporter / windows_exporter counters
            idle = self._sum(m, r'.*cpu.*mode="idle".*')
            total = self._sum(m, r'.*cpu.*')
            if total > 0:
                prev = self._prev_metrics.get(res.target.server_id, {})
                if prev.get('total'):
                    t_delta = total - prev['total']
                    i_delta = idle - prev['idle']
                    if t_delta > 0: cpu = 100 * (1 - i_delta / t_delta)
                self._prev_metrics[res.target.server_id] = {'idle': idle, 'total': total}
        res.cpu = cpu or 0

        # Memory calculation
        mem = self._find_val(m, ["memory_usage_percent", "windows_memory_usage", "node_memory_calculated"])
        if not mem:
            total_m = self._find_val(m, ["node_memory_MemTotal_bytes", "windows_cs_physical_memory_bytes"])
            free_m = self._find_val(m, ["node_memory_MemAvailable_bytes", "windows_os_physical_memory_free_bytes"])
            if total_m > 0: mem = 100 * (1 - free_m / total_m)
        res.mem = mem or 0
        
        # Disk
        res.disk = self._find_val(m, ["disk_usage_percent", "windows_disk_usage"]) or 0

    async def _queue_status_update(self, res: ScrapeResult):
        async with self._status_lock:
            self._status_buffer.append(res)

    async def _flush_status_loop(self):
        while self._running:
            await asyncio.sleep(5)
            await self._flush_status_batch()

    async def _flush_status_batch(self):
        if not self._status_buffer: return
        async with self._status_lock:
            batch = self._status_buffer[:]
            self._status_buffer = []
        
        try:
            conn = sqlite3.connect(self.config.storage.path, timeout=30)
            now = datetime.now(timezone.utc).isoformat()
            for r in batch:
                st = "online" if r.success else "offline"
                if r.success:
                    conn.execute("UPDATE servers SET last_status=?, last_check=?, cpu_percent=?, memory_percent=?, disk_percent=?, exporter_version=?, error_message=NULL WHERE id=?",
                                 (st, now, r.cpu, r.mem, r.disk, r.version, r.target.server_id))
                else:
                    conn.execute("UPDATE servers SET last_status=?, last_check=?, error_message=? WHERE id=?",
                                 (st, now, r.error, r.target.server_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Status flush error: {e}")

    async def _flush_buffer_loop(self):
        while self._running:
            await asyncio.sleep(60)
            await self._flush_history()

    async def _flush_history(self):
        if not self._history_buffer: return
        async with self._buffer_lock:
            batch = self._history_buffer[:]
            self._history_buffer = []
            
        try:
            conn = sqlite3.connect(self.config.storage.path, timeout=30)
            now = datetime.now(timezone.utc).isoformat()
            for r in batch:
                conn.execute("INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, timestamp) VALUES (?, ?, ?, ?, ?)",
                             (r.target.server_id, r.cpu, r.mem, r.disk, now))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"History flush error: {e}")

    async def scrape_target(self, target: ScrapeTarget) -> ScrapeResult:
        res = ScrapeResult(target=target, success=False, timestamp=datetime.now(timezone.utc), metrics={})
        url = target.target
        if not url.startswith("http"): url = f"http://{url}"
        if not url.endswith(target.metrics_path): url = url.rstrip("/") + target.metrics_path
        
        start = time.time()
        try:
            r = await self._client.get(url, timeout=target.timeout)
            res.latency_ms = (time.time() - start) * 1000
            res.status_code = r.status_code
            res.success = (r.status_code == 200)
            if res.success: res.metrics = self._parse_metrics(r.text)
        except Exception as e:
            res.error = str(e)
        return res

    def _parse_metrics(self, text: str) -> dict:
        m = {"__version__": "unknown"}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "_exporter_build_info{" in line:
                match = re.search(r'version="([^"]+)"', line)
                if match: m["__version__"] = match.group(1)
            try:
                if "{" in line:
                    name, rest = line.split("{", 1)
                    val = float(rest.rsplit("}", 1)[1].strip())
                    m[name.strip()] = val
                    m[line] = val
                else:
                    p = line.split()
                    if len(p) >= 2: m[p[0]] = float(p[1])
            except: continue
        return m

    def _find_val(self, m, keys):
        for k in keys:
            if k in m: return m[k]
        return None

    def _sum(self, m, pattern):
        total = 0.0
        regex = re.compile(pattern)
        for k, v in m.items():
            if regex.match(k): total += v
        return total
