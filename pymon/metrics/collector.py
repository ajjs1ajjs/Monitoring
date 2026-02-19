"""Metrics collector and registry"""

from collections import defaultdict
from threading import Lock
from typing import Iterator

from pymon.metrics.models import Label, Metric, MetricSeries, MetricType


class MetricsRegistry:
    def __init__(self):
        self._metrics: dict[str, dict[str, Metric]] = defaultdict(dict)
        self._series: dict[str, MetricSeries] = {}
        self._lock = Lock()

    def register(
        self,
        name: str,
        metric_type: MetricType,
        help_text: str = "",
        labels: list[Label] | None = None,
    ) -> MetricSeries:
        with self._lock:
            if name not in self._series:
                series = MetricSeries(name=name, metric_type=metric_type, help_text=help_text, labels=labels or [])
                self._series[name] = series
            return self._series[name]

    def set(self, name: str, value: float, labels: list[Label] | None = None) -> None:
        with self._lock:
            series = self._series.get(name)
            if not series:
                raise ValueError(f"Metric {name} not registered")

            metric = Metric(
                name=name, value=value, metric_type=series.metric_type, labels=labels or [], help_text=series.help_text
            )
            self._metrics[name][metric.labels_key] = metric

    def inc(self, name: str, value: float = 1.0, labels: list[Label] | None = None) -> None:
        with self._lock:
            series = self._series.get(name)
            if not series:
                raise ValueError(f"Metric {name} not registered")

            labels = labels or []
            key = Metric(name=name, value=0, metric_type=series.metric_type, labels=labels).labels_key

            if key in self._metrics[name]:
                self._metrics[name][key].value += value
            else:
                self.set(name, value, labels)

    def observe(self, name: str, value: float, labels: list[Label] | None = None) -> None:
        self.set(name, value, labels)

    def get_metric(self, name: str, labels: list[Label] | None = None) -> Metric | None:
        key = Metric(name=name, value=0, metric_type=MetricType.GAUGE, labels=labels or []).labels_key
        return self._metrics.get(name, {}).get(key)

    def get_all_metrics(self) -> Iterator[Metric]:
        with self._lock:
            for name_metrics in self._metrics.values():
                yield from name_metrics.values()

    def export_prometheus(self) -> str:
        lines = []
        for name, series in sorted(self._series.items()):
            lines.append(f"# HELP {name} {series.help_text}")
            lines.append(f"# TYPE {name} {series.metric_type.value}")

            for metric in self._metrics.get(name, {}).values():
                label_str = ""
                if metric.labels:
                    label_str = "{" + ", ".join(f'{l.name}="{l.value}"' for l in metric.labels) + "}"
                lines.append(f"{name}{label_str} {metric.value}")

        return "\n".join(lines)


registry = MetricsRegistry()


class Counter:
    def __init__(self, name: str, help_text: str = "", labels: list[Label] | None = None):
        self.name = name
        registry.register(name, MetricType.COUNTER, help_text, labels)
        self._base_labels = labels or []

    def inc(self, value: float = 1.0, labels: list[Label] | None = None) -> None:
        registry.inc(self.name, value, labels or self._base_labels)


class Gauge:
    def __init__(self, name: str, help_text: str = "", labels: list[Label] | None = None):
        self.name = name
        registry.register(name, MetricType.GAUGE, help_text, labels)
        self._base_labels = labels or []

    def set(self, value: float, labels: list[Label] | None = None) -> None:
        registry.set(self.name, value, labels or self._base_labels)

    def inc(self, value: float = 1.0, labels: list[Label] | None = None) -> None:
        metric = registry.get_metric(self.name, labels or self._base_labels)
        current = metric.value if metric else 0
        registry.set(self.name, current + value, labels or self._base_labels)

    def dec(self, value: float = 1.0, labels: list[Label] | None = None) -> None:
        self.inc(-value, labels)


class Histogram:
    def __init__(
        self,
        name: str,
        help_text: str = "",
        buckets: list[float] | None = None,
        labels: list[Label] | None = None,
    ):
        self.name = name
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        registry.register(name, MetricType.HISTOGRAM, help_text, labels)
        self._base_labels = labels or []

    def observe(self, value: float, labels: list[Label] | None = None) -> None:
        registry.observe(self.name, value, labels or self._base_labels)
