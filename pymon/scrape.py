import asyncio
import json
import sys
from datetime import datetime

import httpx

from pymon.api.deps import get_db, manager


class ScrapeManager:
    def __init__(self, config=None):
        self.config = config
        self.interval = 15
        self.retention_hours = 168
        if config:
            self.interval = config.scrape_configs[0].scrape_interval if config.scrape_configs else 15
            if hasattr(config.storage, 'retention_hours'):
                self.retention_hours = config.storage.retention_hours
        self.running = False
        self._last_cleanup = 0

    async def start(self):
        self.running = True
        asyncio.create_task(self._scrape_loop())

    async def stop(self):
        self.running = False

    async def _scrape_loop(self):
        await asyncio.sleep(5)
        while self.running:
            try:
                await self.scrape_all()
                await self._cleanup_old_metrics()
            except Exception as e:
                import traceback
                print(f"[ERROR] Scrape loop: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
            await asyncio.sleep(self.interval)

    async def _cleanup_old_metrics(self):
        import time
        now = time.time()
        if now - self._last_cleanup < 3600:
            return
        self._last_cleanup = now
        try:
            conn = get_db()
            conn.execute(
                "DELETE FROM metrics_history WHERE timestamp < datetime('now', ?)",
                (f"-{self.retention_hours} hours",),
            )
            conn.execute(
                "DELETE FROM services_history WHERE timestamp < datetime('now', ?)",
                (f"-{self.retention_hours} hours",),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    async def scrape_all(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, host, agent_port, os_type, enabled, scrape_interval FROM servers WHERE enabled=1")
        servers = cursor.fetchall()
        conn.close()

        if not servers:
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = []
            for s in servers:
                sid, name, host, port, os_type, enabled = s[:6]
                tasks.append(self._scrape_one(client, sid, name, host, port))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            ok = 0
            for r in results:
                if r is True:
                    ok += 1
                elif isinstance(r, Exception):
                    print(f"[ScrapeManager] Error: {type(r).__name__}: {r}", file=sys.stderr, flush=True)
            if ok:
                print(f"[ScrapeManager] Collected {ok}/{len(servers)} servers", flush=True)

    async def _scrape_one(self, client, server_id, name, host, port):
        url = f"http://{host}:{port}/metrics"
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return False
            text = resp.text
        except httpx.ConnectError:
            return False
        except httpx.TimeoutException:
            return False
        except Exception:
            return False

        data = self._parse_metrics(text, name)

        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        try:
            vols = data.get('volumes', [])
            disk_json = json.dumps(vols)
            vol_summary = json.dumps([{'volume': v['volume'], 'used_percent': v['used_percent']} for v in vols])
            cursor.execute("""
                INSERT INTO metrics_history
                (timestamp, server_id, cpu_percent, memory_percent,
                 disk_percent, network_rx, network_tx, disk_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (now, server_id,
                  data.get('cpu', 0), data.get('memory', 0),
                  data.get('disk', 0), data.get('net_rx', 0),
                  data.get('net_tx', 0), disk_json))

            cursor.execute("""
                UPDATE servers SET last_status='up', last_check=?,
                cpu_percent=?, memory_percent=?, disk_percent=?,
                volumes=?
                WHERE id=?
            """, (now, data.get('cpu', 0), data.get('memory', 0),
                  data.get('disk', 0), vol_summary, server_id))
            conn.commit()
            conn.close()
            await manager.broadcast({"type": "metrics_updated", "server_id": server_id})
            return True
        except Exception:
            conn.close()
            return False

    def _parse_metrics(self, text, name=""):
        result = {'cpu': 0, 'memory': 0, 'disk': 0, 'net_rx': 0, 'net_tx': 0, 'volumes': []}
        metrics_map: dict[str, list[dict]] = {}

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.rsplit(None, 1)
            if len(parts) != 2:
                continue
            metric, val_str = parts
            try:
                val = float(val_str)
            except ValueError:
                continue

            name_m = metric.split('{')[0] if '{' in metric else metric
            labels = {}
            if '{' in metric:
                lbl_str = metric[metric.index('{')+1:metric.index('}')]
                for pair in lbl_str.split(','):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        labels[k.strip()] = v.strip('"')
            metrics_map.setdefault(name_m, []).append({'val': val, 'labels': labels})

        def _should_include_volume(vol: str) -> bool:
            vl = vol.lower()
            if 'harddiskvolume' in vl:
                return False
            if vl.startswith('/snap/') or '/snap/' in vl:
                return False
            if 'docker' in vl or 'kubelet' in vl or 'tmpfs' in vl or 'overlay' in vl:
                return False
            if vl == 'shm' or vl.endswith('/shm') or '/shm' in vl:
                return False
            if '/run/user/' in vl:
                return False
            return True

        is_linux = any('node_' in k for k in metrics_map)

        if is_linux:
            self._parse_linux_metrics(metrics_map, result, _should_include_volume)
        else:
            self._parse_windows_metrics(metrics_map, result, _should_include_volume)

        return result

    def _parse_linux_metrics(self, metrics_map, result, _should_include_volume):
        cpu_idle = 0.0
        cpu_total = 0.0
        for k, items in metrics_map.items():
            if 'node_cpu_seconds_total' in k:
                for item in items:
                    if item['labels'].get('cpu') == 'cpu':
                        continue
                    cpu_total += item['val']
                    if item['labels'].get('mode') == 'idle':
                        cpu_idle += item['val']
        if cpu_total > 0:
            result['cpu'] = round((1 - cpu_idle / cpu_total) * 100, 1)

        mem_total = 0.0
        mem_available = 0.0
        for k, items in metrics_map.items():
            if 'node_memory_MemTotal_bytes' in k:
                mem_total = items[0]['val'] if items else 0
            elif 'node_memory_MemAvailable_bytes' in k:
                mem_available = items[0]['val'] if items else 0
        if mem_total > 0:
            result['memory'] = round(((mem_total - mem_available) / mem_total) * 100, 1)

        disk_size = {}
        disk_free = {}
        for k, items in metrics_map.items():
            if 'node_filesystem_size_bytes' in k:
                for item in items:
                    fstype = item['labels'].get('fstype', '')
                    if fstype in ('tmpfs', 'devtmpfs', 'squashfs', 'overlay', 'nsfs'):
                        continue
                    mountpoint = item['labels'].get('mountpoint', '') or item['labels'].get('device', '')
                    if not mountpoint:
                        continue
                    disk_size[mountpoint] = max(disk_size.get(mountpoint, 0), item['val'])
            elif 'node_filesystem_avail_bytes' in k:
                for item in items:
                    fstype = item['labels'].get('fstype', '')
                    if fstype in ('tmpfs', 'devtmpfs', 'squashfs', 'overlay', 'nsfs'):
                        continue
                    mountpoint = item['labels'].get('mountpoint', '') or item['labels'].get('device', '')
                    if not mountpoint:
                        continue
                    disk_free[mountpoint] = max(disk_free.get(mountpoint, 0), item['val'])

        total_linux_free = 0.0
        total_linux_size = 0.0
        for key in disk_size:
            if not _should_include_volume(key):
                continue
            size = disk_size[key]
            free_val = disk_free.get(key, size)
            if size > 0:
                used_pct = round(((size - free_val) / size) * 100, 1)
                result['volumes'].append({
                    'volume': key,
                    'size_bytes': size,
                    'free_bytes': free_val,
                    'used_percent': used_pct
                })
                total_linux_free += free_val
                total_linux_size += size
        if total_linux_size > 0:
            result['disk'] = round(((total_linux_size - total_linux_free) / total_linux_size) * 100, 1)

        net_rx = 0.0
        net_tx = 0.0
        for k, items in metrics_map.items():
            if 'node_network_receive_bytes_total' in k:
                for item in items:
                    if item['labels'].get('device', '') == 'lo':
                        continue
                    net_rx += item['val']
            elif 'node_network_transmit_bytes_total' in k:
                for item in items:
                    if item['labels'].get('device', '') == 'lo':
                        continue
                    net_tx += item['val']
        if net_rx > 0 or net_tx > 0:
            result['net_rx'] = net_rx
            result['net_tx'] = net_tx

    def _parse_windows_metrics(self, metrics_map, result, _should_include_volume):
        windows_cpu_total = 0.0
        windows_cpu_idle = 0.0
        for k, items in metrics_map.items():
            if 'windows_cpu_time_total' in k:
                for item in items:
                    windows_cpu_total += item['val']
                    if item['labels'].get('mode') == 'idle':
                        windows_cpu_idle += item['val']
        if windows_cpu_total > 0:
            result['cpu'] = round((1 - windows_cpu_idle / windows_cpu_total) * 100, 1)

        if result['cpu'] == 0:
            for k, items in metrics_map.items():
                if 'windows_cpu_percent' in k or 'windows_cpu_processor_time_percent' in k:
                    vals = [item['val'] for item in items]
                    if vals:
                        result['cpu'] = round(min(max(sum(vals) / len(vals), 0), 100), 1)
                        break

        mem_total = 0.0
        mem_available = 0.0
        for k, items in metrics_map.items():
            if 'windows_cs_physical_memory_bytes' in k:
                mem_total = items[0]['val'] if items else 0
            elif 'windows_memory_available_bytes' in k:
                mem_available = items[0]['val'] if items else 0
        if mem_total > 0:
            result['memory'] = round(((mem_total - mem_available) / mem_total) * 100, 1)

        disk_free_items = [
            item for k, items in metrics_map.items()
            if 'windows_logical_disk_free_bytes' in k
            for item in items
        ]
        disk_size_items = [
            item for k, items in metrics_map.items()
            if 'windows_logical_disk_size_bytes' in k
            for item in items
        ]

        vol_data = {}
        for item in disk_free_items:
            vol = item['labels'].get('volume', 'ALL')
            vol_data.setdefault(vol, {})['free'] = item['val']
        for item in disk_size_items:
            vol = item['labels'].get('volume', 'ALL')
            vol_data.setdefault(vol, {})['size'] = item['val']

        total_free = 0.0
        total_size = 0.0
        for vol, d in vol_data.items():
            if not _should_include_volume(vol):
                continue
            if 'size' in d and d['size'] > 0:
                free_val = d.get('free', 0)
                used_pct = round(((d['size'] - free_val) / d['size']) * 100, 1)
                result['volumes'].append({
                    'volume': vol,
                    'size_bytes': d['size'],
                    'free_bytes': free_val,
                    'used_percent': used_pct
                })
                total_free += free_val
                total_size += d['size']
        if total_size > 0:
            result['disk'] = round(((total_size - total_free) / total_size) * 100, 1)

        net_rx = 0.0
        net_tx = 0.0
        for k, items in metrics_map.items():
            if 'windows_net_bytes_received_total' in k:
                net_rx += sum(item['val'] for item in items)
            elif 'windows_net_bytes_sent_total' in k:
                net_tx += sum(item['val'] for item in items)

        if net_rx == 0 and net_tx == 0:
            for k, items in metrics_map.items():
                if 'windows_net_current_bandwidth_bytes' in k:
                    vals = [item['val'] for item in items]
                    if vals:
                        net_rx = sum(vals)
                        net_tx = sum(vals)
                    break
        if net_rx > 0 or net_tx > 0:
            result['net_rx'] = net_rx
            result['net_tx'] = net_tx


class ServiceChecker:
    def __init__(self):
        self.default_interval = 60
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self._check_loop())

    async def stop(self):
        self.running = False

    async def _check_loop(self):
        await asyncio.sleep(10)
        last_checked: dict[int, float] = {}
        while self.running:
            try:
                await self.check_all(last_checked)
            except Exception as e:
                import traceback
                print(f"[ERROR] ServiceChecker: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
            await asyncio.sleep(5)

    async def check_all(self, last_checked: dict[int, float] | None = None):
        import time
        now_ts = time.time()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, target_url, timeout, expected_status, enabled, interval FROM services WHERE enabled=1")
        services = cursor.fetchall()
        conn.close()

        if not services:
            return

        async with httpx.AsyncClient(timeout=15.0) as client:
            tasks = []
            for s in services:
                sid, name, url, timeout, expected, enabled = s[:6]
                srv_interval = s[6] if len(s) > 6 and s[6] and s[6] > 0 else self.default_interval
                if last_checked is not None:
                    last = last_checked.get(sid, 0)
                    if now_ts - last < srv_interval:
                        continue
                    last_checked[sid] = now_ts
                tasks.append(self._check_one(client, sid, name, url, timeout, expected))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_one(self, client, service_id, name, url, timeout, expected):
        expected_status = int(expected) if expected else 200
        start = datetime.now()
        try:
            resp = await client.get(url, timeout=timeout if timeout else 10)
            latency = int((datetime.now() - start).total_seconds() * 1000)
            status = 'up' if resp.status_code == expected_status else 'degraded'
        except Exception:
            latency = 0
            status = 'down'

        now = datetime.now().isoformat()
        for attempt in range(3):
            try:
                conn = get_db()
                conn.execute("UPDATE services SET status=?, last_check=?, response_time_ms=? WHERE id=?",
                             (status, now, latency, service_id))
                conn.execute("INSERT INTO services_history (service_id, status, latency_ms, timestamp) VALUES (?, ?, ?, ?)",
                             (service_id, status, latency, now))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                try:
                    conn.close()
                except Exception:
                    pass
                if attempt == 2:
                    print(f"[ServiceChecker] DB error for {name} ({url}): {e}", file=sys.stderr, flush=True)
                    return False
                await asyncio.sleep(0.2)
        return False


scraper = ScrapeManager()
service_checker = ServiceChecker()


def get_scraper():
    return scraper


async def start_scraper():
    await scraper.start()
    await service_checker.start()
    asyncio.create_task(_backup_scheduler())


async def _backup_scheduler():
    await asyncio.sleep(60)
    while True:
        try:
            import os

            from pymon.config import load_config
            config = load_config(os.getenv("CONFIG_PATH", "config.yml"))
            if hasattr(config, 'backup') and config.backup and config.backup.enabled:
                await _run_backup_if_due(config)
        except Exception:
            pass
        await asyncio.sleep(3600)


_last_backup_run = 0


async def _run_backup_if_due(config):
    global _last_backup_run
    import os
    import shutil
    import time
    now = time.time()
    if now - _last_backup_run < 3600:
        return
    try:
        schedule = config.backup.schedule
        parts = schedule.strip().split()
        if len(parts) != 5:
            return
        minute, hour, day, month, weekday = parts
        if hour != '*' and int(hour) != datetime.now().hour:
            return
        _last_backup_run = now
        backup_dir = config.backup.backup_dir
        os.makedirs(backup_dir, exist_ok=True)
        db_path = config.storage.path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"pymon_backup_{timestamp}.db")
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
        backups = sorted(
            [f for f in os.listdir(backup_dir) if f.endswith('.db')],
            key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
        )
        while len(backups) > config.backup.max_backups:
            os.remove(os.path.join(backup_dir, backups.pop(0)))
    except Exception:
        pass
