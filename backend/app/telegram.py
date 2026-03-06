import httpx
import logging
from datetime import datetime
from app.config import settings
from app.models import LeadRequest

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


def format_lead_message(lead: LeadRequest, ip: str) -> str:
    """Форматирует заявку для отправки в Telegram."""

    class_labels = {
        "10": "10 класс",
        "11": "11 класс",
        "gap": "Выпускник (пересдача)",
    }

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    class_label = class_labels.get(lead.student_class, lead.student_class)
    goal = lead.goal or "не указана"

    # экранируем спецсимволы MarkdownV2
    def escape_md(text: str) -> str:
        special = r"_*[]()~`>#+-=|{}.!\\"
        for ch in special:
            text = text.replace(ch, f"\\{ch}")
        return text

    lines = [
        "📩 *Новая заявка на диагностику*",
        "",
        f"👤 *Имя:* {escape_md(lead.name)}",
        f"🎓 *Класс:* {escape_md(class_label)}",
        f"🎯 *Цель:* {escape_md(goal)}",
        f"📱 *Контакт:* {escape_md(lead.contact)}",
        "",
        f"🕐 {escape_md(now)}",
        f"🌐 IP: `{escape_md(ip)}`",
    ]

    return "\n".join(lines)


async def send_to_telegram(lead: LeadRequest, ip: str) -> bool:
    """Отправляет заявку в Telegram-чат. Возвращает True при успехе."""

    message = format_lead_message(lead, ip)

    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    logger.info(
                        "Telegram message sent",
                        extra={"contact": lead.contact},
                    )
                    return True

            # если MarkdownV2 сломался — отправляем plain text
            logger.warning(
                "Telegram MarkdownV2 failed, retrying plain text: %s",
                response.text,
            )
            return await _send_plain_text(lead, ip)

    except httpx.TimeoutException:
        logger.error("Telegram API timeout")
        return False
    except Exception as e:
        logger.error("Telegram send error: %s", str(e))
        return False


async def _send_plain_text(lead: LeadRequest, ip: str) -> bool:
    """Fallback: отправка без форматирования."""

    class_labels = {
        "10": "10 класс",
        "11": "11 класс",
        "gap": "Выпускник (пересдача)",
    }

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    goal = lead.goal or "не указана"

    text = (
        f"📩 Новая заявка на диагностику\n\n"
        f"Имя: {lead.name}\n"
        f"Класс: {class_labels.get(lead.student_class, lead.student_class)}\n"
        f"Цель: {goal}\n"
        f"Контакт: {lead.contact}\n\n"
        f"Время: {now}\n"
        f"IP: {ip}"
    )

    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json=payload,
            )
            if response.status_code == 200 and response.json().get("ok"):
                logger.info("Telegram plain text sent")
                return True

            logger.error("Telegram plain text failed: %s", response.text)
            return False

    except Exception as e:
        logger.error("Telegram plain text error: %s", str(e))
        return False
