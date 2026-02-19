"""
library/states.py — Константы FSM-состояний бота.
Аналог aiogram StatesGroup, но для in-memory state manager.
"""


class TestStates:
    """Состояния FSM для теста."""
    
    # Ввод пользовательских данных
    WAITING_FULL_NAME = "waiting_full_name"
    WAITING_POSITION = "waiting_position"
    WAITING_DEPARTMENT = "waiting_department"
    
    # Выбор уровня сложности
    WAITING_DIFFICULTY = "waiting_difficulty"
    
    # Прохождение теста
    ANSWERING_QUESTION = "answering_question"
    
    # Завершение теста
    SHOWING_RESULTS = "showing_results"
    SHOWING_ANSWERS = "showing_answers"
    GENERATING_CERTIFICATE = "generating_certificate"
    
    # Статистика
    SHOWING_STATS = "showing_stats"
