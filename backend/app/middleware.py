from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging
import time

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Добавляет security-заголовки ко всем ответам."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Логирует входящие запросы."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 1)

        if request.url.path not in ("/health", "/favicon.ico"):
            logger.info(
                "%s %s %s %sms",
                request.method,
                request.url.path,
                response.status_code,
                duration,
            )

        return response
