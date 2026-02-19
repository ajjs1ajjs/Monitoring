"""Configuration loader and manager"""

import os
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

import yaml


@dataclass
class StaticConfig:
    targets: list[str]
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class ScrapeConfig:
    job_name: str
    scrape_interval: int = 15
    scrape_timeout: int = 10
    metrics_path: str = "/metrics"
    honor_labels: bool = False
    static_configs: list[StaticConfig] = field(default_factory=list)


@dataclass
class AlertRule:
    name: str
    expr: str
    threshold: float
    duration: int = 0
    severity: str = "warning"
    message: str = ""


@dataclass
class NotificationConfig:
    enabled: bool = False
    
    # Email
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    email_to: str = ""
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    # Slack
    slack_webhook_url: str = ""
    
    # Discord
    discord_webhook_url: str = ""
    
    # Generic webhook
    webhook_url: str = ""
    webhook_headers: dict = field(default_factory=dict)


@dataclass
class ServerConfig:
    port: int = 8090
    host: str = "0.0.0.0"
    domain: str = "localhost"


@dataclass
class StorageConfig:
    backend: str = "sqlite"
    path: str = "pymon.db"
    retention_hours: int = 168


@dataclass
class AuthConfig:
    admin_username: str = "admin"
    admin_password: str = "admin"
    jwt_expire_hours: int = 24


@dataclass
class BackupConfig:
    enabled: bool = True
    max_backups: int = 10
    backup_dir: str = "/etc/pymon/backups"
    schedule: str = "0 2 * * *"


