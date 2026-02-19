"""specializations/aliment.py — Алименты."""
from ._base import make_handlers

SPEC_NAME  = "aliment"
SPEC_LABEL = "Алименты"
SPEC_EMOJI = "🧑‍🧑‍🧒"

handlers = make_handlers(SPEC_NAME, SPEC_LABEL, SPEC_EMOJI)
