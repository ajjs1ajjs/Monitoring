import asyncio
import json
import time
import os
import sqlite3
import re
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from pymon.config import PyMonConfig

logger = logging.getLogger(__name__)

@dataclass
class ScrapeTarget:
    job_name: str
    target: str
    server_id: Optional[int] = None
    service_id: Optional[int] = None
    interval: int = 60
    timeout: int = 15

@dataclass
class ScrapeResult:
    target: ScrapeTarget
    success: bool
    status_code: int = 0
    latency_ms: float = 0
    error: str = ""
    metrics: dict = None
    cpu: float = 0
    mem: float = 0
    disk: float = 0
    version: str = "v?"
    os_type: str = "linux"

class ScrapeManager:
    def __init__(self, config: PyMonConfig):
        self.config = config
        self.targets: list[ScrapeTarget] = []
        self._running = False
        self._tasks = []
        self._status_buffer = []
        self._history_buffer = []
        self._status_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()
        self._prev_metrics = {}
        
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=200)
        self._client = httpx.AsyncClient(timeout=15.0, follow_redirects=True, limits=limits, verify=False)
        self.db_path = config.storage.path

    async def start(self):
        if self._running: return
        self._running = True
        print(f"[*] ScrapeManager: Starting (Full Mode) with DB {self.db_path}", flush=True)
        await self.reload_targets()
        
        self._tasks.append(asyncio.create_task(self._reload_loop()))
        self._tasks.append(asyncio.create_task(self._flush_status_loop()))
        self._tasks.append(asyncio.create_task(self._flush_history_loop()))
        print(f"[OK] ScrapeManager: Monitoring {len(self.targets)} targets", flush=True)

    async def _reload_loop(self):
        while self._running:
            await asyncio.sleep(60)
            await self.reload_targets()

    async def reload_targets(self):
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            # Servers
            rows = conn.execute("SELECT id, name, host, agent_port FROM servers WHERE enabled = 1").fetchall()
            for r in rows:
                url = f"{r['host']}:{r['agent_port']}"
                if any(t.target == url and t.server_id == r['id'] for t in self.targets): continue
                t = ScrapeTarget(job_name=r['name'], target=url, server_id=r['id'])
                self.targets.append(t)
                self._tasks.append(asyncio.create_task(self._scrape_loop(t)))
            # Services
            rows = conn.execute("SELECT id, name, target_url, interval, timeout, expected_status FROM services WHERE enabled = 1").fetchall()
            for r in rows:
                if any(t.service_id == r['id'] for t in self.targets): continue
                t = ScrapeTarget(job_name=r['name'], target=r['target_url'], service_id=r['id'], interval=r['interval'] or 60)
                self.targets.append(t)
                self._tasks.append(asyncio.create_task(self._scrape_loop(t)))
            conn.close()
        except Exception as e:
            print(f"[!] ScrapeManager DB Error: {e}", flush=True)

    async def _scrape_loop(self, target: ScrapeTarget):
        while self._running:
            start_ts = time.time()
            try:
                url = target.target
                if not url.startswith("http"): url = f"http://{url}"
                if target.server_id and "/metrics" not in url: url = url.rstrip("/") + "/metrics"
                
                timeout = target.timeout or 10
                resp = await self._client.get(url, timeout=timeout)
                
                expected = target.expected_status or 200
                res = ScrapeResult(target=target, success=(resp.status_code == expected), status_code=resp.status_code)
                res.latency_ms = (time.time() - start_ts) * 1000
                
                if res.success and target.server_id:
                    res.metrics = self._parse_metrics(resp.text)
                    self._process_metrics(res)
                
                await self._queue_result(res)
                if res.success:
                    print(f"[OK] Scraped: {target.target} ({res.latency_ms:.0f}ms)", flush=True)
                else:
                    print(f"[WRN] HTTP {resp.status_code}: {target.target}", flush=True)
                    
            except Exception as e:
                res = ScrapeResult(target=target, success=False, error=str(e))
                await self._queue_result(res)
                print(f"[ERR] Failed: {target.target} - {e}", flush=True)
            
            await asyncio.sleep(60)

    def _process_metrics(self, res: ScrapeResult):
        m = res.metrics or {}
        ver = m.get("__version__", "v?")
        
        # Auto-detect Agent and OS from metrics
        agent = "Unknown"
        if any(k.startswith("windows_") for k in m.keys()):
            agent = "Windows Exporter"
            res.os_type = "windows"
        elif any(k.startswith("node_") for k in m.keys()):
            agent = "Node Exporter"
            res.os_type = "linux"
        elif any(k.startswith("telegraf_") for k in m.keys()):
            agent = "Telegraf"
            # Telegraf can be both, but we'll try to guess
            if any("windows" in k for k in m.keys()): res.os_type = "windows"
        
        res.version = f"{agent} ({ver})" if ver != "unknown" else agent
        
        # CPU
        cpu = m.get("cpu_usage_percent") or m.get("windows_cpu_usage")
        if cpu is None and "cpu_usage_idle" in m:
            cpu = 100.0 - m["cpu_usage_idle"]
        if cpu is None:
            idle = self._sum(m, r'.*cpu.*idle.*')
            total = self._sum(m, r'.*cpu.*')
            if total and total > 0:
                prev = self._prev_metrics.get(res.target.server_id, {})
                if prev.get('total'):
                    t_d = total - prev['total']
                    i_d = idle - prev['idle']
                    if t_d > 0: cpu = 100 * (1 - i_d / t_d)
                self._prev_metrics[res.target.server_id] = {'idle': idle, 'total': total}
        res.cpu = cpu or 0
        # RAM
        mem = m.get("memory_usage_percent") or m.get("windows_memory_usage") or m.get("mem_used_percent")
        if mem is None:
            t_m = m.get("node_memory_MemTotal_bytes") or m.get("windows_cs_physical_memory_bytes")
            f_m = m.get("node_memory_MemAvailable_bytes") or m.get("windows_os_physical_memory_free_bytes")
            if t_m and t_m > 0: mem = 100 * (1 - (f_m or 0) / t_m)
        res.mem = mem or 0
        res.disk = m.get("disk_usage_percent") or m.get("windows_disk_usage") or m.get("disk_used_percent") or 0

    async def _queue_result(self, res: ScrapeResult):
        async with self._status_lock:
            self._status_buffer.append(res)
        if res.success and res.target.server_id:
            async with self._history_lock:
                self._history_buffer.append(res)

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
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            now = datetime.now(timezone.utc).isoformat()
            for r in batch:
                st = "up" if r.success else "down"
                if r.target.server_id:
                    if r.success:
                        conn.execute("UPDATE servers SET last_status=?, last_check=?, cpu_percent=?, memory_percent=?, disk_percent=?, exporter_version=?, os_type=?, error_message=NULL WHERE id=?",
                                     (st, now, r.cpu, r.mem, r.disk, r.version, r.os_type, r.target.server_id))
                    else:
                        conn.execute("UPDATE servers SET last_status=?, last_check=?, error_message=? WHERE id=?",
                                     (st, now, (r.error or f"HTTP {r.status_code}")[:200], r.target.server_id))
                elif r.target.service_id:
                    st_srv = "UP" if r.success else "DOWN"
                    conn.execute("UPDATE services SET last_status=?, last_check=?, last_latency_ms=? WHERE id=?",
                                 (st_srv, now, r.latency_ms, r.target.service_id))
            conn.commit()
            conn.close()
        except: pass

    async def _flush_history_loop(self):
        while self._running:
            await asyncio.sleep(60)
            await self._flush_history_batch()

    async def _flush_history_batch(self):
        if not self._history_buffer: return
        async with self._history_lock:
            batch = self._history_buffer[:]
            self._history_buffer = []
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            now = datetime.now(timezone.utc).isoformat()
            for r in batch:
                conn.execute("INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, timestamp) VALUES (?, ?, ?, ?, ?)",
                             (r.target.server_id, r.cpu, r.mem, r.disk, now))
            conn.commit()
            conn.close()
        except: pass

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
                    name = line.split("{", 1)[0].strip()
                    val = float(line.rsplit("}", 1)[1].strip())
                    m[name] = val
                else:
                    p = line.split()
                    if len(p) >= 2: m[p[0]] = float(p[1])
            except: continue
        return m

    def _sum(self, m, pattern):
        total = 0.0
        try:
            regex = re.compile(pattern)
            for k, v in m.items():
                if regex.match(k): total += v
        except: pass
        return total

    async def stop(self):
        self._running = False
        await self._client.aclose()
