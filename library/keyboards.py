"""
library/keyboards.py — Клавиатуры VK Teams (inline keyboard format).
VK Teams использует 2D-массив кнопок вместо aiogram InlineKeyboardBuilder.
"""
from typing import List, Dict, Optional, Set

from .vk_types import STYLE_PRIMARY, STYLE_BASE, STYLE_ATTENTION


def _btn(text: str, cb: str, style: str = STYLE_BASE) -> Dict:
    return {"text": text, "callbackData": cb, "style": style}


def get_main_keyboard() -> List[List[Dict]]:
    """Главное меню: 11 специализаций в 1 колонку."""
    specs = [
        ("🚨 ООУПДС",                                    "spec_oupds",        STYLE_PRIMARY),
        ("📊 Исполнительное производство",               "spec_ispolniteli",  STYLE_BASE),
        ("🧑‍🧑‍🧒 Алименты",                             "spec_aliment",      STYLE_BASE),
        ("🎯 Дознание",                                   "spec_doznanie",     STYLE_BASE),
        ("⏳ Исполнительный розыск и реализация имущества","spec_rozyisk",    STYLE_BASE),
        ("📈 Организация профессиональной подготовки",   "spec_prof",         STYLE_BASE),
        ("📡 Организация управления и контроля",         "spec_oko",          STYLE_BASE),
        ("💻 Информатизация и информационная безопасность","spec_informatika", STYLE_BASE),
        ("👥 Кадровая работа",                           "spec_kadry",        STYLE_BASE),
        ("🔒 Обеспечение собственной безопасности",      "spec_bezopasnost",  STYLE_BASE),
        ("💼 Управленческая деятельность",               "spec_upravlenie",   STYLE_BASE),
        ("❓ Помощь 🆘",                                  "help",              STYLE_BASE),
    ]
    return [[_btn(text, cb, style)] for text, cb, style in specs]


def get_difficulty_keyboard() -> List[List[Dict]]:
    """Выбор уровня сложности."""
    return [
        [_btn("🥉 Резерв (20 вопросов, 35 мин)",      "diff_резерв",       STYLE_BASE)],
        [_btn("🥈 Базовый (30 вопросов, 25 мин)",      "diff_базовый",      STYLE_BASE)],
        [_btn("🥇 Стандартный (40 вопросов, 20 мин)",  "diff_стандартный",  STYLE_PRIMARY)],
        [_btn("💎 Продвинутый (50 вопросов, 20 мин)", "diff_продвинутый",  STYLE_ATTENTION)],
    ]


def get_test_keyboard(
    num_options: int,
    selected: Optional[Set[int]] = None
) -> List[List[Dict]]:
    """
    Клавиатура теста: числовые кнопки + «Далее».
    Выбранные варианты отмечены ✅.
    """
    selected = selected or set()
    NUMBER_EMOJI = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}
    
    buttons = []
    for i in range(1, num_options + 1):
        emoji = NUMBER_EMOJI.get(i, str(i))
        check = "✅ " if i in selected else ""
        style = STYLE_PRIMARY if i in selected else STYLE_BASE
        buttons.append(_btn(f"{check}{emoji}", f"ans_{i}", style))
    
    # Разбиваем на строки по 5 кнопок
    rows: List[List[Dict]] = []
    row_size = 5
    for chunk_start in range(0, len(buttons), row_size):
        rows.append(buttons[chunk_start:chunk_start + row_size])
    
    # Кнопка "Далее" отдельной строкой
    rows.append([_btn("➡️ Далее", "next", STYLE_PRIMARY)])
    
    return rows


def get_finish_keyboard() -> List[List[Dict]]:
    """Клавиатура после завершения теста."""
    return [
        [_btn("📋 Показать правильные ответы", "show_answers",  STYLE_BASE)],
        [_btn("🏆 Сертификат PDF",              "generate_cert", STYLE_PRIMARY)],
        [_btn("🔄 Повторить тест",               "repeat_test",   STYLE_BASE)],
        [_btn("📊 Моя статистика",               "my_stats",      STYLE_BASE)],
        [_btn("🏠 Главное меню",                 "main_menu",     STYLE_BASE)],
    ]
