import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pymon.api.deps import manager
from pymon.api.routers import alerts, auth, backup, logs, metrics, reports, servers, services, settings

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

@api.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    # Authenticate via the first message instead of a ?token= query parameter:
    # a token in the URL leaks into proxy/access logs and Referer headers.
    import json

    from fastapi import HTTPException

    from pymon.auth import decode_token

    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=15)
    except (asyncio.TimeoutError, WebSocketDisconnect, RuntimeError):
        await websocket.close(code=1008)
        return

    try:
        msg = json.loads(raw)
        token = msg.get("token") if isinstance(msg, dict) else None
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        # decode_token() never returns None — it either returns a dict or raises
        # HTTPException. Catch the exception so it doesn't crash the WS handler.
        decode_token(token)
    except (ValueError, TypeError, HTTPException):
        await websocket.close(code=1008)  # policy violation
        return

    await manager.connect(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                # Send a ping to keep the connection alive; if it fails, disconnect.
                try:
                    await websocket.send_text("")
                except Exception:
                    break
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@api.get("/health")
async def health():
    return {"status": "healthy"}
