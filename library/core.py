"""
library/core.py — Основная логика теста для VK Teams.
Аналог library.py из Telegram-версии, но работает с VKBot и state_manager.
"""
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vk_bot.bot import VKBot
    from vk_bot.types import VKMessage, VKCallbackQuery

from .models import CurrentTestState
from .keyboards import get_test_keyboard, get_finish_keyboard
from .states import TestStates
from .state_manager import state_manager
from .stats import stats_manager

logger = logging.getLogger(__name__)

NUMBER_EMOJI = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}


def _build_question_text(test_state: CurrentTestState) -> str:
    """Собирает текст вопроса с вариантами ответов."""
    question = test_state.questions[test_state.current_index]
    timer_text = test_state.timer_task.remaining_time() if test_state.timer_task else "∞"
    
    header = (
        f"⏰ Осталось: <b>{timer_text}</b>\n\n"
        f"📝 <b>Вопрос {test_state.current_index + 1}/{len(test_state.questions)}</b>"
    )
    
    options_text = "\n\n<b>Варианты ответов:</b>\n"
    for i, option in enumerate(question.options, start=1):
        emoji = NUMBER_EMOJI.get(i, str(i))
        mark = "✅ " if i in test_state.selected_answers else ""
        options_text += f"{mark}{emoji} {option}\n"
    
    return header + f"\n\n{question.question}" + options_text


async def show_question(
    bot: "VKBot",
    chat_id: str,
    test_state: CurrentTestState,
    question_index: int | None = None
):
    """Показать вопрос пользователю (новое сообщение)."""
    if question_index is not None:
        test_state.current_index = question_index
    
    test_state.load_answer(test_state.current_index)
    
    question = test_state.questions[test_state.current_index]
    full_text = _build_question_text(test_state)
    keyboard = get_test_keyboard(len(question.options), test_state.selected_answers)
    
    # Удаляем предыдущее сообщение с вопросом
    if test_state.last_message_id:
        try:
            await bot.delete_message(chat_id, test_state.last_message_id)
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение: {e}")
    
    resp = await bot.send_text(chat_id, full_text, keyboard)
    if resp and resp.get("ok"):
        test_state.last_message_id = str(resp.get("msgId", ""))


async def handle_answer_toggle(
    bot: "VKBot",
    query: "VKCallbackQuery",
    user_id: str
):
    """Toggle выбора варианта ответа."""
    try:
        answer_num = int(query.callbackData.split("_")[1])
    except (ValueError, IndexError):
        await bot.answer_callback(query.queryId, "❌ Ошибка")
        return
    
    data = await state_manager.get_data(user_id)
    test_state: CurrentTestState | None = data.get("test_state")
    if not test_state:
        await bot.answer_callback(query.queryId, "❌ Тест не найден")
        return
    
    if answer_num in test_state.selected_answers:
        test_state.selected_answers.discard(answer_num)
    else:
        test_state.selected_answers.add(answer_num)
    
    question = test_state.questions[test_state.current_index]
    full_text = _build_question_text(test_state)
    keyboard = get_test_keyboard(len(question.options), test_state.selected_answers)
    
    chat_id = query.message.chat.chatId
    msg_id = query.message.msgId
    
    try:
        await bot.edit_text(chat_id, msg_id, full_text, keyboard)
    except Exception as e:
        logger.warning(f"⚠️ Не удалось обновить сообщение: {e}")
    
    await bot.answer_callback(query.queryId)
    await state_manager.update_data(user_id, test_state=test_state)


async def handle_next_question(
    bot: "VKBot",
    query: "VKCallbackQuery",
    user_id: str
):
    """Кнопка «Далее» — переход к следующему вопросу."""
    data = await state_manager.get_data(user_id)
    test_state: CurrentTestState | None = data.get("test_state")
    if not test_state:
        await bot.answer_callback(query.queryId, "❌ Тест не найден")
        return
    
    test_state.save_answer(test_state.current_index)
    test_state.selected_answers.clear()
    test_state.current_index += 1
    
    await bot.answer_callback(query.queryId)
    
    if test_state.current_index >= len(test_state.questions):
        await finish_test(bot, query, user_id, test_state)
        return
    
    chat_id = query.message.chat.chatId
    await show_question(bot, chat_id, test_state)
    await state_manager.update_data(user_id, test_state=test_state)
    
    logger.info(
        f"➡️ {user_id}: вопрос "
        f"{test_state.current_index + 1}/{len(test_state.questions)}"
    )


async def finish_test(
    bot: "VKBot",
    query: "VKCallbackQuery",
    user_id: str,
    test_state: CurrentTestState | None = None
):
    """Завершение теста: подсчёт результатов, сохранение в БД."""
    if test_state is None:
        data = await state_manager.get_data(user_id)
        test_state = data.get("test_state")
    
    if not test_state:
        chat_id = query.message.chat.chatId
        await bot.send_text(chat_id, "❌ Ошибка: тест не найден")
        return
    
    # Останавливаем таймер
    if test_state.timer_task:
        test_state.timer_task.stop()
    
    test_state.calculate_results()
    
    # Сохраняем в БД
    await stats_manager.save_result(user_id, test_state)
    
    grade_emoji = {
        "отлично": "🏆", "хорошо": "👍",
        "удовлетворительно": "👌", "неудовлетворительно": "❌"
    }
    emoji = grade_emoji.get(test_state.grade, "📊")
    
    result_text = (
        f"{emoji} <b>Тест завершён!</b>\n\n"
        f"👤 <b>ФИО:</b> {test_state.full_name}\n"
        f"💼 <b>Должность:</b> {test_state.position}\n"
        f"🏢 <b>Подразделение:</b> {test_state.department}\n"
        f"📚 <b>Специализация:</b> {test_state.specialization}\n"
        f"📊 <b>Уровень:</b> {test_state.difficulty.value.capitalize()}\n\n"
        f"✅ <b>Оценка:</b> {test_state.grade.upper()}\n"
        f"📈 <b>Правильных ответов:</b> {test_state.correct_count} из {test_state.total_questions}\n"
        f"💯 <b>Процент:</b> {test_state.percentage:.1f}%\n"
        f"⏱ <b>Время:</b> {test_state.elapsed_time}"
    )
    
    chat_id = query.message.chat.chatId
    
    # Удаляем сообщение с последним вопросом
    if test_state.last_message_id:
        try:
            await bot.delete_message(chat_id, test_state.last_message_id)
        except Exception:
            pass
    
    await bot.send_text(chat_id, result_text, get_finish_keyboard())
    
    await state_manager.set_state(user_id, TestStates.SHOWING_RESULTS)
    await state_manager.update_data(user_id, test_state=test_state)
    
    logger.info(
        f"🏁 {user_id} завершил тест: "
        f"{test_state.percentage:.1f}% ({test_state.grade})"
    )
