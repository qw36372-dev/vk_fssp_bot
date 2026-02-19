"""specializations/upravlenie.py — Управленческая деятельность."""
from ._base import make_handlers

SPEC_NAME  = "upravlenie"
SPEC_LABEL = "Управленческая деятельность"
SPEC_EMOJI = "💼"

handlers = make_handlers(SPEC_NAME, SPEC_LABEL, SPEC_EMOJI)
