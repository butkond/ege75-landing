import time
import asyncio
from collections import defaultdict
from typing import Dict, List
from app.config import settings


class RateLimiter:
    """
    In-memory rate limiter по IP.
    Для горизонтального масштабирования заменить на Redis.
    """

    def __init__(self):
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._cleanup_interval = 300  # 5 минут
        self._last_cleanup = time.time()

    async def is_allowed(self, ip: str) -> bool:
        """Проверяет, разрешён ли запрос для данного IP."""

        async with self._lock:
            now = time.time()

            # периодическая очистка старых записей
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup(now)
                self._last_cleanup = now

            timestamps = self._requests[ip]

            # удаляем записи старше часа
            timestamps[:] = [t for t in timestamps if now - t < 3600]

            # проверяем лимит в минуту
            recent_minute = sum(1 for t in timestamps if now - t < 60)
            if recent_minute >= settings.RATE_LIMIT_PER_MINUTE:
                return False

            # проверяем лимит в час
            if len(timestamps) >= settings.RATE_LIMIT_PER_HOUR:
                return False

            timestamps.append(now)
            return True

    def _cleanup(self, now: float):
        """Удаляет IP без активности за последний час."""

        stale_ips = [
            ip
            for ip, timestamps in self._requests.items()
            if not timestamps or now - timestamps[-1] > 3600
        ]
        for ip in stale_ips:
            del self._requests[ip]


rate_limiter = RateLimiter()
