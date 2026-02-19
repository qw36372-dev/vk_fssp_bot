"""
specializations/_base.py — Фабрика обработчиков для VK Teams.
Каждая специализация вызывает register_handlers() с своими константами.
Все хэндлеры регистрируются в глобальном диспетчере.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vk_bot.bot import VKBot
    from vk_bot.types import VKMessage, VKCallbackQuery

from library.models import CurrentTestState
from library.states import TestStates
from library.state_manager import state_manager
from library.question_loader import load_questions_for_specialization
from library.enum import Difficulty
from library.keyboards import (
    get_difficulty_keyboard, get_finish_keyboard, get_main_keyboard
)
from library.core import (
    show_question, handle_answer_toggle,
    handle_next_question, finish_test
)
from library.timers import create_timer
from library.certificates import generate_certificate
from library.stats import stats_manager
from config.settings import settings

logger = logging.getLogger(__name__)


HELP_TEXT = (
    "❓ <b>Помощь по боту</b>\n\n"
    "<b>Как пройти тест:</b>\n"
    "1️⃣ Выберите специализацию\n"
    "2️⃣ Введите данные (ФИО, должность, подразделение)\n"
    "3️⃣ Выберите уровень сложности\n"
    "4️⃣ Отвечайте на вопросы (1️⃣2️⃣3️⃣...)\n"
    "5️⃣ Нажмите ➡️ Далее\n"
    "6️⃣ Получите результат и PDF сертификат\n\n"
    "<b>Уровни сложности:</b>\n"
    "🥉 Резерв: 20 вопросов, 35 мин\n"
    "🥈 Базовый: 30 вопросов, 25 мин\n"
    "🥇 Стандартный: 40 вопросов, 20 мин\n"
    "💎 Продвинутый: 50 вопросов, 20 мин\n\n"
    "Удачи! 🍀"
)

MAIN_MENU_TEXT = "🧪 <b>ФССП Тест-бот</b>\n\nВыберите специализацию:"


def make_handlers(spec_name: str, spec_label: str, spec_emoji: str):
    """
    Возвращает словарь хэндлеров для данной специализации.
    
    Ключи словаря соответствуют callback_data,
    значения — async функции (bot, query/message, user_id).
    """

    # ------------------------------------------------------------------ #
    # Шаг 1: Выбор специализации
    # ------------------------------------------------------------------ #
    async def on_select_spec(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        chat_id = query.message.chat.chatId
        await bot.answer_callback(query.queryId)
        # Удаляем сообщение с меню
        try:
            await bot.delete_message(chat_id, query.message.msgId)
        except Exception:
            pass
        await bot.send_text(
            chat_id,
            f"{spec_emoji} <b>{spec_label}</b>\n\nВведите ваше ФИО:"
        )
        await state_manager.set_state(user_id, TestStates.WAITING_FULL_NAME)
        await state_manager.update_data(user_id, specialization=spec_name)

    # ------------------------------------------------------------------ #
    # Шаги 2–4: Сбор данных пользователя (текстовые сообщения)
    # ------------------------------------------------------------------ #
    async def on_full_name(bot: "VKBot", message: "VKMessage", user_id: str):
        await state_manager.update_data(user_id, full_name=message.text.strip())
        await bot.send_text(message.chat.chatId, "Введите вашу должность:")
        await state_manager.set_state(user_id, TestStates.WAITING_POSITION)

    async def on_position(bot: "VKBot", message: "VKMessage", user_id: str):
        await state_manager.update_data(user_id, position=message.text.strip())
        await bot.send_text(message.chat.chatId, "Введите ваше подразделение:")
        await state_manager.set_state(user_id, TestStates.WAITING_DEPARTMENT)

    async def on_department(bot: "VKBot", message: "VKMessage", user_id: str):
        await state_manager.update_data(user_id, department=message.text.strip())
        await bot.send_text(
            message.chat.chatId,
            "Выберите уровень сложности:",
            get_difficulty_keyboard()
        )
        await state_manager.set_state(user_id, TestStates.WAITING_DIFFICULTY)

    # ------------------------------------------------------------------ #
    # Шаг 5: Выбор сложности → старт теста
    # ------------------------------------------------------------------ #
    async def on_difficulty(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        await bot.answer_callback(query.queryId)
        diff_value = query.callbackData.split("_", 1)[1]
        
        try:
            difficulty = Difficulty(diff_value)
        except ValueError:
            await bot.answer_callback(query.queryId, "❌ Неверный уровень сложности", True)
            return
        
        user_data = await state_manager.get_data(user_id)
        specialization = user_data.get("specialization", spec_name)
        
        questions = load_questions_for_specialization(specialization, difficulty, user_id)
        if not questions:
            chat_id = query.message.chat.chatId
            await bot.delete_message(chat_id, query.message.msgId)
            await bot.send_text(chat_id, "❌ Не удалось загрузить вопросы. Попробуйте позже.")
            await state_manager.clear(user_id)
            return
        
        test_state = CurrentTestState(
            questions=questions,
            specialization=specialization,
            difficulty=difficulty,
            full_name=user_data.get("full_name", ""),
            position=user_data.get("position", ""),
            department=user_data.get("department", "")
        )
        
        chat_id = query.message.chat.chatId
        
        async def on_timeout():
            await finish_test(bot, query, user_id, test_state)
        
        timer = create_timer(difficulty, on_timeout)
        await timer.start()
        test_state.timer_task = timer
        
        await stats_manager.update_user_activity(user_id)
        
        await state_manager.set_state(user_id, TestStates.ANSWERING_QUESTION)
        await state_manager.update_data(user_id, test_state=test_state)
        
        # Удаляем сообщение с выбором сложности
        try:
            await bot.delete_message(chat_id, query.message.msgId)
        except Exception:
            pass
        
        await show_question(bot, chat_id, test_state, question_index=0)
        await state_manager.update_data(user_id, test_state=test_state)
        
        logger.info(f"▶️ {user_id} начал {specialization} ({difficulty.value})")

    # ------------------------------------------------------------------ #
    # Прохождение теста
    # ------------------------------------------------------------------ #
    async def on_answer(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        await handle_answer_toggle(bot, query, user_id)

    async def on_next(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        await handle_next_question(bot, query, user_id)

    # ------------------------------------------------------------------ #
    # Результаты: показ правильных ответов
    # ------------------------------------------------------------------ #
    async def on_show_answers(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        data = await state_manager.get_data(user_id)
        test_state: CurrentTestState = data.get("test_state")
        if not test_state:
            await bot.answer_callback(query.queryId, "❌ Данные теста не найдены", True)
            return
        
        answers_text = "📋 <b>Правильные ответы:</b>\n\n"
        for i, question in enumerate(test_state.questions, 1):
            user_answer = test_state.answers_history.get(i - 1, set())
            correct = question.correct_answers
            emoji = "✅" if user_answer == correct else "❌"
            nums = ", ".join(str(n) for n in sorted(correct))
            answers_text += f"{emoji} <b>Вопрос {i}:</b> {nums}\n"
        answers_text += f"\n⏱ <i>Сообщение удалится через {settings.answers_show_time} сек</i>"
        
        chat_id = query.message.chat.chatId
        await bot.answer_callback(query.queryId)
        resp = await bot.send_text(chat_id, answers_text)
        
        if resp and resp.get("ok"):
            msg_id = str(resp.get("msgId", ""))
            async def delete_later():
                await asyncio.sleep(settings.answers_show_time)
                try:
                    await bot.delete_message(chat_id, msg_id)
                except Exception:
                    pass
            asyncio.create_task(delete_later())

    # ------------------------------------------------------------------ #
    # Генерация PDF сертификата
    # ------------------------------------------------------------------ #
    async def on_generate_cert(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        data = await state_manager.get_data(user_id)
        test_state: CurrentTestState = data.get("test_state")
        if not test_state:
            await bot.answer_callback(query.queryId, "❌ Данные теста не найдены", True)
            return
        
        await bot.answer_callback(query.queryId, "📄 Генерация сертификата...")
        
        try:
            pdf_buffer = await generate_certificate(test_state, user_id)
            pdf_bytes = pdf_buffer.read()
            
            caption = (
                f"🏆 <b>Ваш сертификат готов!</b>\n\n"
                f"Специализация: {test_state.specialization.upper()}\n"
                f"Оценка: {test_state.grade.upper()}\n"
                f"Результат: {test_state.percentage:.1f}%"
            )
            
            await bot.send_file(
                query.message.chat.chatId,
                pdf_bytes,
                filename=f"certificate_{test_state.specialization}.pdf",
                caption=caption
            )
        except Exception as e:
            logger.error(f"❌ Ошибка генерации сертификата: {e}", exc_info=True)
            await bot.send_text(
                query.message.chat.chatId,
                "❌ Ошибка при генерации сертификата"
            )

    # ------------------------------------------------------------------ #
    # Повторить тест
    # ------------------------------------------------------------------ #
    async def on_repeat(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        await state_manager.clear(user_id)
        chat_id = query.message.chat.chatId
        await bot.answer_callback(query.queryId)
        try:
            await bot.delete_message(chat_id, query.message.msgId)
        except Exception:
            pass
        await bot.send_text(
            chat_id,
            f"{spec_emoji} <b>{spec_label}</b>\n\nВведите ваше ФИО:"
        )
        await state_manager.set_state(user_id, TestStates.WAITING_FULL_NAME)
        await state_manager.update_data(user_id, specialization=spec_name)

    # ------------------------------------------------------------------ #
    # Статистика
    # ------------------------------------------------------------------ #
    async def on_stats(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        try:
            stats = await stats_manager.get_user_stats(user_id)
            if stats.get("total_tests", 0) == 0:
                text = (
                    "📊 <b>Ваша статистика</b>\n\n"
                    "У вас пока нет пройденных тестов.\n"
                    "Начните тестирование прямо сейчас!"
                )
            else:
                text = (
                    f"📊 <b>Ваша статистика</b>\n\n"
                    f"📝 Всего тестов: {stats['total_tests']}\n"
                    f"📈 Средний балл: {stats['avg_percentage']}%\n"
                    f"🏆 Лучший результат: {stats['best_result']}%\n"
                    f"📉 Худший результат: {stats['worst_result']}%"
                )
                if stats.get("recent_tests"):
                    text += "\n\n<b>Последние тесты:</b>\n"
                    for r in stats["recent_tests"]:
                        text += (
                            f"• {r['specialization']} ({r['difficulty']}): "
                            f"{r['grade']} — {r['percentage']:.1f}%\n"
                        )
            await bot.answer_callback(query.queryId)
            await bot.send_text(query.message.chat.chatId, text)
        except Exception as e:
            logger.error(f"❌ Ошибка статистики: {e}", exc_info=True)
            await bot.answer_callback(query.queryId, "❌ Ошибка загрузки", True)

    # ------------------------------------------------------------------ #
    # Главное меню
    # ------------------------------------------------------------------ #
    async def on_main_menu(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        await state_manager.clear(user_id)
        chat_id = query.message.chat.chatId
        await bot.answer_callback(query.queryId)
        try:
            await bot.edit_text(
                chat_id, query.message.msgId,
                MAIN_MENU_TEXT, get_main_keyboard()
            )
        except Exception:
            await bot.send_text(chat_id, MAIN_MENU_TEXT, get_main_keyboard())

    # ------------------------------------------------------------------ #
    # Помощь
    # ------------------------------------------------------------------ #
    async def on_help(bot: "VKBot", query: "VKCallbackQuery", user_id: str):
        await bot.answer_callback(query.queryId)
        try:
            await bot.edit_text(
                query.message.chat.chatId, query.message.msgId,
                HELP_TEXT, get_main_keyboard()
            )
        except Exception:
            await bot.send_text(
                query.message.chat.chatId, HELP_TEXT, get_main_keyboard()
            )

    return {
        # Callback handlers (keyed by callbackData prefix/exact)
        f"spec_{spec_name}": on_select_spec,
        "diff_": on_difficulty,         # prefix match
        "ans_":  on_answer,             # prefix match
        "next":  on_next,
        "show_answers":  on_show_answers,
        "generate_cert": on_generate_cert,
        "repeat_test":   on_repeat,
        "my_stats":      on_stats,
        "main_menu":     on_main_menu,
        "help":          on_help,
        # Message handlers (keyed by state)
        f"msg:{TestStates.WAITING_FULL_NAME}":  on_full_name,
        f"msg:{TestStates.WAITING_POSITION}":   on_position,
        f"msg:{TestStates.WAITING_DEPARTMENT}": on_department,
    }
