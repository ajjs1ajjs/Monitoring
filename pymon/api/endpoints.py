from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pymon.api.deps import manager
from pymon.api.routers import alerts, auth, backup, logs, metrics, reports, servers, services, settings
from pymon.metrics.prometheus import router as prometheus_router

api = APIRouter()

api.include_router(auth.router)
api.include_router(servers.router)
api.include_router(metrics.router)
api.include_router(alerts.router)
api.include_router(settings.router)
api.include_router(logs.router)
api.include_router(services.router)
api.include_router(reports.router)
api.include_router(backup.router)
api.include_router(prometheus_router)

@api.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@api.get("/health")
async def health():
    return {"status": "healthy"}
