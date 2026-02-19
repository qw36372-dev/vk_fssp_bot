"""
library/enum.py — Перечисление уровней сложности.
"""
from enum import Enum


class Difficulty(str, Enum):
    RESERVE  = "резерв"
    BASIC    = "базовый"
    STANDARD = "стандартный"
    ADVANCED = "продвинутый"
