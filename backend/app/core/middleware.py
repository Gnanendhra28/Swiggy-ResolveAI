import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from backend.app.core.logging import logger


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every incoming HTTP request is tagged with an X-Correlation-ID.
    Propagates incoming X-Correlation-ID or generates a new UUIDv4.
    Injects execution latency into X-Process-Time-Ms response header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"[{correlation_id}] Request failed: {request.method} {request.url.path} in {duration_ms:.2f}ms — {exc}"
            )
            raise exc

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

        return response
