"""FastAPI API endpoints"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from pymon.auth import (
    User, UserLogin, Token, PasswordChange, APIKeyCreate,
    get_current_user, authenticate_user, change_password,
    create_api_key, list_api_keys, delete_api_key,
)
from pymon.metrics.collector import registry
from pymon.metrics.models import Label, MetricType
from pymon.storage import get_storage

api = APIRouter()

class MetricPayload(BaseModel):
    name: str
    value: float
    type: str = "gauge"
    labels: list[dict[str, str]] = []
    help_text: str = ""

class QueryRequest(BaseModel):
    query: str
    start: datetime
    end: datetime
    step: int = 60

@api.post("/auth/login", response_model=Token)
async def login(data: UserLogin):
    return authenticate_user(data.username, data.password)

@api.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api.post("/auth/change-password")
async def change_pwd(data: PasswordChange, current_user: User = Depends(get_current_user)):
    change_password(current_user.id, data.current_password, data.new_password)
    return {"status": "ok"}

@api.post("/auth/api-keys")
async def create_key(data: APIKeyCreate, current_user: User = Depends(get_current_user)):
    key = create_api_key(current_user.id, data.name)
    return {"api_key": key, "name": data.name}

@api.get("/auth/api-keys")
async def list_keys(current_user: User = Depends(get_current_user)):
    return {"api_keys": list_api_keys(current_user.id)}

@api.delete("/auth/api-keys/{key_id}")
async def delete_key(key_id: int, current_user: User = Depends(get_current_user)):
    if delete_api_key(current_user.id, key_id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="API key not found")

@api.post("/metrics")
async def ingest_metric(payload: MetricPayload, current_user: User = Depends(get_current_user)):
    storage = get_storage()
    try:
        metric_type = MetricType(payload.type)
    except ValueError:
        metric_type = MetricType.GAUGE

    labels = [Label(name=l["name"], value=l["value"]) for l in payload.labels]
    registry.register(payload.name, metric_type, payload.help_text, labels)
    registry.set(payload.name, payload.value, labels)

    from pymon.metrics.models import Metric
    metric = Metric(
        name=payload.name, value=payload.value, metric_type=metric_type,
        labels=labels, help_text=payload.help_text
    )
    await storage.write(metric)
    return {"status": "ok"}

@api.get("/metrics")
async def list_metrics(current_user: User = Depends(get_current_user)):
    return {"metrics": [m.to_dict() for m in registry.get_all_metrics()]}

@api.get("/query")
async def query_metrics(
    query: str,
    start: datetime | None = None,
    end: datetime | None = None,
    step: int = 60,
    current_user: User = Depends(get_current_user),
):
    storage = get_storage()
    end = end or datetime.now(timezone.utc)
    start = start or (end - timedelta(hours=1))
    points = await storage.read(query, start, end, step=step)
    return {
        "query": query,
        "result": [{"timestamp": p.timestamp.isoformat(), "value": p.value} for p in points],
    }

@api.get("/series")
async def list_series(current_user: User = Depends(get_current_user)):
    storage = get_storage()
    names = await storage.get_series_names()
    return {"series": names}

@api.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
