"""Configuration loader and manager, using Pydantic for strict validation."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseModel, Field, ValidationError


class StaticConfig(BaseModel):
    targets: List[str]
    labels: Dict[str, str] = Field(default_factory=dict)


class ScrapeConfig(BaseModel):
    job_name: str
    scrape_interval: int = 15  # seconds
    scrape_timeout: int = 10  # seconds
    metrics_path: str = "/metrics"
    honor_labels: bool = False
    static_configs: List[StaticConfig] = Field(default_factory=list)


class AlertRule(BaseModel):
    name: str
    expr: str = Field(..., description="PromQL query expression")
    threshold: float = 0.0
    duration: int = 0  # seconds
    severity: str = "warning"
    message: str = ""


class NotificationConfig(BaseModel):
    """Handles connection details for various alerting channels."""

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
    webhook_headers: Dict[str, str] = Field(default_factory=dict)


class ServerConfig(BaseModel):
    """Configuration for the main monitoring server."""

    port: int = 8090
    host: str = "0.0.0.0"
    domain: str = "localhost"


class StorageConfig(BaseModel):
    """Configuration for the data storage backend."""

    backend: str = "sqlite"
    path: str = "pymon.db"
    retention_hours: int = 168  # Hours of retention


class AuthConfig(BaseModel):
    """Authentication credentials and policies."""

    admin_username: str = "admin"
    admin_password: str = "changeme"
    jwt_expire_hours: int = 24  # Hours token is valid


class BackupConfig(BaseModel):
    """Configuration for scheduled database backups."""

    enabled: bool = True
    max_backups: int = 10
    backup_dir: str = "./backups"
    schedule: str = "0 2 * * *"  # Cron format


class PyMonConfig(BaseModel):
    """The root configuration model for the entire monitoring system."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    backup: BackupConfig = Field(default_factory=BackupConfig)
    scrape_configs: List[ScrapeConfig] = Field(default_factory=list)
    alerting_rules: List[AlertRule] = Field(default_factory=list)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "PyMonConfig":
        """Loads configuration from a YAML file and validates it using Pydantic."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return cls.from_dict(data)  # type: ignore
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {path}")
        except ValidationError as e:
            print(f"\n[ERROR] Configuration Validation Failed in {path}:")
            for error in e.errors():
                print(f"- Field '{error['loc'][0]}': {error['msg']}")
            raise ValueError("Invalid configuration structure or data types.") from e

    @classmethod
    def from_dict(cls, data: dict) -> "PyMonConfig":
        """Validates and constructs the config model from a dictionary."""
        try:
            return cls(**data)
        except ValidationError as e:
            print("\n[ERROR] Configuration Validation Failed:")
            for error in e.errors():
                print(f"- Field '{error['loc'][0]}': {error['msg']}")
            raise ValueError("Invalid configuration structure or data types.") from e

    @classmethod  # type: ignore
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
                # If not provided, default to a secure placeholder to avoid weak defaults
                admin_password=a.get("admin_password", "changeme"),
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
                    static_configs.append(
                        StaticConfig(
                            targets=ssc.get("targets", []),
                            labels=ssc.get("labels", {}),
                        )
                    )

                config.scrape_configs.append(
                    ScrapeConfig(
                        job_name=sc.get("job_name", "default"),
                        scrape_interval=_parse_duration(sc.get("scrape_interval", "15s")),
                        scrape_timeout=_parse_duration(sc.get("scrape_timeout", "10s")),
                        metrics_path=sc.get("metrics_path", "/metrics"),
                        honor_labels=sc.get("honor_labels", False),
                        static_configs=static_configs,
                    )
                )

        if "alerting" in data:
            alerting = data["alerting"]
            for rule in alerting.get("rules", []):
                config.alerting_rules.append(
                    AlertRule(
                        name=rule.get("name", ""),
                        expr=rule.get("expr", ""),
                        threshold=rule.get("threshold", 0),
                        duration=_parse_duration(rule.get("duration", "0s")),
                        severity=rule.get("severity", "warning"),
                        message=rule.get("message", ""),
                    )
                )

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
                    "static_configs": [{"targets": ssc.targets, "labels": ssc.labels} for ssc in sc.static_configs],
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


def _parse_duration(value: Any) -> int:
    """Parses a duration string (e.g., '15s', 60, '2h') into total seconds."""
    if isinstance(value, int):
        return value

    try:
        value = str(value).strip()
    except Exception:
        raise TypeError("Duration must be a string or integer.")

    # Handle common suffixes for robustness
    if value.endswith("s"):
        seconds = int(value[:-1])
        if seconds < 0:
            raise ValueError("Duration cannot be negative.")
        return seconds
    elif value.endswith("m"):
        minutes = int(value[:-1])
        return minutes * 60
    elif value.endswith("h"):
        hours = int(value[:-1])
        return hours * 3600
    # Assuming 'd' for days is rare, but included for completeness
    elif value.endswith("d"):
        days = int(value[:-1])
        return days * 86400
    else:
        try:
            # Assume plain integer seconds if no suffix is provided
            return int(value)
        except ValueError:
            raise ValueError(f"Invalid duration format: {value}. Must end with s, m, h, or be a number.")


def load_config(path: str | None = None) -> PyMonConfig:
    """
    Loads configuration from specified path or environment variable.
    Automatically attempts common file extensions (.yml, .yaml, .json).
    """
    if path and os.path.exists(path):
        # If the path is explicitly given and exists, we prioritize it
        if path.lower().endswith((".yml", ".yaml")):
            return PyMonConfig.from_yaml(path)
        elif path.lower().endswith(".json"):
            with open(path, "r") as f:
                data = json.load(f)
            return PyMonConfig.from_dict(data)  # type: ignore

    # Fallback search logic (searching for the file by common extensions)
    config_path = path or os.getenv("CONFIG_PATH", "config.yml")

    for ext in [".yml", ".yaml", ".json"]:
        test_path = config_path
        if not test_path.lower().endswith(ext):  # type: ignore
            # Construct a potential alternative path for testing
            test_path = str(Path(config_path).with_suffix(ext))  # type: ignore

        if os.path.exists(test_path):  # type: ignore
            try:
                print(f"Attempting to load configuration from: {test_path}")
                if ext in [".yml", ".yaml"]:
                    return PyMonConfig.from_yaml(test_path)  # type: ignore
                elif ext == ".json":
                    with open(test_path, "r") as f:  # type: ignore
                        data = json.load(f)
                    return PyMonConfig.from_dict(data)  # type: ignore
            except Exception as e:
                print(f"[WARNING] Could not load configuration from {test_path}: {e}")
                continue  # Try next extension

    # If no config was loaded successfully
    raise FileNotFoundError("Could not find or validate a valid configuration file (.yml, .yaml, or .json).")
