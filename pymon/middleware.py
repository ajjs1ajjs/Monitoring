"""Error handling middleware and utilities"""

import logging
import traceback
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Centralized error handling middleware"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            return self._handle_exception(request, e)

    def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        # Time-unique id (id(request) reuses memory addresses across requests).
        request_id = uuid.uuid4().hex

        logger.error(
            f"Request {request.url} failed: {exc}",
            extra={"request_id": request_id, "traceback": traceback.format_exc()},
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if logger.isEnabledFor(logging.DEBUG) else "An error occurred",
                "request_id": request_id,
            },
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security response headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "script-src 'self' 'unsafe-inline' https:; "
            "connect-src 'self' ws: wss:; frame-ancestors 'none'",
        )
        # HSTS only over HTTPS (harmless/ignored over plain HTTP, but avoid
        # pinning HSTS for users who legitimately serve over http on a LAN).
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


def setup_middleware(app: FastAPI):
    """Add all middleware to the app"""
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
