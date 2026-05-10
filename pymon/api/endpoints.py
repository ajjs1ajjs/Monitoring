from fastapi import APIRouter
from pymon.api.routers import auth, servers, metrics, alerts, settings, logs
from pymon.api.deps import manager
from fastapi import WebSocket, WebSocketDisconnect

api = APIRouter()

# Include modular routers
api.include_router(auth.router)
api.include_router(servers.router)
api.include_router(metrics.router)
api.include_router(alerts.router)
api.include_router(settings.router)
api.include_router(logs.router)

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
