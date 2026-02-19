"""specializations/bezopasnost.py — Обеспечение собственной безопасности."""
from ._base import make_handlers

SPEC_NAME  = "bezopasnost"
SPEC_LABEL = "Обеспечение собственной безопасности"
SPEC_EMOJI = "🔒"

handlers = make_handlers(SPEC_NAME, SPEC_LABEL, SPEC_EMOJI)
