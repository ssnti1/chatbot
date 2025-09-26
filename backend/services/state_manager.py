# backend/services/state_manager.py
from __future__ import annotations
import re
from typing import Literal

_SESSIONS: dict[str, dict] = {}

def get_state(session_id: str) -> dict:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {
            "espacio": None,
            "espacio_source": None,
            "necesidad": None,
            "preferencias": {"vatios": None, "temp_color": None, "instalacion": None, "presupuesto": None},
            "last_query": None,
            "last_filter": None,
            "last_items": [],
            "page": 0,
            "seen_codes": set(),
            "focus": set(),
            "result_seed": 0,
        }
    return _SESSIONS[session_id]

_MORE = {
    "muestrame otros","muestrame mas","mostrar mas","mostrar más","otros","más","mas",
    "enséñame otros","muéstrame otros","enséñame más","muéstrame más",
    "muestrame otras","otras","enséñame otras","muéstrame otras",
    "ver mas","ver más","ver otros","ver otras","siguiente","continuar",
    "más productos","mas productos","más opciones","mas opciones"
}
def is_more_signal(text: str) -> bool:
    t = (text or "").lower().strip()
    return any(t.startswith(x) or t == x for x in _MORE)

_WATTS = re.compile(r"(\d{1,3})\s*?w\b", re.I)
_TEMP  = re.compile(r"(2700|3000|3500|4000|5000|6500)\s*?k\b", re.I)
_MONEY = re.compile(r"(\$?\s?\d{2,3}\.?\d{0,3}\.?\d{0,3}|\d+\s?(mil|k))", re.I)

def maybe_extract_slots(text: str) -> dict:
    out = {}
    if not text:
        return out
    m = _WATTS.search(text)
    if m: out.setdefault("preferencias", {})["vatios"] = int(m.group(1))
    m = _TEMP.search(text)
    if m: out.setdefault("preferencias", {})["temp_color"] = int(m.group(1))
    m = _MONEY.search(text)
    if m: out.setdefault("preferencias", {})["presupuesto"] = m.group(1)
    return out

Intent = Literal["keyword", "more"]

def is_keyword_signal(text: str) -> bool:
    t = (text or "").strip()
    return bool(re.search(r"[a-zA-Z0-9]", t))

def classify_intent(text: str) -> Intent:
    if is_more_signal(text):
        return "more"
    return "keyword"

def update_state(session_id: str, delta: dict):
    s = get_state(session_id)
    s.update(delta)
