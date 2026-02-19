#!/usr/bin/env python3
"""
main.py — VK Workspace ФССП Тест-бот.
Production-ready: long-polling, FSM, PDF, статистика, напоминания.
"""
import asyncio
import logging
import sys
import time
from collections import defaultdict
from typing import Dict, List

from config.settings import settings
from vk_bot.bot import VKBot
from vk_bot.types import VKEvent
from library.keyboards import get_main_keyboard
from library.state_manager import state_manager
from library.states import TestStates
from library.stats import stats_manager
from library.reminders import reminders_background_task

from specializations import (
    callback_handlers,
    callback_prefix_handlers,
    message_state_handlers,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────── #
# Anti-spam: не более 3 событий за 1 секунду на пользователя
# ─────────────────────────────────────────────────────────────────────────
_SPAM_WINDOW = 1.0
_SPAM_LIMIT  = 3
_user_timestamps: Dict[str, List[float]] = defaultdict(list)


def _is_spam(user_id: str) -> bool:
    now = time.monotonic()
    ts = _user_timestamps[user_id]
    ts[:] = [t for t in ts if now - t < _SPAM_WINDOW]
    if len(ts) >= _SPAM_LIMIT:
        return True
    ts.append(now)
    return False


# ─────────────────────────────────────────────────────────────────────── #
# Command handlers
# ─────────────────────────────────────────────────────────────────────── #
MAIN_MENU_TEXT = "🧪 <b>ФССП Тест-бот</b>\n\nДобро пожаловать!\nВыберите специализацию:"

HELP_TEXT = (
    "❓ <b>Справка по боту</b>\n\n"
    "<b>Как пройти тест:</b>\n"
    "1️⃣ Напишите /start и выберите специализацию\n"
    "2️⃣ Введите ФИО, должность, подразделение\n"
    "3️⃣ Выберите уровень сложности\n"
    "4️⃣ Отвечайте на вопросы кнопками\n"
    "5️⃣ Нажимайте ➡️ Далее после ответа\n"
    "6️⃣ Получите результат и PDF сертификат\n\n"
    "<b>Уровни сложности:</b>\n"
    "🥉 Резерв: 20 вопросов, 35 мин\n"
    "🥈 Базовый: 30 вопросов, 25 мин\n"
    "🥇 Стандартный: 40 вопросов, 20 мин\n"
    "💎 Продвинутый: 50 вопросов, 20 мин\n\n"
    "Удачи на тестировании! 🍀"
)


async def handle_start(bot: VKBot, message, user_id: str):
    await state_manager.clear(user_id)
    await bot.send_text(message.chat.chatId, MAIN_MENU_TEXT, get_main_keyboard())


async def handle_stats_cmd(bot: VKBot, message, user_id: str):
    try:
        stats = await stats_manager.get_user_stats(user_id)
        if stats.get("total_tests", 0) == 0:
            text = (
                "📊 <b>Ваша статистика</b>\n\n"
                "Пройденных тестов нет.\n"
                "Начните с команды /start!"
            )
        else:
            text = (
                f"📊 <b>Ваша статистика</b>\n\n"
                f"📝 Всего тестов: {stats['total_tests']}\n"
                f"📈 Средний балл: {stats['avg_percentage']}%\n"
                f"🏆 Лучший: {stats['best_result']}%\n"
                f"📉 Худший: {stats['worst_result']}%"
            )
            if stats.get("recent_tests"):
                text += "\n\n<b>Последние тесты:</b>\n"
                for r in stats["recent_tests"]:
                    text += (
                        f"• {r['specialization']} ({r['difficulty']}): "
                        f"{r['grade']} — {r['percentage']:.1f}%\n"
                    )
        await bot.send_text(message.chat.chatId, text)
    except Exception as e:
        logger.error(f"❌ Ошибка статистики: {e}", exc_info=True)
        await bot.send_text(message.chat.chatId, "❌ Ошибка загрузки статистики")


async def handle_help_cmd(bot: VKBot, message, user_id: str):
    await bot.send_text(message.chat.chatId, HELP_TEXT)


COMMANDS = {
    "/start":  handle_start,
    "/stats":  handle_stats_cmd,
    "/help":   handle_help_cmd,
    "/помощь": handle_help_cmd,
}


# ─────────────────────────────────────────────────────────────────────── #
# Event dispatcher
# ─────────────────────────────────────────────────────────────────────── #
async def dispatch_message(bot: VKBot, event: VKEvent):
    """Обработка текстовых сообщений."""
    msg = event.message
    if not msg:
        return
    
    user_id = msg.from_user.userId
    text = (msg.text or "").strip()
    
    if _is_spam(user_id):
        await bot.send_text(msg.chat.chatId, "⏳ Слишком частые запросы. Подождите секунду.")
        return
    
    # Команды
    cmd = text.split()[0].lower() if text else ""
    if cmd in COMMANDS:
        await COMMANDS[cmd](bot, msg, user_id)
        return
    
    # FSM — текстовый ввод по состоянию
    current_state = await state_manager.get_state(user_id)
    if current_state and current_state in message_state_handlers:
        try:
            await message_state_handlers[current_state](bot, msg, user_id)
        except Exception as e:
            logger.error(f"❌ Ошибка msg-хэндлера [{current_state}]: {e}", exc_info=True)
            await bot.send_text(msg.chat.chatId, "❌ Ошибка. Начните заново с /start")
        return
    
    # Если нет состояния — показываем меню
    if not current_state:
        await bot.send_text(msg.chat.chatId, MAIN_MENU_TEXT, get_main_keyboard())


async def dispatch_callback(bot: VKBot, event: VKEvent):
    """Обработка нажатий на inline-кнопки."""
    cb = event.callback_query
    if not cb:
        return
    
    user_id = cb.from_user.userId
    data = cb.callbackData
    
    if _is_spam(user_id):
        await bot.answer_callback(cb.queryId, "⏳ Подождите немного...", True)
        return
    
    current_state = await state_manager.get_state(user_id)
    
    try:
        # 1. Точное совпадение
        if data in callback_handlers:
            handler = callback_handlers[data]
            # Проверяем совместимость состояния для ans_* и next
            if data == "next" and current_state != TestStates.ANSWERING_QUESTION:
                await bot.answer_callback(cb.queryId, "❌ Нет активного теста", True)
                return
            await handler(bot, cb, user_id)
            return
        
        # 2. Совпадение по префиксу
        for prefix, handler in callback_prefix_handlers.items():
            if data.startswith(prefix):
                # Проверка состояния для ans_*
                if prefix == "ans_" and current_state != TestStates.ANSWERING_QUESTION:
                    await bot.answer_callback(cb.queryId, "❌ Нет активного теста", True)
                    return
                # Проверка состояния для diff_
                if prefix == "diff_" and current_state != TestStates.WAITING_DIFFICULTY:
                    await bot.answer_callback(cb.queryId, "❌ Ошибка состояния", True)
                    return
                await handler(bot, cb, user_id)
                return
        
        # Не нашли хэндлер
        await bot.answer_callback(cb.queryId, "❓ Неизвестная команда")
        logger.warning(f"⚠️ Неизвестный callback: {data!r}")
    
    except Exception as e:
        logger.error(f"❌ Ошибка callback-хэндлера [{data}]: {e}", exc_info=True)
        await bot.answer_callback(cb.queryId, "❌ Ошибка. Попробуйте /start", True)


# ─────────────────────────────────────────────────────────────────────── #
# Polling loop
# ─────────────────────────────────────────────────────────────────────── #
async def polling_loop(bot: VKBot):
    """
    Основной цикл long-polling.
    Получает события, передаёт в диспетчер. 
    Exponential backoff при ошибках.
    """
    last_event_id = 0
    error_count = 0
    MAX_ERRORS = 10
    
    logger.info("🚀 Polling запущен")
    
    while True:
        try:
            resp = await bot.get_events(last_event_id)
            
            if resp is None:
                error_count += 1
                wait = min(2 ** error_count, 60)
                logger.warning(f"⚠️ Нет ответа от API, ждём {wait}s")
                await asyncio.sleep(wait)
                continue
            
            error_count = 0  # сбрасываем счётчик ошибок
            
            events = resp.get("events", [])
            
            for raw_event in events:
                event_id = raw_event.get("eventId", 0)
                if event_id > last_event_id:
                    last_event_id = event_id
                
                event = VKEvent(
                    type=raw_event.get("type", ""),
                    payload=raw_event.get("payload", {}),
                    event_id=event_id
                )
                
                # Запускаем обработку в фоне (не блокируем polling)
                if event.type in ("newMessage", "editedMessage"):
                    asyncio.create_task(dispatch_message(bot, event))
                elif event.type == "callbackQuery":
                    asyncio.create_task(dispatch_callback(bot, event))
                else:
                    logger.debug(f"ℹ️ Игнорируем событие: {event.type}")
            
        except asyncio.CancelledError:
            logger.info("⚠️ Polling отменён")
            break
        except Exception as e:
            error_count += 1
            wait = min(2 ** error_count, 60)
            logger.error(f"❌ Ошибка polling: {e}. Ждём {wait}s", exc_info=True)
            if error_count >= MAX_ERRORS:
                logger.critical("❌ Слишком много ошибок подряд. Перезапуск через 60s")
                await asyncio.sleep(60)
                error_count = 0
            else:
                await asyncio.sleep(wait)


# ─────────────────────────────────────────────────────────────────────── #
# Startup / Shutdown
# ─────────────────────────────────────────────────────────────────────── #
async def main():
    if not settings.api_token:
        logger.error("❌ API_TOKEN не установлен!")
        sys.exit(1)
    
    bot = VKBot(token=settings.api_token, api_url=settings.api_url)
    await bot.start()
    
    # Проверка соединения
    info = await bot.self_get()
    if info and info.get("ok"):
        nick = info.get("nick", "unknown")
        logger.info(f"✅ Бот авторизован: @{nick}")
    else:
        logger.warning("⚠️ Не удалось получить информацию о боте, продолжаем...")
    
    # Инициализация БД
    await stats_manager.init_db()
    logger.info("✅ База данных инициализирована")
    
    # Запуск фоновых задач
    reminder_task = asyncio.create_task(reminders_background_task(bot))
    logger.info("✅ Сервис напоминаний запущен")
    
    logger.info(f"✅ Загружено 11 специализаций")
    logger.info(f"🧪 ФССП Тест-бот запущен (VK Workspace)")
    
    try:
        await polling_loop(bot)
    except KeyboardInterrupt:
        logger.info("⚠️ Остановка по Ctrl+C")
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        await bot.stop()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"❌ Фатальная ошибка: {e}", exc_info=True)
        sys.exit(1)
