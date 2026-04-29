"""Error handling middleware and utilities"""

import logging
import traceback
from fastapi import FastAPI, Request, Response
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
        request_id = id(request)

        logger.error(
            f"Request {request.url} failed: {exc}",
            extra={"request_id": request_id, "traceback": traceback.format_exc()},
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if logger.level == logging.DEBUG else "An error occurred",
                "request_id": request_id,
            },
        )


def setup_middleware(app: FastAPI):
    """Add all middleware to the app"""
    app.add_middleware(ErrorHandlingMiddleware)