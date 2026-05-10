from typing import Any, Dict, List

from pydantic import BaseModel


class HistoryResponse(BaseModel):
    history: List[Dict[str, Any]]


class ExportAllResponse(BaseModel):
    range: str
    servers: List[Dict[str, Any]]


class AllServersExportResponse(BaseModel):
    range: str
    servers: List[Dict[str, Any]]


class HistoryAllResponse(BaseModel):
    range: str
    servers: List[Dict[str, Any]]


class UptimeTimelineResponse(BaseModel):
    timeline: List[Dict[str, Any]]
    uptime_percent: float


class DiskBreakdownResponse(BaseModel):
    disks: List[Dict[str, Any]]


class BackupListResponse(BaseModel):
    backups: List[Dict[str, Any]]


class BackupCreateResponse(BaseModel):
    status: str
    filename: str | None = None


class MaintenanceToggle(BaseModel):
    is_maintenance: bool


class ServiceCreate(BaseModel):
    name: str
    target_url: str
    check_type: str = "http"
    interval: int = 60
    timeout: int = 10
