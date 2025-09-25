import re
import unicodedata
from typing import List, Dict, Tuple, Set, Optional
import random
from backend.services.product_loader import load_products, PRODUCTOS
from backend.services.focus_rules import FOCUS_RULES

# ============================
# Carga segura del catálogo
# ============================
def _ensure_catalog():
    global PRODUCTOS
    if not PRODUCTOS:
        PRODUCTOS, _ = load_products()


# ============================
# Vocablo de dominio + Off-topic
# ============================

_DOMAIN_VOCAB: Set[str] = set()
_DOMAIN_READY: bool = False

def _ensure_domain_vocab():
    """
    Construye un vocabulario de dominio dinámico a partir del catálogo y reglas de foco.
    Se genera 1 sola vez en memoria.
    """
    global _DOMAIN_READY, _DOMAIN_VOCAB
    if _DOMAIN_READY:
        return
    _ensure_catalog()
    vocab: Set[str] = set()

    def _add_text(s: str):
        for t in _tokenize(_norm(s or "")):
            if len(t) >= 3:
                vocab.add(t)

    for p in PRODUCTOS.values():
        try:
            blob = _product_blob(p)  
        except Exception:
            blob = f"{p.get('name','')} {' '.join(p.get('categories',[]) or [])} {p.get('description','')} {p.get('code','')}"
        _add_text(blob)

    try:
        for r in FOCUS_RULES.values():
            for key in ("aliases", "must_any", "accessories_any", "must_not"):
                for val in r.get(key, []) or []:
                    _add_text(val)
    except Exception:
        pass

    _DOMAIN_VOCAB = vocab
    _DOMAIN_READY = True

_LIGHTING_HINT_RE = re.compile(
    r"(?:\b(?:e27|e14|g9|gu10|mr16|t8|t5)\b)|"          # casquillos/tipos
    r"(?:\bip6[5-8]\b)|"                                # IP65..IP68
    r"(?:\b(?:12|24|110|220)v\b)|"                      # voltajes
    r"(?:\b\d{2,3}w\b)|"                                # vatios (10w..999w)
    r"(?:\b\d{3,4}k\b)|"                                # temperatura (2700k..6500k)
    r"(?:\b(?:lm|lumen(?:es)?)\b)",                     # lúmenes
    flags=re.IGNORECASE
)

def _has_lighting_hints(msg: str) -> bool:
    return bool(_LIGHTING_HINT_RE.search(msg))

_DOMAIN_VOCAB: Set[str] = set()
_DOMAIN_READY: bool = False

_CORE_DOMAIN_TOKENS: Set[str] = {
    "led","lampara","lamparas","luz","luces","aplique","reflector","panel","tubo","riel",
    "decorativa","industrial","piscina","sumergible","ip65","ip66","ip67","ip68",
    "gu10","e27","mr16","g9","t8","t5","rgb","driver","fuente","controlador","campana","highbay",
    "solar","exterior","interior","emergencia","seguridad","cctv"
}

_WEAK_TOKENS: Set[str] = {"oro","dorado","dorada","plateado","plateada","negro","negra","blanco","blanca","gris","mate","brillante"}

_STOPWORDS_ES: Set[str] = {
    "de","del","la","el","los","las","un","una","unos","unas","y","o","u","a","en",
    "por","para","con","sin","que","quien","quién","cuando","cuándo","donde","dónde",
    "como","cómo","cual","cuál","cuáles","es","son","ser","estar","haber","hay","hace",
    "al","este","esta","esto","estas","estos","lo","le","les","mi","tu","su","sus"
}

def _ensure_domain_vocab():
    """
    Construye un vocabulario de dominio dinámico a partir del catálogo y reglas de foco.
    Se genera 1 sola vez en memoria.
    """
    global _DOMAIN_READY, _DOMAIN_VOCAB
    if _DOMAIN_READY:
        return
    _ensure_catalog()
    vocab: Set[str] = set()

    def _add_text(s: str):
        for t in _tokenize(_norm(s or "")):
            if len(t) >= 3:
                vocab.add(t)

    for p in PRODUCTOS.values():
        try:
            blob = _product_blob(p)
        except Exception:
            blob = f"{p.get('name','')} {' '.join(p.get('categories',[]) or [])} {p.get('description','')} {p.get('code','')}"
        _add_text(blob)

    try:
        for r in FOCUS_RULES.values():
            for key in ("aliases", "must_any", "accessories_any", "must_not"):
                for val in r.get(key, []) or []:
                    _add_text(val)
    except Exception:
        pass

    _DOMAIN_VOCAB = vocab
    _DOMAIN_READY = True

