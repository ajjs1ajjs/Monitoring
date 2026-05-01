"""DTO models for API input/output using Pydantic."""

from datetime import datetime, timezone
from typing import Any, List, Optional

import pydantic


class ServerCreate(pydantic.BaseModel):  # noqa: D101
    """Input model for creating a server."""

    name: str = pydantic.Field(..., min_length=1, max_length=256)
    host: Optional[str] = None
    os_type: Optional[str] = "linux"
    agent_port: Optional[int] = 8080
    enabled: bool = True


class ServerResponse(pydantic.BaseModel):  # noqa: D101
    """Output model for server list."""

    id: int
    name: str
    host: Optional[str]
    os_type: Optional[str]
    agent_port: Optional[int]
    enabled: bool
    last_status: Optional[str]
    cpu_percent: float
    memory_percent: float


class MetricResponse(pydantic.BaseModel):  # noqa: D101, D417
    """Output model for metric data."""

    server_id: int
    metric: str
    values: List[float]
    timestamps: List[datetime]


class CacheHitResponse(pydantic.BaseModel):  # noqa: D101
    """Indicates cache was hit or not."""

    cached: bool
    ttl_remaining: Optional[int] = None


class ErrorDetail(pydantic.BaseModel):  # noqa: D101, D417
    """Detailed API error information."""

    code: str
    message: str
    details: dict = pydantic.Field(default_factory=dict)
