"""Alerting system"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable

from pymon.metrics.collector import registry


class AlertState(Enum):
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class Alert:
    name: str
    state: AlertState
    message: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    fired_at: datetime | None = None
    resolved_at: datetime | None = None


AlertHandler = Callable[[Alert], None]


class AlertRule:
    def __init__(
        self,
        name: str,
        expr: str,
        threshold: float,
        duration: int = 0,
        labels: dict[str, str] | None = None,
        annotations: dict[str, str] | None = None,
    ):
        self.name = name
        self.expr = expr
        self.threshold = threshold
        self.duration = duration
        self.labels = labels or {}
        self.annotations = annotations or {}
        self._pending_since: datetime | None = None

    def evaluate(self) -> Alert | None:
        metric = registry.get_metric(self.expr)
        if not metric:
            return None

        if metric.value > self.threshold:
            if self._pending_since is None:
                self._pending_since = datetime.utcnow()
                return Alert(
                    name=self.name,
                    state=AlertState.PENDING,
                    message=f"{self.expr} = {metric.value} > {self.threshold}",
                    value=metric.value,
                    labels=self.labels,
                )

            if self.duration > 0:
                elapsed = (datetime.utcnow() - self._pending_since).total_seconds()
                if elapsed >= self.duration:
                    return Alert(
                        name=self.name,
                        state=AlertState.FIRING,
                        message=f"{self.expr} = {metric.value} > {self.threshold}",
                        value=metric.value,
                        labels=self.labels,
                        fired_at=datetime.utcnow(),
                    )
            else:
                return Alert(
                    name=self.name,
                    state=AlertState.FIRING,
                    message=f"{self.expr} = {metric.value} > {self.threshold}",
                    value=metric.value,
                    labels=self.labels,
                    fired_at=datetime.utcnow(),
                )
        else:
            if self._pending_since is not None:
                self._pending_since = None
                return Alert(
                    name=self.name,
                    state=AlertState.RESOLVED,
                    message=f"{self.expr} = {metric.value} <= {self.threshold}",
                    value=metric.value,
                    labels=self.labels,
                    resolved_at=datetime.utcnow(),
                )

        return None


class AlertManager:
    def __init__(self):
        self._rules: dict[str, AlertRule] = {}
        self._handlers: list[AlertHandler] = []
        self._alerts: list[Alert] = []

    def add_rule(self, rule: AlertRule) -> None:
        self._rules[rule.name] = rule

    def add_handler(self, handler: AlertHandler) -> None:
        self._handlers.append(handler)

    def evaluate_all(self) -> list[Alert]:
        fired = []
        for rule in self._rules.values():
            alert = rule.evaluate()
            if alert:
                self._alerts.append(alert)
                fired.append(alert)
                for handler in self._handlers:
                    handler(alert)
        return fired

    def get_alerts(self, state: AlertState | None = None) -> list[Alert]:
        if state:
            return [a for a in self._alerts if a.state == state]
        return self._alerts


alert_manager = AlertManager()
