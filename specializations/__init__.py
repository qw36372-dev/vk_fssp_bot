"""
specializations/__init__.py — Объединяет все хэндлеры в один реестр.

Структура реестра:
    callback_handlers: Dict[str, handler_fn]   — точное совпадение callbackData
    callback_prefix_handlers: Dict[str, handler_fn] — совпадение по префиксу
    message_state_handlers: Dict[str, handler_fn]  — по текущему состоянию
"""
from . import (
    oupds, ispolniteli, aliment, doznanie, rozyisk,
    prof, oko, informatika, kadry, bezopasnost, upravlenie
)

# Все 11 специализаций
_ALL = [
    oupds, ispolniteli, aliment, doznanie, rozyisk,
    prof, oko, informatika, kadry, bezopasnost, upravlenie
]

# Собираем реестры из всех специализаций
callback_handlers = {}        # exact callbackData
callback_prefix_handlers = {} # callbackData.startswith(key)
message_state_handlers = {}   # state -> handler

_PREFIX_KEYS = {"diff_", "ans_"}

for mod in _ALL:
    for key, fn in mod.handlers.items():
        if key.startswith("msg:"):
            # Сообщения по состоянию
            message_state_handlers[key[4:]] = fn
        elif key in _PREFIX_KEYS:
            callback_prefix_handlers[key] = fn
        else:
            callback_handlers[key] = fn