@dataclass
class PyMonConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    scrape_configs: list[ScrapeConfig] = field(default_factory=list)
    alerting_rules: list[AlertRule] = field(default_factory=list)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    
    @classmethod
    def from_yaml(cls, path: str) -> "PyMonConfig":
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: dict) -> "PyMonConfig":
        config = cls()
        
        if "server" in data:
            s = data["server"]
            config.server = ServerConfig(
                port=s.get("port", 8090),
                host=s.get("host", "0.0.0.0"),
                domain=s.get("domain", "localhost"),
            )
        
        if "storage" in data:
            st = data["storage"]
            config.storage = StorageConfig(
                backend=st.get("backend", "sqlite"),
                path=st.get("path", "pymon.db"),
                retention_hours=st.get("retention_hours", 168),
            )
        
        if "auth" in data:
            a = data["auth"]
            config.auth = AuthConfig(
                admin_username=a.get("admin_username", "admin"),
                admin_password=a.get("admin_password", "admin"),
                jwt_expire_hours=a.get("jwt_expire_hours", 24),
            )
        
        if "backup" in data:
            b = data["backup"]
            config.backup = BackupConfig(
                enabled=b.get("enabled", True),
                max_backups=b.get("max_backups", 10),
                backup_dir=b.get("backup_dir", "/etc/pymon/backups"),
                schedule=b.get("schedule", "0 2 * * *"),
            )
        
        if "scrape_configs" in data:
            for sc in data["scrape_configs"]:
                static_configs = []
                for ssc in sc.get("static_configs", []):
                    static_configs.append(StaticConfig(
                        targets=ssc.get("targets", []),
                        labels=ssc.get("labels", {}),
                    ))
                
                config.scrape_configs.append(ScrapeConfig(
                    job_name=sc.get("job_name", "default"),
                    scrape_interval=_parse_duration(sc.get("scrape_interval", "15s")),
                    scrape_timeout=_parse_duration(sc.get("scrape_timeout", "10s")),
                    metrics_path=sc.get("metrics_path", "/metrics"),
                    honor_labels=sc.get("honor_labels", False),
                    static_configs=static_configs,
                ))
        
        if "alerting" in data:
            alerting = data["alerting"]
            for rule in alerting.get("rules", []):
                config.alerting_rules.append(AlertRule(
                    name=rule.get("name", ""),
                    expr=rule.get("expr", ""),
                    threshold=rule.get("threshold", 0),
                    duration=_parse_duration(rule.get("duration", "0s")),
                    severity=rule.get("severity", "warning"),
                    message=rule.get("message", ""),
                ))
        
        if "notifications" in data:
            n = data["notifications"]
            config.notifications = NotificationConfig(
                enabled=n.get("email", {}).get("enabled", False),
                smtp_server=n.get("email", {}).get("smtp_server", ""),
                smtp_port=n.get("email", {}).get("smtp_port", 587),
                smtp_user=n.get("email", {}).get("smtp_user", ""),
                smtp_pass=n.get("email", {}).get("smtp_pass", ""),
                email_to=n.get("email", {}).get("to", ""),
                telegram_bot_token=n.get("telegram", {}).get("bot_token", ""),
                telegram_chat_id=n.get("telegram", {}).get("chat_id", ""),
                slack_webhook_url=n.get("slack", {}).get("webhook_url", ""),
                discord_webhook_url=n.get("discord", {}).get("webhook_url", ""),
                webhook_url=n.get("webhook", {}).get("url", ""),
                webhook_headers=n.get("webhook", {}).get("headers", {}),
            )
        
        return config
    
    def to_yaml(self, path: str) -> None:
        data = self.to_dict()
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def to_dict(self) -> dict:
        return {
            "server": {
                "port": self.server.port,
                "host": self.server.host,
                "domain": self.server.domain,
            },
            "storage": {
                "backend": self.storage.backend,
                "path": self.storage.path,
                "retention_hours": self.storage.retention_hours,
            },
            "auth": {
                "admin_username": self.auth.admin_username,
                "admin_password": self.auth.admin_password,
                "jwt_expire_hours": self.auth.jwt_expire_hours,
            },
            "backup": {
                "enabled": self.backup.enabled,
                "max_backups": self.backup.max_backups,
                "backup_dir": self.backup.backup_dir,
                "schedule": self.backup.schedule,
            },
            "scrape_configs": [
                {
                    "job_name": sc.job_name,
                    "scrape_interval": f"{sc.scrape_interval}s",
                    "scrape_timeout": f"{sc.scrape_timeout}s",
                    "metrics_path": sc.metrics_path,
                    "honor_labels": sc.honor_labels,
                    "static_configs": [
                        {"targets": ssc.targets, "labels": ssc.labels}
                        for ssc in sc.static_configs
                    ],
                }
                for sc in self.scrape_configs
            ],
            "alerting": {
                "enabled": len(self.alerting_rules) > 0,
                "rules": [
                    {
                        "name": r.name,
                        "expr": r.expr,
                        "threshold": r.threshold,
                        "duration": f"{r.duration}s",
                        "severity": r.severity,
                        "message": r.message,
                    }
                    for r in self.alerting_rules
                ],
            },
        }


def _parse_duration(value: str | int) -> int:
    if isinstance(value, int):
        return value
    
    value = str(value).strip()
    if value.endswith("s"):
        return int(value[:-1])
    elif value.endswith("m"):
        return int(value[:-1]) * 60
    elif value.endswith("h"):
        return int(value[:-1]) * 3600
    elif value.endswith("d"):
        return int(value[:-1]) * 86400
    else:
        return int(value)


def load_config(path: str | None = None) -> PyMonConfig:
    if path and os.path.exists(path):
        if path.endswith((".yml", ".yaml")):
            return PyMonConfig.from_yaml(path)
    
    config_path = path or os.getenv("CONFIG_PATH", "config.yml")
    
    for ext in [".yml", ".yaml", ".json"]:
        test_path = config_path
        if not test_path.endswith(ext):
            test_path = Path(config_path).stem + ext
        if os.path.exists(test_path):
            if ext in [".yml", ".yaml"]:
                return PyMonConfig.from_yaml(test_path)
    
    return PyMonConfig()
