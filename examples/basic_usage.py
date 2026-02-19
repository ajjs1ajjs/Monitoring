"""Example usage of PyMon"""

import asyncio

from pymon.client import PyMonClient, push_metric
from pymon.metrics.collector import Counter, Gauge, Histogram, registry
from pymon.metrics.models import Label
from pymon.metrics.system import SystemCollector
from pymon.storage import get_storage, init_storage


async def example_local():
    print("=== Local monitoring example ===")

    init_storage("memory")

    counter = Counter("app_requests_total", "Total application requests")
    gauge = Gauge("app_memory_bytes", "Application memory usage")
    histogram = Histogram("app_request_duration_seconds", "Request duration")

    for i in range(10):
        counter.inc()
        gauge.set(1024 * 1024 * (i + 1))
        histogram.observe(0.1 * i)

    print("\nMetrics in registry:")
    for m in registry.get_all_metrics():
        print(f"  {m.name}: {m.value}")

    print("\nPrometheus export:")
    print(registry.export_prometheus())


async def example_client():
    print("\n=== Remote client example ===")

    async with PyMonClient("http://localhost:8090") as client:
        await client.push("custom_metric", 42.5, "gauge", {"host": "server1", "region": "us-east"})
        print("Pushed metric to server")

        series = await client.list_series()
        print(f"Available series: {series}")


async def example_system_collector():
    print("\n=== System collector example ===")

    init_storage("memory")

    collector = SystemCollector(interval=5, labels=[Label("host", "localhost")])
    collector.start()

    await asyncio.sleep(6)

    print("System metrics collected:")
    for m in registry.get_all_metrics():
        if m.name.startswith("system_"):
            print(f"  {m.name}: {m.value}")

    collector.stop()


async def example_alerts():
    print("\n=== Alerting example ===")

    from pymon.alerts.manager import AlertManager, AlertRule

    manager = AlertManager()

    gauge = Gauge("cpu_usage", "CPU usage percentage")
    gauge.set(85)

    rule = AlertRule(name="HighCPU", expr="cpu_usage", threshold=80, duration=0, labels={"severity": "warning"})

    manager.add_rule(rule)

    def on_alert(alert):
        print(f"ALERT: {alert.name} - {alert.state.value} - {alert.message}")

    manager.add_handler(on_alert)

    alerts = manager.evaluate_all()
    for alert in alerts:
        print(f"Alert fired: {alert.name} -> {alert.state.value}")


def main():
    asyncio.run(example_local())
    asyncio.run(example_alerts())


if __name__ == "__main__":
    main()
