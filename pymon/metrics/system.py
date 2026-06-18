"""System metrics collector"""

import asyncio
import time

from pymon.metrics.collector import Counter, Gauge, registry
from pymon.metrics.models import Label
from pymon.storage import get_storage


class SystemCollector:
    def __init__(self, interval: int = 15, labels: list[Label] | None = None):
        self.interval = interval
        self.labels = labels or []
        self._running = False
        self._task = None

        self.cpu_gauge = Gauge("system_cpu_usage_percent", "CPU usage percentage", self.labels)
        self.memory_gauge = Gauge("system_memory_usage_percent", "Memory usage percentage", self.labels)
        self.memory_bytes = Gauge("system_memory_bytes", "Memory usage in bytes", self.labels)
        self.disk_gauge = Gauge("system_disk_usage_percent", "Disk usage percentage", self.labels)
        self.uptime_gauge = Gauge("system_uptime_seconds", "System uptime in seconds", self.labels)
        self.requests_counter = Counter("http_requests_total", "Total HTTP requests", self.labels)

        self._start_time = time.time()

    async def collect(self) -> None:
        while self._running:
            try:
                await self._collect_cpu()
                await self._collect_memory()
                await self._collect_disk()
                await self._collect_uptime()

                for metric in registry.get_all_metrics():
                    if metric.name.startswith("system_"):
                        await get_storage().write(metric)

            except Exception as e:
                print(f"Collection error: {e}")

            await asyncio.sleep(self.interval)

    async def _collect_cpu(self) -> None:
        try:
            import psutil

            cpu = await asyncio.to_thread(psutil.cpu_percent, 1)
            self.cpu_gauge.set(cpu, self.labels)
        except ImportError:
            self.cpu_gauge.set(0, self.labels)

    async def _collect_memory(self) -> None:
        try:
            import psutil

            mem = psutil.virtual_memory()
            self.memory_gauge.set(mem.percent, self.labels)
            self.memory_bytes.set(mem.used, self.labels + [Label("type", "used")])
            self.memory_bytes.set(mem.total, self.labels + [Label("type", "total")])
        except ImportError:
            self.memory_gauge.set(0, self.labels)

    async def _collect_disk(self) -> None:
        try:
            import psutil

            for part in psutil.disk_partitions():
                if 'cdrom' in part.opts or part.fstype == '':
                    continue
                mp = part.mountpoint.lower()
                fst = part.fstype.lower()
                dev = part.device.lower()
                if 'harddiskvolume' in mp or 'harddiskvolume' in dev:
                    continue
                if 'docker' in mp or 'kubelet' in mp or 'tmpfs' in fst or 'squashfs' in fst or 'overlay' in fst:
                    continue
                if mp.startswith('/snap/') or '/snap/' in mp:
                    continue
                if mp == '/dev/shm' or mp.startswith('/run/user/'):
                    continue
                if dev.startswith('/dev/loop'):
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    vol = part.mountpoint.rstrip('\\').rstrip('/')
                    self.disk_gauge.set(usage.percent, self.labels + [Label("volume", vol)])
                except PermissionError:
                    continue
        except ImportError:
            self.disk_gauge.set(0, self.labels)

    async def _collect_uptime(self) -> None:
        uptime = time.time() - self._start_time
        self.uptime_gauge.set(uptime, self.labels)

    def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self.collect())

    def stop(self) -> None:
        self._running = False
