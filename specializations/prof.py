"""specializations/prof.py — Организация профессиональной подготовки."""
from ._base import make_handlers

SPEC_NAME  = "prof"
SPEC_LABEL = "Организация профессиональной подготовки"
SPEC_EMOJI = "📈"

handlers = make_handlers(SPEC_NAME, SPEC_LABEL, SPEC_EMOJI)
