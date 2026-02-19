"""FastAPI endpoints for metrics collection and querying"""

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pymon.auth import (
    User,
    UserLogin,
    UserCreate,
    Token,
    PasswordChange,
    get_current_user,
    get_admin_user,
    init_auth_tables,
    authenticate_user,
    create_user,
    change_password,
    create_api_key,
    list_api_keys,
    delete_api_key,
)
from pymon.metrics.collector import registry
from pymon.metrics.models import Label, MetricType
from pymon.storage import get_storage


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


class APIKeyCreate(BaseModel):
    name: str


api = FastAPI(title="PyMon API", version="0.1.0", docs_url="/api-docs", redoc_url="/api-redoc")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.on_event("startup")
async def startup():
    init_auth_tables()


@api.get("/api/v1/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@api.post("/api/v1/auth/login", response_model=Token)
async def login(data: UserLogin):
    return authenticate_user(data.username, data.password)


@api.post("/api/v1/auth/register", response_model=User)
async def register(data: UserCreate, current_user: User = Depends(get_admin_user)):
    return create_user(data.username, data.password, data.is_admin)


@api.get("/api/v1/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@api.post("/api/v1/auth/change-password")
async def change_user_password(data: PasswordChange, current_user: User = Depends(get_current_user)):
    change_password(current_user.id, data.current_password, data.new_password)
    return {"status": "ok", "message": "Password changed successfully"}


@api.post("/api/v1/auth/api-keys")
async def create_new_api_key(data: APIKeyCreate, current_user: User = Depends(get_current_user)):
    key = create_api_key(current_user.id, data.name)
    return {"api_key": key, "name": data.name}


@api.get("/api/v1/auth/api-keys")
async def list_user_api_keys(current_user: User = Depends(get_current_user)):
    return {"api_keys": list_api_keys(current_user.id)}


@api.delete("/api/v1/auth/api-keys/{key_id}")
async def delete_user_api_key(key_id: int, current_user: User = Depends(get_current_user)):
    if delete_api_key(current_user.id, key_id):
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="API key not found")


@api.post("/api/v1/metrics")
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
        name=payload.name, value=payload.value, metric_type=metric_type, labels=labels, help_text=payload.help_text
    )
    await storage.write(metric)

    return {"status": "ok"}


@api.get("/api/v1/metrics")
async def list_metrics(current_user: User = Depends(get_current_user)):
    return {"metrics": [m.to_dict() for m in registry.get_all_metrics()]}


@api.get("/api/v1/query")
async def query_metrics(
    query: str,
    start: datetime | None = None,
    end: datetime | None = None,
    step: int = 60,
    current_user: User = Depends(get_current_user),
):
    storage = get_storage()
    end = end or datetime.utcnow()
    start = start or (end - timedelta(hours=1))

    points = await storage.read(query, start, end, step=step)
    return {
        "query": query,
        "result": [{"timestamp": p.timestamp.isoformat(), "value": p.value} for p in points],
    }


@api.post("/api/v1/query_range")
async def query_range(req: QueryRequest, current_user: User = Depends(get_current_user)):
    storage = get_storage()

    points = await storage.read(req.query, req.start, req.end, step=req.step)
    return {
        "query": req.query,
        "result": [{"timestamp": p.timestamp.isoformat(), "value": p.value} for p in points],
    }


@api.get("/api/v1/series")
async def list_series(current_user: User = Depends(get_current_user)):
    storage = get_storage()
    names = await storage.get_series_names()
    return {"series": names}


@api.get("/metrics", response_class=PlainTextResponse)
async def prometheus_export():
    return registry.export_prometheus()


@api.post("/api/v1/write")
async def remote_write(request: Request, current_user: User = Depends(get_current_user)):
    body = await request.body()
    return {"status": "ok", "size": len(body)}
