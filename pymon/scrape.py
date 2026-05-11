import asyncio
import time
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

@dataclass
class ScrapeResult:
    target: ScrapeTarget
    success: bool
    latency_ms: float = 0
    error: str = ""
    metrics: dict = None

class ScrapeManager:
    def __init__(self, config: PyMonConfig):
        self.config = config
        self.targets = []
        self._running = False
        self._tasks = []
        self._client = httpx.AsyncClient(timeout=5.0, follow_redirects=True, verify=False)
        self.db_path = config.storage.path

    async def start(self):
        if self._running: return
        self._running = True
        print(f"[*] ScrapeManager: Starting with DB {self.db_path}", flush=True)
        await self.reload_targets()
        asyncio.create_task(self._reload_loop())
        print(f"[OK] ScrapeManager: {len(self.targets)} targets active", flush=True)

    async def _reload_loop(self):
        while self._running:
            await asyncio.sleep(60)
            await self.reload_targets()

    async def reload_targets(self):
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
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
            rows = conn.execute("SELECT id, name, target_url, interval FROM services WHERE enabled = 1").fetchall()
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
                # If server, append /metrics
                if target.server_id and "/metrics" not in url:
                    url = url.rstrip("/") + "/metrics"
                
                resp = await self._client.get(url)
                success = (resp.status_code == 200)
                latency = (time.time() - start_ts) * 1000
                
                # Immediate DB update for stability (one by one for now to debug)
                await self._save_status(target, success, latency, "" if success else f"HTTP {resp.status_code}")
                if success:
                    print(f"[OK] Scraped: {target.target} ({latency:.0f}ms)", flush=True)
            except Exception as e:
                await self._save_status(target, False, 0, str(e))
                print(f"[ERR] Failed: {target.target} - {e}", flush=True)
            
            await asyncio.sleep(max(10, target.interval))

    async def _save_status(self, target: ScrapeTarget, success: bool, latency: float, error: str):
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            now = datetime.now(timezone.utc).isoformat()
            st = "online" if success else "offline"
            if target.server_id:
                conn.execute("UPDATE servers SET last_status=?, last_check=?, error_message=? WHERE id=?",
                             (st, now, error[:200], target.server_id))
            elif target.service_id:
                st_srv = "UP" if success else "DOWN"
                conn.execute("UPDATE services SET status=?, last_check=?, response_time_ms=? WHERE id=?",
                             (st_srv, now, latency, target.service_id))
            conn.commit()
            conn.close()
        except: pass

    async def stop(self):
        self._running = False
        await self._client.aclose()
