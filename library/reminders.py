"""
library/reminders.py — Фоновые напоминания для VK Teams.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vk_bot.bot import VKBot

from .stats import stats_manager

logger = logging.getLogger(__name__)


async def reminders_background_task(bot: "VKBot"):
    """
    Фоновая задача: раз в 24 ч проверяет неактивных пользователей (7+ дней)
    и отправляет им напоминание.
    """
    CHECK_INTERVAL_HOURS = 24
    INACTIVE_DAYS = 7

    logger.info(
        f"▶️ Сервис напоминаний запущен "
        f"(каждые {CHECK_INTERVAL_HOURS}ч, порог {INACTIVE_DAYS} дней)"
    )

    while True:
        try:
            inactive_users = await stats_manager.get_inactive_users(days=INACTIVE_DAYS)
            if inactive_users:
                logger.info(f"📨 Неактивных пользователей: {len(inactive_users)}")
                sent_count = 0
                for user_id in inactive_users:
                    try:
                        message = (
                            "👋 Привет! Тебя давно не было видно.\n\n"
                            "Не желаешь пройти тест и проверить свои знания?\n\n"
                            "Напиши /start и начни прямо сейчас! 🚀"
                        )
                        await bot.send_text(user_id, message)
                        await stats_manager.mark_reminder_sent(user_id)
                        sent_count += 1
                        logger.info(f"✅ Напоминание → {user_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось отправить {user_id}: {e}")
                    await asyncio.sleep(1)
                logger.info(f"✅ Напоминаний отправлено: {sent_count}/{len(inactive_users)}")
            else:
                logger.debug("ℹ️ Нет неактивных пользователей")
        except Exception as e:
            logger.error(f"❌ Ошибка сервиса напоминаний: {e}", exc_info=True)
        
        await asyncio.sleep(CHECK_INTERVAL_HOURS * 3600)
