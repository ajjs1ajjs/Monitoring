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
    service_id: Optional[int] = None
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
        self._status_buffer = []
        self._status_lock = asyncio.Lock()
        self._prev_metrics: dict[int, dict] = {}
        
        # Connection Pool
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=200)
        self._client = httpx.AsyncClient(timeout=15.0, follow_redirects=True, limits=limits, verify=False)
        
        self._build_targets()

    def _build_targets(self):
        self.targets = []
        # Config-based targets are not used much in this project, mostly DB-based
        pass

    async def start(self):
        if self._running: return
        self._running = True
        
        print("[*] ScrapeManager: Loading targets from database...")
        await self._load_dynamic_targets()
        
        # Start loops
        self._tasks.append(asyncio.create_task(self._flush_status_loop()))
        self._tasks.append(asyncio.create_task(self._dynamic_reload_loop()))
        print(f"[OK] ScrapeManager: Started with {len(self.targets)} active targets")

    async def stop(self):
        self._running = False
        for task in self._tasks: task.cancel()
        await self._client.aclose()

    async def _dynamic_reload_loop(self):
        while self._running:
            await asyncio.sleep(60)
            await self._load_dynamic_targets()

    async def _load_dynamic_targets(self):
        db_path = self.config.storage.path
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            # 1. Load Servers
            servers = conn.execute("SELECT * FROM servers WHERE enabled = 1").fetchall()
            for r in servers:
                t_str = f"{r['host']}:{r['agent_port']}"
                if any(t.target == t_str and t.server_id == r['id'] for t in self.targets): continue
                
                target = ScrapeTarget(
                    job_name=r['server_group'] or "server",
                    target=t_str,
                    metrics_path="/metrics",
                    interval=60,
                    timeout=10,
                    labels={"name": r['name']},
                    server_id=r['id']
                )
                self.targets.append(target)
                self._tasks.append(asyncio.create_task(self._scrape_loop(target)))

            # 2. Load Services
            services = conn.execute("SELECT * FROM services WHERE enabled = 1").fetchall()
            for r in services:
                if any(t.service_id == r['id'] for t in self.targets): continue
                
                target = ScrapeTarget(
                    job_name="service",
                    target=r['target_url'],
                    metrics_path="",
                    interval=r['interval'] or 60,
                    timeout=10,
                    labels={"name": r['name']},
                    service_id=r['id']
                )
                self.targets.append(target)
                self._tasks.append(asyncio.create_task(self._scrape_loop(target)))
                
            conn.close()
        except Exception as e:
            print(f"[!] ScrapeManager Error: {e}")

    async def _scrape_loop(self, target: ScrapeTarget):
        while self._running:
            start = time.time()
            try:
                res = await self.scrape_target(target)
                if res.success and target.server_id:
                    self._process_metrics(res)
                await self._queue_status(res)
            except Exception as e:
                pass
            
            wait = max(10, target.interval - (time.time() - start))
            await asyncio.sleep(wait)

    async def scrape_target(self, target: ScrapeTarget) -> ScrapeResult:
        res = ScrapeResult(target=target, success=False, timestamp=datetime.now(timezone.utc))
        url = target.target
        if not url.startswith("http"): url = f"http://{url}"
        if target.metrics_path:
            url = url.rstrip("/") + target.metrics_path
            
        try:
            r = await self._client.get(url, timeout=target.timeout)
            res.latency_ms = (time.time() - res.timestamp.timestamp()) * 1000 # Corrected latency
            res.latency_ms = max(0, time.time() - res.timestamp.timestamp()) * 1000
            res.status_code = r.status_code
            res.success = (r.status_code == 200)
            if res.success and target.metrics_path:
                res.metrics = self._parse_metrics(r.text)
        except Exception as e:
            res.error = str(e)
        return res

    def _process_metrics(self, res: ScrapeResult):
        m = res.metrics or {}
        res.version = m.get("__version__", "v?")
        
        # CPU
        cpu = m.get("cpu_usage_percent") or m.get("windows_cpu_usage")
        if cpu is None:
            idle = self._sum(m, r'.*cpu.*idle.*')
            total = self._sum(m, r'.*cpu.*')
            if total > 0:
                prev = self._prev_metrics.get(res.target.server_id, {})
                if prev.get('total'):
                    t_d = total - prev['total']
                    i_d = idle - prev['idle']
                    if t_d > 0: cpu = 100 * (1 - i_d / t_d)
                self._prev_metrics[res.target.server_id] = {'idle': idle, 'total': total}
        res.cpu = cpu or 0

        # RAM
        mem = m.get("memory_usage_percent") or m.get("windows_memory_usage")
        if mem is None:
            t_m = m.get("node_memory_MemTotal_bytes") or m.get("windows_cs_physical_memory_bytes")
            f_m = m.get("node_memory_MemAvailable_bytes") or m.get("windows_os_physical_memory_free_bytes")
            if t_m and t_m > 0: mem = 100 * (1 - (f_m or 0) / t_m)
        res.mem = mem or 0
        res.disk = m.get("disk_usage_percent") or m.get("windows_disk_usage") or 0

    async def _queue_status(self, res: ScrapeResult):
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
                if r.target.server_id:
                    if r.success:
                        conn.execute("UPDATE servers SET last_status=?, last_check=?, cpu_percent=?, memory_percent=?, disk_percent=?, exporter_version=?, error_message=NULL WHERE id=?",
                                     (st, now, r.cpu, r.mem, r.disk, r.version, r.target.server_id))
                    else:
                        conn.execute("UPDATE servers SET last_status=?, last_check=?, error_message=? WHERE id=?",
                                     (st, now, r.error[:200] if r.error else "Error", r.target.server_id))
                elif r.target.service_id:
                    st_srv = "UP" if r.success else "DOWN"
                    conn.execute("UPDATE services SET status=?, last_check=?, response_time_ms=? WHERE id=?",
                                 (st_srv, now, r.latency_ms, r.target.service_id))
            conn.commit()
            conn.close()
            print(f"[*] ScrapeManager: Flushed {len(batch)} statuses to DB")
        except Exception as e:
            print(f"[!] ScrapeManager Flush Error: {e}")

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
                else:
                    p = line.split()
                    if len(p) >= 2: m[p[0]] = float(p[1])
            except: continue
        return m

    def _sum(self, m, pattern):
        total = 0.0
        regex = re.compile(pattern)
        for k, v in m.items():
            if regex.match(k): total += v
        return total
