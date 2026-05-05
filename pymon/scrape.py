"""Scrape manager for collecting metrics from targets (Prometheus-style)"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from pymon.config import PyMonConfig
from pymon.metrics.collector import Counter, Gauge, Histogram, registry
from pymon.metrics.models import Label, MetricType
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
        self._tasks: list = []
        self._cpu_history = {}  # Store {target: (idle_last, total_last)}
        self._down_alerted = set()  # Server IDs already alerted as down

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

        print(f"ScrapeManager: {len(self.targets)} targets configured")

    async def execute_scrape(self, target: ScrapeTarget) -> ScrapeResult:
        """Perform a scrape and update server status in the database."""
        result = await self.scrape_target(target)

        labels = [Label(name="job", value=target.job_name), Label(name="target", value=target.target)]
        self.scrape_total.inc()

        if result.success:
            self.scrape_success.inc()
            self.up_gauge.set(1, labels)
            self._update_server_status(target.target, result.metrics or {}, True, server_id=target.server_id)
        else:
            self.scrape_failures.inc()
            self.up_gauge.set(0, labels)
            self._update_server_status(target.target, {}, False, result.error, server_id=target.server_id)

        self.response_time.set(result.latency_ms / 1000, labels)
        return result

    async def scrape_target(self, target: ScrapeTarget) -> ScrapeResult:

        result = ScrapeResult(target=target, success=False, timestamp=datetime.now(timezone.utc), metrics={})

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
                    result.metrics = await self._parse_prometheus_response(response.text, target)
                    result.metrics_count = len(result.metrics)

        except httpx.TimeoutException:
            result.error = "timeout"
        except httpx.ConnectError:
            result.error = "connection_refused"
        except Exception as e:
            result.error = str(e)[:100]

        return result

    async def _parse_prometheus_response(self, content: str, target: ScrapeTarget) -> dict:
        # Fallback: Get disk info via PowerShell only for LOCAL target if exporter doesn't provide it
        disk_info = {}
        is_local = any(x in target.target for x in ["localhost", "127.0.0.1", "::1"])

        if is_local:
            try:
                import subprocess

                ps = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        "Get-WmiObject Win32_LogicalDisk | Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if ps.returncode == 0 and ps.stdout.strip():
                    try:
                        disks = json.loads(ps.stdout)
                        if isinstance(disks, dict) and "DeviceID" in disks:
                            disks = [disks]
                        for d in disks:
                            vol = d.get("DeviceID", "")
                            if vol and d.get("Size"):
                                disk_info[vol] = {
                                    "volume": vol,
                                    "free": float(d.get("FreeSpace", 0)),
                                    "size": float(d.get("Size", 0)),
                                }
                    except Exception:
                        pass
            except Exception:
                pass

        from typing import Any

        metrics: dict[str, Any] = {}
        storage = get_storage()

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            try:
                name = None
                value = None
                labels = []
                if "{" in line:
                    name_part, value_part = line.split("{", 1)
                    name = name_part.strip()
                    labels_part, value_str = value_part.rsplit("}", 1)
                    value = float(value_str.strip())
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

                if name and value is not None:
                    metrics[name] = value
                    print(f"DEBUG PARSE: name={name}, value={value}")

                    label_objs = list(target.labels.items()) if not target.honor_labels else []
                    label_objs.extend(labels)
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

        # Calculate node_exporter metrics with labels
        try:
            cpu_idle = 0
            cpu_user = 0
            cpu_system = 0
            mem_total = 0
            mem_avail = 0
            disk_total = 0
            disk_avail = 0

            for k, v in metrics.items():
                # CPU metrics - exact match patterns
                if k == "node_cpu_seconds_total" and "idle" in k:
                    cpu_idle = max(cpu_idle, v)
                elif k == "node_cpu_seconds_total" and "user" in k:
                    cpu_user = max(cpu_user, v)
                elif k == "node_cpu_seconds_total" and "system" in k:
                    cpu_system = max(cpu_system, v)
                elif "cpu_seconds_total" in k:
                    if "idle" in k:
                        cpu_idle = max(cpu_idle, v)
                    elif "user" in k:
                        cpu_user = max(cpu_user, v)
                    elif "system" in k:
                        cpu_system = max(cpu_system, v)

                # Memory metrics - exact match
                if k == "node_memory_MemTotal_bytes":
                    mem_total = max(mem_total, v)
                elif k == "node_memory_MemAvailable_bytes":
                    mem_avail = max(mem_avail, v)
                # Also try partial match
                elif "MemTotal" in k:
                    mem_total = max(mem_total, v)
                elif "MemAvailable" in k:
                    mem_avail = max(mem_avail, v)

                # Disk metrics - підтримка різних варіацій імен
                k_lower = k.lower()
                if "filesystem_size_bytes" in k_lower or "filesystem_size" in k_lower:
                    # Try to extract mountpoint from labels embedded in metric name (if present)
                    mount = None
                    import re

                    m = re.search(r'mountpoint="([^"]+)"', k)
                    if m:
                        mount = m.group(1)
                    # Пропустимо невідомі mountpoint або системні
                    if not mount or mount == "unknown" or mount.startswith("/proc") or mount.startswith("/sys"):
                        continue
                    disk_total = max(disk_total, v)
                    print(f"DEBUG DISK: Found filesystem_size for {mount}: {k} = {v}")
                elif (
                    "filesystem_avail_bytes" in k_lower
                    or "filesystem_available" in k_lower
                    or "filesystem_free" in k_lower
                ):
                    mount = None
                    import re

                    m = re.search(r'mountpoint="([^"]+)"', k)
                    if m:
                        mount = m.group(1)
                    if not mount or mount == "unknown" or mount.startswith("/proc") or mount.startswith("/sys"):
                        continue
                    disk_avail = max(disk_avail, v)
                    print(f"DEBUG DISK: Found filesystem_avail for {mount}: {k} = {v}")

            # Calculate CPU
            if cpu_idle > 0:
                total_cpu = cpu_idle + cpu_user + cpu_system
                if total_cpu > 0:
                    metrics["node_cpu_calculated"] = 100 * (1 - cpu_idle / total_cpu)

            # Calculate Memory
            print(f"DEBUG: mem_total={mem_total}, mem_avail={mem_avail}")
            if mem_total > 0 and mem_avail > 0:
                metrics["node_memory_calculated"] = 100 * (1 - mem_avail / mem_total)
                print(f"DEBUG: memory % = {100 * (1 - mem_avail / mem_total):.1f}")

            # Calculate Disk
            if disk_total > 0 and disk_avail > 0:
                metrics["node_disk_calculated"] = 100 * (1 - disk_avail / disk_total)

        except Exception as e:
            print(f"Metric calc error: {e}")

        return metrics

    def _update_server_status(
        self, target: str, metrics: dict, success: bool, error: str = "", server_id: Optional[int] = None
    ):
        import os
        import sqlite3

        try:
            db_path = os.getenv("DB_PATH", "pymon.db")
            conn = sqlite3.connect(db_path, timeout=5)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            sid = None
            if server_id:
                sid = server_id
            else:
                server = c.execute(
                    "SELECT id FROM servers WHERE host = ? OR host LIKE ?", (target, f"{target}%")
                ).fetchone()
                if server:
                    sid = server["id"]

            if sid:
                now = datetime.now(timezone.utc).isoformat()

                if success:
                    # Parse CPU - support both node_exporter and windows_exporter
                    cpu = (
                        metrics.get("node_cpu_percent")
                        or metrics.get("cpu_usage_percent")
                        or metrics.get("node_cpu_calculated")
                        or 0
                    )
                    if not cpu:
                        idle = metrics.get("windows_cpu_time_total_idle", 0)
                        total = metrics.get("windows_cpu_time_total_all", 0)
                        if total > 0:
                            cpu = 100 * (1 - idle / total) if idle < total else 0

                    # Parse Memory - support both node_exporter and windows_exporter
                    memory = (
                        metrics.get("node_memory_percent")
                        or metrics.get("memory_usage_percent")
                        or metrics.get("node_memory_calculated")
                        or 0
                    )
                    if not memory:
                        mem_total = metrics.get("windows_cs_physical_memory_bytes", 0)
                        mem_free = metrics.get("windows_os_physical_memory_free_bytes", 0)
                        if mem_total > 0:
                            memory = 100 * (1 - mem_free / mem_total) if mem_free < mem_total else 0

                    # Parse Disk - support both node_exporter and windows_exporter
                    disk = (
                        metrics.get("node_disk_percent")
                        or metrics.get("disk_usage_percent")
                        or metrics.get("node_disk_calculated")
                        or 0
                    )
                    if not disk:
                        disk_total = metrics.get("windows_logical_disk_size_bytes", 0)
                        disk_free = metrics.get("windows_logical_disk_free_bytes", 0)
                        if disk_total > 0:
                            disk = 100 * (1 - disk_free / disk_total) if disk_free < disk_total else 0

                    network_rx = (
                        metrics.get("node_network_receive_bytes")
                        or metrics.get("node_network_receive_bytes_total")
                        or metrics.get("system_network_rx_bytes", 0)
                    )
                    network_tx = (
                        metrics.get("node_network_transmit_bytes")
                        or metrics.get("node_network_transmit_bytes_total")
                        or metrics.get("system_network_tx_bytes", 0)
                    )
                    uptime = (
                        metrics.get("node_boot_time_seconds")
                        or metrics.get("system_uptime_seconds")
                        or metrics.get("windows_system_system_up_time", "")
                    )
                    disk_info_json = metrics.get("_disk_info_json")
                    exporter_version = "active" if metrics.get("_exporter_detected") else "unknown"

                    c.execute(
                        """UPDATE servers SET
                        last_check = ?, last_status = 'up', error_message = NULL,
                        cpu_percent = ?, memory_percent = ?, disk_percent = ?,
                        network_rx = ?, network_tx = ?, uptime = ?, disk_info = ?,
                        exporter_version = ?
                        WHERE id = ?""",
                        (
                            now,
                            cpu,
                            memory,
                            disk,
                            network_rx,
                            network_tx,
                            str(uptime),
                            disk_info_json,
                            exporter_version,
                            sid,
                        ),
                    )

                    # Add to metrics history for charts
                    try:
                        c.execute(
                            """INSERT INTO metrics_history (server_id, cpu_percent, memory_percent, disk_percent, network_rx, network_tx, disk_info, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (sid, cpu, memory, disk, network_rx, network_tx, disk_info_json, now),
                        )
                        # Keep only 7 days of history to prevent DB bloat
                        c.execute("DELETE FROM metrics_history WHERE timestamp < datetime('now', '-7 days')")
                    except Exception as he:
                        print(f"History insert error: {he}")

                    # Broadcast update via WebSocket
                    try:
                        import asyncio

                        from pymon.api.endpoints import manager

                        if manager.loop and manager.loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                manager.broadcast(
                                    {
                                        "type": "server_update",
                                        "server_id": sid,
                                        "cpu": cpu,
                                        "memory": memory,
                                        "disk": disk,
                                        "status": "up",
                                    }
                                ),
                                manager.loop,
                            )
                    except Exception as e:
                        pass
                else:
                    c.execute(
                        """UPDATE servers SET
                        last_check = ?, last_status = 'down', error_message = ?
                        WHERE id = ?""",
                        (now, error, sid),
                    )

                conn.commit()

                # Phase 2.15: Check alerts for this server
                if success:
                    try:
                        import asyncio

                        asyncio.run(self._check_alerts(sid, cpu, memory, disk, now))
                        # Clear down state if it was previously down
                        self._down_alerted.discard(sid)
                    except Exception as ae:
                        print(f"Alert check failed: {ae}")
                else:
                    # Exporter Down alert
                    try:
                        if sid not in self._down_alerted:
                            self._down_alerted.add(sid)
                            import asyncio

                            asyncio.run(self._fire_exporter_down_alert(sid, target, error, now))
                    except Exception as ae:
                        print(f"Exporter Down alert failed: {ae}")

            conn.close()
        except Exception as e:
            print(f"Error updating server status: {e}")

    async def _check_alerts(self, server_id: int, cpu: float, memory: float, disk: float, timestamp: str):
        """Check active alert rules for the server and dispatch notifications."""
        import os
        import sqlite3

        from pymon.notifications import dispatcher

        try:
            db_path = os.getenv("DB_PATH", "pymon.db")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # Get active alerts
            alerts = c.execute("SELECT * FROM alerts WHERE enabled = 1").fetchall()

            # Get notification config from app state if available
            # For now, we'll try to find it in the DB or global config
            from pymon.config import load_config

            config = load_config(os.getenv("CONFIG_PATH", "config.yml"))
            notif_cfg = config.notifications

            for alert in alerts:
                triggered = False
                metric_val = 0

                if alert["metric"] == "cpu":
                    metric_val = cpu
                elif alert["metric"] == "memory":
                    metric_val = memory
                elif alert["metric"] == "disk":
                    metric_val = disk

                if alert["condition"] == ">":
                    triggered = metric_val > alert["threshold"]
                elif alert["condition"] == "<":
                    triggered = metric_val < alert["threshold"]

                if triggered:
                    # Check if already firing (to avoid spam)
                    # We can use a simple memory cache in ScrapeManager or a table
                    # For now, let's just send if triggered and log it
                    msg = f"🚨 <b>{alert['name']}</b> triggered on Server ID {server_id}!\nValue: {metric_val:.1f}%\nThreshold: {alert['threshold']}%"

                    channels = {}
                    if notif_cfg.enabled:
                        if notif_cfg.telegram_bot_token and notif_cfg.telegram_chat_id:
                            channels["telegram"] = {
                                "bot_token": notif_cfg.telegram_bot_token,
                                "chat_id": notif_cfg.telegram_chat_id,
                            }
                        if notif_cfg.discord_webhook_url:
                            channels["discord"] = {"webhook_url": notif_cfg.discord_webhook_url}

                    if channels:
                        dispatcher.dispatch(alert["name"], msg, channels)

                    # Log to audit logs
                    c.execute(
                        "INSERT INTO audit_logs (username, action, target, timestamp) VALUES (?, ?, ?, ?)",
                        ("system", f"Alert Triggered: {alert['name']}", f"Server {server_id}", timestamp),
                    )
                    conn.commit()

            conn.close()
        except Exception as e:
            print(f"Error in alert check: {e}")

    async def _fire_exporter_down_alert(self, server_id: int, target: str, error: str, timestamp: str):
        """Fire an alert when an exporter becomes unreachable."""
        import os
        import sqlite3

        from pymon.notifications import dispatcher

        try:
            db_path = os.getenv("DB_PATH", "pymon.db")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # Get server name
            server = c.execute("SELECT name, host FROM servers WHERE id = ?", (server_id,)).fetchone()
            server_name = server["name"] if server else f"ID {server_id}"
            server_host = server["host"] if server else target

            # Get notification config
            from pymon.config import load_config

            config = load_config(os.getenv("CONFIG_PATH", "config.yml"))
            notif_cfg = config.notifications

            msg = (
                f"🔴 <b>EXPORTER DOWN</b>\n\n"
                f"Server: <b>{server_name}</b>\n"
                f"Endpoint: {server_host}\n"
                f"Error: {error or 'unreachable'}\n"
                f"Time: {timestamp}"
            )

            channels = {}
            if notif_cfg.enabled:
                if notif_cfg.telegram_bot_token and notif_cfg.telegram_chat_id:
                    channels["telegram"] = {
                        "bot_token": notif_cfg.telegram_bot_token,
                        "chat_id": notif_cfg.telegram_chat_id,
                    }
                if notif_cfg.discord_webhook_url:
                    channels["discord"] = {"webhook_url": notif_cfg.discord_webhook_url}

            if channels:
                dispatcher.dispatch("Exporter Down", msg, channels)

            # Log to audit
            c.execute(
                "INSERT INTO audit_logs (username, action, target, timestamp) VALUES (?, ?, ?, ?)",
                ("system", "Exporter Down", f"{server_name} ({server_host})", timestamp),
            )
            conn.commit()
            conn.close()
            print(f"[ALERT] Exporter Down: {server_name} ({server_host}) - {error}")
        except Exception as e:
            print(f"Error firing exporter down alert: {e}")

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
        import time

        import httpx

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

                    # Fallback: Get disk info via PowerShell only for LOCAL target if exporter doesn't provide it
                    disk_info = {}
                    is_local = any(x in target.target for x in ["localhost", "127.0.0.1", "::1"])

                    if is_local:
                        try:
                            import subprocess

                            ps = subprocess.run(
                                [
                                    "powershell",
                                    "-NoProfile",
                                    "-Command",
                                    "Get-WmiObject Win32_LogicalDisk | Select-Object DeviceID,Size,FreeSpace | ConvertTo-Json",
                                ],
                                capture_output=True,
                                text=True,
                                timeout=10,
                            )
                            if ps.returncode == 0 and ps.stdout.strip():
                                try:
                                    disks = json.loads(ps.stdout)
                                    if isinstance(disks, dict) and "DeviceID" in disks:
                                        disks = [disks]
                                    for d in disks:
                                        vol = d.get("DeviceID", "")
                                        if vol and d.get("Size"):
                                            disk_info[vol] = {
                                                "volume": vol,
                                                "free": float(d.get("FreeSpace", 0)),
                                                "size": float(d.get("Size", 0)),
                                            }
                                except:
                                    pass
                        except:
                            pass

                    # Parse metrics - support both node_exporter and windows_exporter
                    from typing import Any

                    metrics: dict[str, Any] = {}
                    cpu_idle_total = 0.0
                    cpu_all_total = 0.0

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

                                # node_exporter (Linux) disk parsing
                                if name == "node_filesystem_free_bytes":
                                    import re

                                    mount_match = re.search(r'mountpoint="([^"]+)"', labels_part)
                                    if mount_match:
                                        mount = mount_match.group(1)
                                        # Filter out system and pseudo filesystems
                                        if not any(
                                            x in mount
                                            for x in ["/proc", "/sys", "/dev", "/run", "/tmp", "/var/lib/docker"]
                                        ):
                                            if mount not in disk_info:
                                                disk_info[mount] = {"volume": mount, "free": 0, "size": 0}
                                            disk_info[mount]["free"] = value

                                if name == "node_filesystem_size_bytes":
                                    import re

                                    mount_match = re.search(r'mountpoint="([^"]+)"', labels_part)
                                    if mount_match:
                                        mount = mount_match.group(1)
                                        if not any(
                                            x in mount
                                            for x in ["/proc", "/sys", "/dev", "/run", "/tmp", "/var/lib/docker"]
                                        ):
                                            if mount not in disk_info:
                                                disk_info[mount] = {"volume": mount, "free": 0, "size": 0}
                                            disk_info[mount]["size"] = value

                                # Aggregate CPU idle time from windows_exporter
                                if name == "windows_cpu_time_total":
                                    if 'mode="idle"' in labels_part:
                                        cpu_idle_total += value
                                    cpu_all_total += value

                                # Collect ALL disks from windows_exporter
                                import re

                                if name == "windows_logical_disk_free_bytes":
                                    vol_match = re.search(r'volume="([^"]+)"', labels_part)
                                    if vol_match:
                                        vol = vol_match.group(1)
                                        if vol not in disk_info:
                                            disk_info[vol] = {"volume": vol, "free": 0, "size": 0}
                                        disk_info[vol]["free"] = value
                                if name == "windows_logical_disk_size_bytes":
                                    vol_match = re.search(r'volume="([^"]+)"', labels_part)
                                    if vol_match:
                                        vol = vol_match.group(1)
                                        if vol not in disk_info:
                                            disk_info[vol] = {"volume": vol, "free": 0, "size": 0}
                                        disk_info[vol]["size"] = value

                                metrics[name] = value
                            else:
                                parts = line.split()
                                if len(parts) >= 2:
                                    name = parts[0]
                                    value = float(parts[1])
                                    metrics[name] = value
                        except:
                            continue

                    # Calculate CPU percentage from counters
                    if cpu_all_total > 0:
                        prev = self._cpu_history.get(target.target)
                        if prev:
                            idle_delta = cpu_idle_total - prev[0]
                            all_delta = cpu_all_total - prev[1]
                            if all_delta > 0:
                                cpu_percent = 100 * (1 - (idle_delta / all_delta))
                                metrics["cpu_usage_percent"] = max(0, min(100, cpu_percent))

                        self._cpu_history[target.target] = (cpu_idle_total, cpu_all_total)

                    # Handle Linux node_exporter metrics
                    if "node_cpu_seconds_total" in metrics or "node_load1" in metrics:
                        # CPU: use load1 as a fallback or calculation
                        if "node_load1" in metrics:
                            metrics["cpu_usage_percent"] = min(
                                100, (metrics["node_load1"] / 4) * 100
                            )  # Assuming 4 cores

                        # RAM: calculate usage from MemTotal and MemAvailable
                        if "node_memory_MemTotal_bytes" in metrics and "node_memory_MemAvailable_bytes" in metrics:
                            total = metrics["node_memory_MemTotal_bytes"]
                            avail = metrics["node_memory_MemAvailable_bytes"]
                            metrics["memory_usage_percent"] = ((total - avail) / total) * 100

                        # Disk: filesystem usage (all mountpoints)
                        disk_usage = 0
                        disk_info_json = {}
                        for k, v in metrics.items():
                            k_lower = k.lower()
                            if "filesystem_size_bytes" in k_lower:
                                # Отримуємо mount point з лейблів
                                import re

                                mount_match = re.search(r'mountpoint="([^"]+)"', k)
                                mount = mount_match.group(1) if mount_match else "unknown"

                                total_fs = v
                                # Шукаємо відповідний available
                                avail_key = k.replace("size_bytes", "avail_bytes")
                                avail_fs = metrics.get(avail_key, 0)

                                if total_fs > 0 and avail_fs >= 0:
                                    usage = ((total_fs - avail_fs) / total_fs) * 100
                                    disk_usage = max(disk_usage, usage)
                                    disk_info_json[mount] = round(usage, 1)
                                    print(f"DEBUG DISK: {mount} = {usage:.1f}% (size={total_fs}, avail={avail_fs})")

                        metrics["disk_usage_percent"] = disk_usage
                        if disk_info_json:
                            metrics["_disk_info_json"] = json.dumps(disk_info_json)
                            print(f"DEBUG DISK: Final disk_usage_percent = {disk_usage:.1f}%")

                    # Broadcast update via WebSocket
                    try:
                        import asyncio

                        from pymon.api.endpoints import manager

                        if hasattr(manager, "loop") and manager.loop:
                            asyncio.run_coroutine_threadsafe(
                                manager.broadcast(
                                    {
                                        "type": "server_update",
                                        "server_id": target.server_id,
                                        "cpu": metrics.get("cpu_usage_percent", 0),
                                        "memory": metrics.get("memory_usage_percent", 0),
                                        "disk": metrics.get("disk_usage_percent", 0),
                                        "status": "up",
                                    }
                                ),
                                manager.loop,
                            )
                    except Exception as e:
                        print(f"WS Broadcast error: {e}")
                    # Calculate disk percentages and get C: for main metric
                    disks_dict = {}  # {"C:": 94.2, "D:": 45.1}
                    c_drive_percent = 0
                    for vol, info in disk_info.items():
                        if info["size"] > 0:
                            pct = 100 * (1 - info["free"] / info["size"])
                            info["percent"] = pct
                            disks_dict[vol] = round(pct, 1)
                            if "C:" in vol:
                                c_drive_percent = pct
                                metrics["windows_logical_disk_free_bytes"] = info["free"]
                                metrics["windows_logical_disk_size_bytes"] = info["size"]
                                print(f"DEBUG DISK: C: = {pct:.1f}% (size={info['size']}, free={info['free']})")

                    # Set the main disk metric for Windows
                    if c_drive_percent > 0:
                        metrics["disk_usage_percent"] = c_drive_percent
                        print(f"DEBUG DISK: Set disk_usage_percent = {c_drive_percent:.1f}% for Windows")

                    metrics["_disk_info_json"] = json.dumps(disks_dict) if disks_dict else None

                    # Detect exporter version from build_info metrics
                    for key in metrics:
                        if "build_info" in key or "exporter_build_info" in key:
                            metrics["_exporter_detected"] = True
                            break

                    # Publish per-disk usage as Prometheus metrics with volume label
                    try:
                        if disk_info:
                            registry.register(
                                "disk_usage_percent", MetricType.GAUGE, "Disk usage percent per volume", None
                            )
                            for vol, info in disk_info.items():
                                vol_label = Label("volume", vol)
                                percent = info.get("percent", 0)
                                registry.set("disk_usage_percent", percent, [vol_label])
                                print(f"DEBUG DISK: Published per-disk metric for {vol} = {percent:.1f}%")
                    except Exception as e:
                        print(f"[DEBUG] failed to publish per-disk metric: {e}")

                    self._update_server_status(target.target, metrics, True, server_id=target.server_id)
                else:
                    self.scrape_failures.inc()
                    self.up_gauge.set(0, labels)
                    self._update_server_status(
                        target.target, {}, False, f"HTTP {response.status_code}", server_id=target.server_id
                    )
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
            if hasattr(task, "cancel"):
                try:
                    task.cancel()
                except:
                    pass

        self._tasks.clear()
        print("ScrapeManager stopped")

    async def close(self):
        self.stop()
        if hasattr(self, "_client") and self._client:
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
            labels={"job": "agents", "server": server["name"]},
            server_id=server["id"],
            honor_labels=scrape_config.honor_labels if scrape_config else False,
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
