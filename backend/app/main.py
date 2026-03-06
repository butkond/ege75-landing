import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import LeadRequest, LeadResponse, HealthResponse
from app.telegram import send_to_telegram
from app.rate_limit import rate_limiter
from app.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware

# ── Logging ──────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app")


# ── Lifespan ─────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting app | env=%s | origins=%s",
        settings.APP_ENV,
        settings.allowed_origins_list,
    )
    yield
    logger.info("Shutting down")


# ── App ──────────────────────────────────────────────────

app = FastAPI(
    title="ЕГЭ Математика — API",
    version="1.0.0",
    docs_url="/docs" if settings.APP_DEBUG else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.APP_DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware (порядок: последний добавленный = первый выполняется) ──

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    max_age=86400,
)


# ── Helpers ──────────────────────────────────────────────


def get_client_ip(request: Request) -> str:
    """Извлекает IP клиента с учётом прокси."""

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


# ── Routes ───────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health():
    """Healthcheck для Docker и мониторинга."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
    )


@app.post("/api/lead", response_model=LeadResponse)
async def create_lead(lead: LeadRequest, request: Request):
    """
    Принимает заявку на диагностику и отправляет в Telegram.
    """

    client_ip = get_client_ip(request)

    # Rate limiting
    if not await rate_limiter.is_allowed(client_ip):
        logger.warning("Rate limit exceeded for IP: %s", client_ip)
        raise HTTPException(
            status_code=429,
            detail="Слишком много заявок. Попробуйте через несколько минут.",
        )

    # Отправка в Telegram
    sent = await send_to_telegram(lead, client_ip)

    if not sent:
        logger.error(
            "Failed to send lead to Telegram | contact=%s | ip=%s",
            lead.contact,
            client_ip,
        )
        # Не теряем заявку — логируем полностью
        logger.critical(
            "LOST LEAD | name=%s | class=%s | goal=%s | contact=%s | ip=%s",
            lead.name,
            lead.student_class,
            lead.goal,
            lead.contact,
            client_ip,
        )
        raise HTTPException(
            status_code=502,
            detail="Не удалось отправить заявку. Попробуйте позже или напишите нам в Telegram напрямую.",
        )

    logger.info(
        "Lead created | contact=%s | class=%s | ip=%s",
        lead.contact,
        lead.student_class,
        client_ip,
    )

    return LeadResponse(
        success=True,
        message="Заявка отправлена. Мы свяжемся с вами в течение дня.",
    )


# ── Error handlers ───────────────────────────────────────


@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    """Человекочитаемые ошибки валидации."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Проверьте правильность заполнения формы.",
            "detail": str(exc),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("Internal error: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Внутренняя ошибка сервера. Попробуйте позже.",
        },
    )
