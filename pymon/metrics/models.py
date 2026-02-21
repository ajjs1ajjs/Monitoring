from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Label:
    name: str
    value: str


@dataclass
class Metric:
    name: str
    value: float
    metric_type: MetricType
    labels: list[Label] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    help_text: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "labels": [{"name": l.name, "value": l.value} for l in self.labels],
            "timestamp": self.timestamp.isoformat(),
            "help": self.help_text,
        }

    @property
    def labels_key(self) -> str:
        return ",".join(f"{l.name}={l.value}" for l in sorted(self.labels, key=lambda x: x.name))


@dataclass
class MetricSeries:
    name: str
    metric_type: MetricType
    help_text: str = ""
    labels: list[Label] = field(default_factory=list)
