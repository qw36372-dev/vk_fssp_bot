"""
library/timers.py — Асинхронный таймер для тестов.
Идентичен Telegram-версии.
"""
import asyncio
import logging
import time
from typing import Callable, Awaitable

from .enum import Difficulty
from config.settings import settings

logger = logging.getLogger(__name__)


class TestTimer:
    def __init__(self, duration_minutes: int, timeout_callback: Callable[[], Awaitable[None]]):
        self.duration_seconds = duration_minutes * 60
        self.timeout_callback = timeout_callback
        self.start_time: float | None = None
        self.task: asyncio.Task | None = None
        self._cancelled = False

    async def _run(self):
        try:
            await asyncio.sleep(self.duration_seconds)
            if not self._cancelled:
                logger.info(f"⏰ Таймер истёк ({self.duration_seconds}s)")
                await self.timeout_callback()
        except asyncio.CancelledError:
            raise

    async def start(self):
        if self.task is not None:
            return
        self.start_time = time.time()
        self.task = asyncio.create_task(self._run())
        logger.info(f"▶️ Таймер запущен на {self.duration_seconds // 60} мин")

    def stop(self):
        if self.task and not self.task.done():
            self._cancelled = True
            self.task.cancel()

    def remaining_time(self) -> str:
        if self.start_time is None:
            return "∞"
        elapsed = time.time() - self.start_time
        remaining = max(0, self.duration_seconds - elapsed)
        return f"{int(remaining // 60):02d}:{int(remaining % 60):02d}"


def create_timer(difficulty: Difficulty, timeout_callback: Callable[[], Awaitable[None]]) -> TestTimer:
    duration = settings.difficulty_times.get(difficulty.value, 20)
    return TestTimer(duration, timeout_callback)
