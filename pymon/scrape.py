import asyncio
import sys
        import json
from datetime import datetime

from pymon.api.deps import get_db, manager

class ScrapeManager:
    def __init__(self, config=None):
        self.config = config
        self.interval = 15
        if config:
            self.interval = config.scrape_configs[0].scrape_interval if config.scrape_configs else 15
        self.running = False

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
            except Exception as e:
                import traceback
                print(f"[ERROR] Scrape loop: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
            await asyncio.sleep(self.interval)

    async def scrape_all(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, host, agent_port, os_type, enabled FROM servers WHERE enabled=1")
        servers = cursor.fetchall()
        conn.close()

        if not servers:
            return

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = []
            for s in servers:
                sid, name, host, port, os_type, enabled = s
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
        except Exception as e:
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
            return True
        except Exception as e:
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
            if name_m.endswith('_total'):
                continue
            labels = {}
            if '{' in metric:
                lbl_str = metric[metric.index('{')+1:metric.index('}')]
                for pair in lbl_str.split(','):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        labels[k.strip()] = v.strip('"')
            metrics_map.setdefault(name_m, []).append({'val': val, 'labels': labels})

        cpu_vals = [item['val'] for k, items in metrics_map.items() if 'windows_cpu_core_frequency_mhz' in k for item in items]
        if cpu_vals:
            result['cpu'] = round(min(max(cpu_vals[0] / 5000.0 * 100, 0), 100), 1)

        mem_total_list = [item['val'] for k, items in metrics_map.items() if 'windows_cs_physical_memory_bytes' in k for item in items]
        mem_free_list = [item['val'] for k, items in metrics_map.items() if 'windows_memory_available_bytes' in k for item in items]
        total_mem = mem_total_list[0] if mem_total_list else 0
        free_mem = mem_free_list[0] if mem_free_list else 0
        if total_mem > 0:
            result['memory'] = round(((total_mem - free_mem) / total_mem) * 100, 1)

        disk_free_items = [item for k, items in metrics_map.items() if 'windows_logical_disk_free_bytes' in k for item in items]
        disk_size_items = [item for k, items in metrics_map.items() if 'windows_logical_disk_size_bytes' in k for item in items]

        vol_data = {}
        for item in disk_free_items:
            vol = item['labels'].get('volume', item['labels'].get('drive', 'ALL'))
            vol_data.setdefault(vol, {})['free'] = item['val']
        for item in disk_size_items:
            vol = item['labels'].get('volume', item['labels'].get('drive', 'ALL'))
            vol_data.setdefault(vol, {})['size'] = item['val']

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

        total_free = 0
        total_size = 0
        for vol, d in vol_data.items():
            if not _should_include_volume(vol):
                continue
            if 'size' in d and d['size'] > 0:
                free = d.get('free', 0)
                used_pct = round(((d['size'] - free) / d['size']) * 100, 1)
                result['volumes'].append({
                    'volume': vol,
                    'size_bytes': d['size'],
                    'free_bytes': free,
                    'used_percent': used_pct
                })
                total_free += free
                total_size += d['size']
        if total_size > 0:
            result['disk'] = round(((total_size - total_free) / total_size) * 100, 1)

        nic_items = [item['val'] for k, items in metrics_map.items() if 'windows_net_current_bandwidth_bytes' in k for item in items]
        if nic_items:
            result['net_rx'] = sum(nic_items)
            result['net_tx'] = sum(nic_items)

        return result


class ServiceChecker:
    def __init__(self):
        self.interval = 60
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self._check_loop())

    async def stop(self):
        self.running = False

    async def _check_loop(self):
        await asyncio.sleep(10)
        while self.running:
            try:
                await self.check_all()
            except Exception as e:
                import traceback
                print(f"[ERROR] ServiceChecker: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
            await asyncio.sleep(self.interval)

    async def check_all(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, target_url, timeout, expected_status, enabled FROM services WHERE enabled=1")
        services = cursor.fetchall()
        conn.close()

        if not services:
            return

        async with httpx.AsyncClient(timeout=15.0) as client:
            tasks = []
            for s in services:
                sid, name, url, timeout, expected, enabled = s
                tasks.append(self._check_one(client, sid, name, url, timeout, expected))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            ok = sum(1 for r in results if r is True)

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