_LIGHTING_HINT_RE = re.compile(
    r"(?:\b(?:e27|e14|g9|gu10|mr16|t8|t5)\b)|"
    r"(?:\bip6[5-8]\b)|"
    r"(?:\b(?:12|24|110|220)v\b)|"
    r"(?:\b\d{2,3}w\b)|"
    r"(?:\b\d{3,4}k\b)|"
    r"(?:\b(?:lm|lumen(?:es)?)\b)",
    flags=re.IGNORECASE
)

def _has_lighting_hints(msg: str) -> bool:
    return bool(_LIGHTING_HINT_RE.search(msg or ""))

def is_offtopic(user_msg: str) -> bool:
    """
    Heurística robusta y *dinámica*:
      IN-TOPIC si:
        - Hay pistas claras de iluminación (IP, W, K, casquillos), o
        - Coincide ≥1 token del núcleo (_CORE_DOMAIN_TOKENS), o
        - Coinciden ≥2 tokens del vocabulario dinámico *excluyendo* tokens débiles,
          o la razón de coincidencias (sin débiles) ≥ 0.40.
      OFF-TOPIC en otro caso.
    """
    text = _norm(user_msg or "")
    toks = [t for t in _tokenize(text) if len(t) >= 3 and t not in _STOPWORDS_ES]
    if not toks:
        return False  
    _ensure_domain_vocab()

    if _has_lighting_hints(text):
        return False

    if any(t in _CORE_DOMAIN_TOKENS for t in toks):
        return False

    domain_hits = sum(1 for t in toks if (t in _DOMAIN_VOCAB and t not in _WEAK_TOKENS))
    ratio = domain_hits / max(1, len(toks))

    return not (domain_hits >= 2 or ratio >= 0.40)

# ============================
# Normalización y utilidades
# ============================
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

