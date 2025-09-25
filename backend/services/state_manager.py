import re
from typing import Literal
from backend.services.focus_rules import FOCUS_RULES
from backend.services.search_service import CATEGORY_MAP
import difflib

_SESSIONS: dict[str, dict] = {}

def get_state(session_id: str) -> dict:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {
            "espacio": None,
            "espacio_source": None,  
            "necesidad": None,
            "preferencias": {
                "vatios": None, "temp_color": None, "instalacion": None, "presupuesto": None
            },
            "historial": [],
            "last_filter": None,
            "last_items": [],
            "page": 0,
            "seen_codes": set(),
            "focus": set(),
        }
    return _SESSIONS[session_id]


def _detect_focuses_from_text(text: str) -> set[str]:
    t = (text or "").lower()
    active = set()
    for key, rule in FOCUS_RULES.items():
        if any(alias in t for alias in rule["aliases"]):
            active.add(key)
    return active

def update_state(session_id: str, message: dict):
    st = get_state(session_id)
    st["historial"].append(message)
    return st

_WATTS = re.compile(r"(\d{1,3})\s*?w\b", re.I)
_TEMP  = re.compile(r"(3000|4000|6500)\s*?k\b", re.I)
_MONEY = re.compile(r"(\$?\s?\d{2,3}\.?\d{0,3}\.?\d{0,3}|\d+\s?(mil|k))", re.I)

ESPACIOS = {"oficina","piscina","bodega","pasillo","sala","cocina","exterior","jardin","jardín","calle"}
NECESIDADES = {"decorativa","industrial","emergencia","panel","tubo","colgante","campana","flood","reflector",
               "riel","magnético","magnetico","gu10","e27"}


_GREETINGS = {"hola","holi","buenas","buenos dias","buenas tardes","buenas noches","que tal","hey","hi","hello"}
_MORE = {
    "muestrame otros","muestrame mas","mostrar mas","mostrar más","otros","más","mas",
    "enséñame otros","muéstrame otros","enséñame más","muéstrame más",
    "muestrame otras","otras","enséñame otras","muéstrame otras", "recomiendame mas", "recomiéndame más", "recomiendame más"
}
_CODE_RE = re.compile(r"\b[A-Z0-9]{3,}(?:-[A-Z0-9]+)?\b", re.I)

_KEYWORDS_SIGNAL = {
    "piscina","ip68","sumergible","oficina","bodega","exterior","jardin","jardín",
    "decorativa","industrial","emergencia","panel","tubo","colgante","campana",
    "flood","reflector","fuente","driver","power","transformador","12v","24v",
    "tira","cinta","neon","led strip","rgb","controlador","nicho","riel","track",
    "magnético","magnetico","gu10","e27","dc42v","100w", "estadio","cancha"
}

Intent = Literal["greeting","more","product_search","faq_or_smalltalk"]


def classify_intent(text: str) -> Intent:
    t = (text or "").strip().lower()

    if t in _GREETINGS or any(t.startswith(g) for g in _GREETINGS):
        return "greeting"

    if (
        t in _MORE
        or re.fullmatch(r'(mu[ée]strame|ense[ñn]ame)\s+(m[aá]s|otros|otras)\s*\.?', t)
    ):
        return "more"

    if _CODE_RE.search(text or "") or any(k in t for k in _KEYWORDS_SIGNAL):
        return "product_search"

    return "faq_or_smalltalk"


def is_keyword_signal(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in _KEYWORDS_SIGNAL)



VALID_CATEGORIES = {
    "driver","lamp","tubo","panel","seguridad","exterior",
    "alumbrado_publico","interior","emergencia","solar",
    "decorativa","industrial","accesorio",
    "lamparas","lamparas decorativas"
}

def _map_to_category(text: str) -> str:
    import difflib
    text = text.lower().replace(" ", "_")
    match = difflib.get_close_matches(text, VALID_CATEGORIES, n=1, cutoff=0.86)
    return match[0] if match else ""

def maybe_extract_slots(state: dict, user_msg: str):
    low = (user_msg or "").lower().strip()

    if low in _GREETINGS:
        return

    state["espacio_source"] = None

    for alias, target in CATEGORY_MAP.items():
        if alias in low:
            state["espacio"] = target
            state["espacio_source"] = "alias"
            return

    for cat in VALID_CATEGORIES:
        if cat in low:
            state["espacio"] = cat
            state["espacio_source"] = "direct"
            return

    has_domain_clues = any(k in low for k in _KEYWORDS_SIGNAL)
    if has_domain_clues and len(low) >= 6 and " " in low:
        mapped = _map_to_category(low)
        if mapped:
            state["espacio"] = mapped
            state["espacio_source"] = "fuzzy"

