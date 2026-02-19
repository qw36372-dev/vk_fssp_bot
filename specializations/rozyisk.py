"""specializations/rozyisk.py — Исполнительный розыск и реализация имущества."""
from ._base import make_handlers

SPEC_NAME  = "rozyisk"
SPEC_LABEL = "Исполнительный розыск и реализация имущества"
SPEC_EMOJI = "⏳"

handlers = make_handlers(SPEC_NAME, SPEC_LABEL, SPEC_EMOJI)