def _norm(s: str) -> str:
    s = _strip_accents((s or "").lower())
    s = re.sub(r"[^a-z0-9\s\-\_\/\.\%]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _tokenize(s: str) -> List[str]:
    return _norm(s).split()

def _product_blob(p: Dict) -> str:
    parts = [
        p.get("code") or "",
        p.get("name") or "",
        " ".join(p.get("tags") or []),
        " ".join(p.get("categories") or []),
        str(p.get("category") or ""),
    ]
    return " ".join(parts)

# ============================
# Mapa de categorías (con alias)
# ============================

CATEGORY_MAP = {
    # --- Cintas LED ---
    "cintas led": "cintas led",
    "tiras led": "cintas led",
    "tiras luces led": "cintas led",
    "luces led flexibles": "cintas led",
    "luces neón": "cintas led",
    "neon led": "cintas led",
    "luces de tira": "cintas led",
    "luces de rollo": "cintas led",
    "led strip": "cintas led",
    "flex strip": "cintas led",
    "strip light": "cintas led",
    "led neon": "cintas led",

    # --- Fuentes de poder ---
    "fuente": "fuentes de poder",
    "fuentes de poder": "fuentes de poder",
    "driver": "fuentes de poder",
    "drivers": "fuentes de poder",
    "power supply": "fuentes de poder",
    "transformador": "fuentes de poder",
    "adaptador": "fuentes de poder",
    "alimentador": "fuentes de poder",
    "controlador": "fuentes de poder",

    # --- Highbay / Campanas ---
    "highbay": "industrial",
    "campana": "industrial",
    "campana ufo": "industrial",
    "campana industrial": "industrial",
    "industrial highbay": "industrial",
    "ufo light": "industrial",
    "high bay": "industrial",

    # --- Reflectores ---
    "reflector": "exterior",
    "reflectores": "exterior",
    "reflectores led": "exterior",
    "luces exteriores": "exterior",
    "foco reflector": "exterior",
    "proyector": "exterior",
    "flood light": "exterior",
    "spot led": "exterior",
    "estadio": "exterior",
    "cancha": "exterior",

    # --- Paneles LED ---
    "panel": "panel",
    "paneles": "panel",
    "panel de techo": "panel",
    "luz de techo": "panel",
    "panel embutido": "panel",
    "downlight panel": "panel",
    "led panel light": "panel",

    # --- Bombillos LED ---
    "bombillo": "lamp",
    "bombillos": "lamp",
    "bombilla": "lamp",
    "foco led": "lamp",
    "ampolleta": "lamp",
    "bulb": "lamp",
    "lampara rosca": "lamp",
    "led bulb": "lamp",

    # --- Lámparas decorativas ---
    "lampara decorativa": "decorativa",
    "lamparas decorativas": "decorativa",
    "lamparas deco": "decorativa",
    "lamparas diseño": "decorativa",
    "colgantes": "decorativa",
    "decorativas": "decorativa",
    "lampara de techo": "decorativa",
    "pendant light": "decorativa",
    "decorative lamp": "decorativa",
    "lampara": "lamp",
    "lamparas": "lamp",
    "lampara solar": "solar",
    "lampara emergencia": "emergencia",
    "lampara de techo": "decorativa",

    # ➕ Sinónimos colombianos
    "pieza": "decorativa",
    "alcoba": "decorativa",
    "habitacion": "decorativa",
    "habitación": "decorativa",
    "dormitorio": "decorativa",
    "sala": "decorativa",
    "comedor": "decorativa",
    "living": "decorativa",
    "cuarto": "decorativa",

    # --- Oficina ---
    "luces oficina": "oficina",
    "lamparas oficina": "oficina",
    "iluminación oficina": "oficina",
    "office light": "oficina",
    "luminaria corporativa": "oficina",
    "techo oficina": "oficina",
    "ofisina": "oficina",
    "oficina": "oficina",
    "estudio": "oficina",
    "consultorio": "oficina",
    "recepcion": "oficina",
    "recepción": "oficina",

    # --- Industrial ---
    "luces industriales": "industrial",
    "lamparas industriales": "industrial",
    "iluminación bodega": "industrial",
    "warehouse light": "industrial",
    "factory light": "industrial",
    "industrial lamp": "industrial",
    "bodega": "industrial",
    "taller": "industrial",
    "fabrica": "industrial",
    "fábrica": "industrial",
    "nave": "industrial",
    "planta": "industrial",
    "galpon": "industrial",
    "galpón": "industrial",

    # --- Piscina ---
    "luces piscina": "piscina",
    "luces sumergibles": "piscina",
    "iluminación piscina": "piscina",
    "pool light": "piscina",
    "submersible led": "piscina",
    "luces acuáticas": "piscina",
    "jacuzzi": "piscina",
    "piscina": "piscina",
    "sumergible": "piscina",
    "ip68": "piscina",
    "acuatica": "piscina",
    "acuática": "piscina",

    # --- Solares ---
    "lampara solar": "solar",
    "lamparas solares": "solar",
    "lámpara solar": "solar",
    "lámparas solares": "solar",
    "luminaria solar": "solar",
    "luminarias solares": "solar",
    "luz solar": "solar",
    "luces solares": "solar",
    "iluminacion solar": "solar",
    "iluminación solar": "solar",
    "reflector solar": "solar",
    "reflectores solares": "solar",
    "solar light": "solar",
    "solar led": "solar",

    # --- Tubos ---
    "tubo": "tubo",
    "tubos": "tubo",
    "tubo fluorescente led": "tubo",
    "fluorescente led": "tubo",
    "tube light": "tubo",
    "led tube": "tubo",
    "t8 led": "tubo",

    # --- Emergencia ---
    "emergencia": "emergencia",
    "salida emergencia": "emergencia",
    "luz emergencia": "emergencia",
    "exit light": "emergencia",
    "emergency lamp": "emergencia",
    "señal salida": "emergencia",

    # --- Apliques ---
    "aplique": "decorativa",
    "apliques pared": "decorativa",
    "luces pared": "decorativa",
    "wall light": "decorativa",
    "aplique exterior": "decorativa",
    "sconce": "decorativa",
    "wall lamp": "decorativa",

    # --- Riel ---
    "luces riel": "riel",
    "lamparas riel": "riel",
    "track light": "riel",
    "sistema riel": "riel",
    "focos riel": "riel",
    "rail lighting": "riel",

    # --- Smart / Seguridad ---
    "camara": "seguridad",
    "camara solar": "seguridad",
    "cctv": "seguridad",
    "cámara de seguridad": "seguridad",
    "smart light": "seguridad",
    "wifi light": "seguridad",
    "inteligente": "seguridad",
    "porteria": "seguridad",
    "portería": "seguridad",
}

ACCESSORY_INTENT_WORDS = {
    "accesorio", "accesorios", "fuente", "driver", "controlador", "controller",
    "nicho", "soporte", "conector", "transformador", "rgb", "rgbw"
}

ACCESSORIES_BY_CATEGORY: Dict[str, List[str]] = {
    "piscina": ["nicho", "controlador rgb", "rgb", "fuente ip68", "waterproof", "pentair"],
    "riel": ["conector", "fuente", "driver", "dc42v", "100w", "controlador"],
    "tiras": ["fuente", "driver", "controlador", "rgb", "12v", "24v"],
    "exterior": [],
    "industrial": [],
    "decorativa": [],
    "emergencia": [],
    "gu10": [],
    "e27": [],
    "panel": [],
    "lineal": [],
    "colgante": [],
    "alumbrado publico": [],
}

from collections import defaultdict

REVERSE_CATEGORY_MAP: Dict[str, List[str]] = defaultdict(list)
for alias, target in CATEGORY_MAP.items():
    REVERSE_CATEGORY_MAP[target].append(alias)

# ============================
# Fuzzy matching
# ============================
def _fuzzy_contains(a: str, b: str) -> bool:
    a = _norm(a)
    b = _norm(b)
    b_tokens = _tokenize(b)
    if not b_tokens:
        return False

    a_tokens = _tokenize(a)

    def token_matches_any(w: str) -> bool:
        if w in a_tokens:
            return True
        if any(tok.startswith(w) for tok in a_tokens):
            return True
        if "-" in w:
            parts = w.split("-")
            for i in range(len(a_tokens) - len(parts) + 1):
                if all(a_tokens[i + j].startswith(parts[j]) for j in range(len(parts))):
                    return True
        return False

    return all(token_matches_any(w) for w in b_tokens)

def _detect_categories_from_text(user_msg: str) -> list[str]:
    prods, _ = load_products()
    norm_msg = _norm(user_msg)

    detected = []

    for alias, target in CATEGORY_MAP.items():
        if alias in norm_msg:
            detected.append(target)

    for p in prods.values():
        for cat in p.get("categories_norm", []):
            if norm_msg in cat or cat in norm_msg:
                detected.append(cat)

    return list(set(detected))

# ============================
# Constraints (regex/sets)
# ============================
IP_RE   = re.compile(r"\bip\s*(6[5678]|[0-5]?\d)\b", re.I)
VOLT_RE = re.compile(r"\b(12\s*v|24\s*v|110\s*v|220\s*v|12-?voltios?|24-?voltios?)\b", re.I)
SOCKETS = {"gu10","e27"}
RGB_WORDS = {"rgb","rgbw","controlador rgb"}

def _extract_constraints(text: str) -> Dict:
    txt = text or ""
    t = _norm(txt)
    ips = set("ip"+m.group(1) for m in IP_RE.finditer(txt))
    volts = set(m.group(1).lower().replace(" ", "") for m in VOLT_RE.finditer(txt))
    socks = {s for s in SOCKETS if s in t}

    wants_rgb = any(w in t for w in RGB_WORDS)

    wants_sumergible = (
        ("sumergible" in t) or
        ("ip68" in t) or
        ("piscina" in t) or
        ("pool" in t) or
        ("acuatic" in t) 
    )

    return {
        "ips": ips,
        "volts": volts,
        "sockets": socks,
        "rgb": wants_rgb,
        "sumergible": wants_sumergible,
    }

# ============================
# Focus
# ============================
def _passes_focus(nb: str, active_focus: Set[str]) -> bool:
    if not active_focus:
        return True
    for f in active_focus:
        rule = FOCUS_RULES.get(f)
        if not rule:
            continue
        must_any = [ _norm(x) for x in (rule.get("must_any") or []) ]
        must_not = [ _norm(x) for x in (rule.get("must_not") or []) ]
        if must_any and not any(x in nb for x in must_any):
            return False
        if must_not and any(x in nb for x in must_not):
            return False
    return True

# ============================
# Guards de categorías (STRICT MODE)
# ============================
def _build_category_guards(active_cats: List[str]) -> List[Set[str]]:
    """
    Construye conjuntos de alias normalizados para cada categoría activa.
    Habilita STRICT_MODE (fix de retorno).
    """
    guards: List[Set[str]] = []
    for cat in active_cats:
        alias_list = REVERSE_CATEGORY_MAP.get(cat, []) if 'REVERSE_CATEGORY_MAP' in globals() else []
        if not alias_list:
            alias_list = [cat]
        norm_aliases = { _norm(a) for a in alias_list if str(a).strip() }
        if norm_aliases:
            guards.append(norm_aliases)
    return guards

# ============================
# Chequeo estricto de categorías (con parciales)
# ============================
def _passes_categories_strict(nb: str, guards: List[Set[str]], product: dict) -> bool:
    """
    Pasa si cumple al menos un alias de cada categoría activa,
    aceptando coincidencias parciales contra categories_norm.
    """
    if not guards:
        return True

    prod_cats = product.get("categories_norm") or []
    prod_cat_text = " ".join(prod_cats)

    for alias_set in guards:
        ok = False
        for alias in alias_set:
            if alias in nb: 
                ok = True
                break
            if any(alias in pc or pc in alias for pc in prod_cats): 
                ok = True
                break
            if alias in prod_cat_text:
                ok = True
                break
        if not ok:
            return False
    return True


def _expand_query_tokens(user_msg: str) -> list[str]:
    """
    Expande tokens de la consulta para buscar coincidencias *parciales* en todo el catálogo,
    sin atar a categorías. Incluye normalización y variantes simples (plural/singular).
    """
    toks = [t for t in _tokenize(user_msg) if len(t) >= 2]
    expanded = set()
    for t in toks:
        expanded.add(t)
        nt = _norm(t)
        expanded.add(nt)
        if nt.endswith("es") and len(nt) > 3:
            expanded.add(nt[:-2]) 
        if nt.endswith("s") and len(nt) > 3:
            expanded.add(nt[:-1])  
    return [x for x in expanded if len(x) >= 2]


# ============================
# Coincidencia parcial por tokens (global)
# ============================
def _partial_token_match(nb: str, toks: list[str]) -> bool:
    """
    Coincidencia parcial *global*: devuelve True si suficientes tokens aparecen como substrings en nb.
    - Umbral adaptativo: al menos 1 token, o ~50% (capado a 3) si la consulta es larga.
    """
    if not toks:
        return True
    hits = sum(1 for t in toks if t in nb)
    need = 1
    if len(toks) >= 4:
        need = min(3, (len(toks) + 1) // 2)
    return hits >= need


# ============================
# Presupuesto
# ============================
def _parse_budget(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    s = raw.strip().lower().replace(" ", "")
    s = s.replace("$","")
    if s.endswith("k"):
        try:
            return int(float(s[:-1]) * 1000)
        except Exception:
            return None
    if s.endswith("mil"):
        try:
            return int(float(s[:-3]) * 1000)
        except Exception:
            return None
    s = s.replace(".", "").replace(",", "")
    if s.isdigit():
        return int(s)
    return None

# ============================
# Coincidencia por CÓDIGO
# ============================
_CODE_RE = re.compile(r"\b[A-Za-z0-9]{3,}(?:-[A-Za-z0-9]+)?\b", re.I)

def _code_hits(user_msg: str) -> List[Dict]:
    _ensure_catalog()
    seen: Set[str] = set()

    for m in _CODE_RE.finditer(user_msg or ""):
        code_q = m.group(0).upper()
        p = PRODUCTOS.get(code_q)

        if not p:
            for _, rec in PRODUCTOS.items():
                if str(rec.get("code","")).upper() == code_q:
                    p = rec
                    break

        if not p:
            for _, rec in PRODUCTOS.items():
                if str(rec.get("code","")).upper().startswith(code_q):
                    p = rec
                    break

        if not p:
            continue

        code = str(p.get("code") or "").upper()
        if code in seen:
            continue
        seen.add(code)

        return [{
            "code": code,
            "name": p.get("name"),
            "price": p.get("price"),
            "url": p.get("url"),
            "img_url": p.get("img_url"),
        }]

    return []


# ============================
# Scoring
# ============================
def _score_product(p: Dict, toks: List[str], budget_num: Optional[int]) -> int:
    nb = _norm(_product_blob(p))
    score = 0

    name_words = set(_tokenize(p.get("name","")))
    for t in toks:
        if t in name_words:
            score += 5
        elif t in nb:
            score += 3
        else:
            if any(w.startswith(t) for w in name_words):
                score += 1

    query_has_venue = any(t in {"estadio", "cancha"} for t in toks)
    if query_has_venue:
        if any(w in nb for w in ("reflector", "flood", "proyector")):
            score += 4
        if any(w in nb for w in ("ip65", "ip66", "ip67")):
            score += 2

        import re as _re
        m = _re.search(r'(\d{2,4})\s*w\b', nb, flags=_re.I)
        if m:
            try:
                w = int(m.group(1))
                if w >= 150:
                    score += 4
                elif w <= 50:
                    score -= 2
            except Exception:
                pass

        if "solar" not in toks and "solar" in nb:
            score -= 4

        if any(w in nb for w in ("cctv", "camara", "cámara", "hikvision")):
            score -= 6

    if budget_num is not None:
        price_str = str(p.get("price") or "")
        price_num = None
        s = price_str.replace("$","").replace(".","").replace(",","").strip()
        if s.isdigit():
            price_num = int(s)
        if price_num:
            if abs(price_num - budget_num) <= max(1, int(budget_num * 0.2)):
                score += 2
            elif price_num > int(budget_num * 1.5):
                score -= 2

    return score

# ============================
# Búsqueda principal
# ============================
def search_candidates(user_msg: str,
                      state: dict,
                      limit: int = 5,
                      offset: int = 0,
                      exclude_codes: Optional[Set[str]] = None) -> List[Dict]:
    """
    Búsqueda *global y parcial* sobre todo el catálogo:
    - No fuerza categorías ni 'modo estricto' por defecto.
    - Aplica 'focus' si está activo (excluye categorías indebidas, p. ej. piscina vs exterior).
    - Usa substring matching sobre el 'blob' normalizado de cada producto.
    - Respeta constraints explícitos (IP, voltajes, sockets, RGB, sumergible).
    - Soporta paginación con 'seen_codes' para 'muéstrame otras/más'.
    """
    _ensure_catalog()
    exclude_codes = exclude_codes or set()

    code_hits = _code_hits(user_msg)
    if code_hits:
        if "seen_codes" in state:
            state["seen_codes"].clear()
        return code_hits

    active_focus: Set[str] = set(state.get("focus") or [])
    if not active_focus:
        try:
            from backend.services.state_manager import _detect_focuses_from_text as _detect
            active_focus = set(_detect(user_msg))
        except Exception:
            active_focus = set()

    toks = _expand_query_tokens(user_msg)

    cons = _extract_constraints(user_msg)

    budget_num = _parse_budget((state.get("preferencias") or {}).get("presupuesto"))

    if "result_seed" not in state:
        state["result_seed"] = random.getrandbits(32)
    rng = random.Random(state["result_seed"])

    scored: List[Tuple[float, Dict]] = []
    for code, p in PRODUCTOS.items():
        codeU = str(p.get("code") or code).upper()
        if codeU in exclude_codes:
            continue

        nb = _norm(_product_blob(p))

        if active_focus and not _passes_focus(nb, active_focus):
            continue

        if toks and not _partial_token_match(nb, toks):
            continue

        if not _passes_constraints(nb, cons, p):
            continue

        score = _score_product(p, toks, budget_num)
        if score <= 0:
            score = 1

        payload = {
            "code": codeU,
            "name": p.get("name"),
            "price": p.get("price"),
            "url": p.get("url"),
            "img_url": p.get("img_url"),
        }

        jitter = rng.random() * 0.49
        scored.append((float(score) + jitter, payload))

    scored.sort(key=lambda x: (-x[0], x[1]["code"]))
    out = [it for _, it in scored]
    out = [it for it in out if it["code"] not in exclude_codes]
    return out[offset: offset + limit]


# ============================
# Constraints globales
# ============================
def _passes_constraints(nb: str, cons: Dict, prod: Dict = None) -> bool:
    """
    Aplica *solo* constraints explícitos del usuario (IP/voltajes/sockets/RGB/sumergible).
    No se fuerza ninguna categoría (la búsqueda es global y parcial).
    """
    ips: Set[str] = set(cons.get("ips") or [])
    if ips and not any(ip in nb for ip in ips):
        return False

    volts: Set[str] = set(cons.get("volts") or [])
    if volts and not any(v in nb for v in volts):
        return False

    socks: Set[str] = set(cons.get("sockets") or [])
    if socks and not any(s in nb for s in socks):
        return False

    if cons.get("rgb"):
        if not any(w in nb for w in ("rgb", "rgbw", "controlador rgb")):
            return False

    if cons.get("sumergible"):
        if not any(w in nb for w in ("sumergible", "ip68", "subacuat", "subacuatic", "submar", "acuática", "acuatica")):
            return False

    return True


