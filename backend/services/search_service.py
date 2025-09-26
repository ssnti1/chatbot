# backend/services/search_service.py
from __future__ import annotations
from typing import List, Dict, Tuple, Set
import re
import math
import random
import unicodedata

from backend.services.product_loader import load_products, PRODUCTOS

# =====================================================
# Normalización y tokenización (100% data-driven)
# =====================================================
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

def _norm(s: str) -> str:
    s = _strip_accents((s or "").lower())
    s = re.sub(r"[^\w\s\-]+", " ", s)
    s = re.sub(r"[\s_]+", " ", s).strip()
    return s

def _tok(s: str) -> List[str]:
    s = _norm(s)
    # separa "3000k", "ip65", "12v" de forma robusta
    s = re.sub(r"([0-9]+)([a-z]+)", r"\1 \2", s)
    s = re.sub(r"([a-z]+)([0-9]+)", r"\1 \2", s)
    toks = re.split(r"[^a-z0-9]+", s)
    return [t for t in toks if t and len(t) >= 2]

_STOPWORDS_ES: Set[str] = {
    "de","del","la","el","los","las","un","una","unos","unas","y","o","u","a","en",
    "por","para","con","sin","que","quien","quién","cuando","cuándo","donde","dónde",
    "como","cómo","cual","cuál","cuáles","es","son","ser","estar","haber","hay","hace",
    "al","este","esta","esto","estas","estos","lo","le","les","mi","tu","su","sus",
    "hola","buenas","buenos","dias","días","tardes","noches","quiero","necesito"
}

# =====================================================
# Índice derivado del catálogo (sin listas estáticas)
# =====================================================
_INDEX_READY = False
_INDEX: Dict[str, Dict[str, Set[str]]] = {}   # code -> {name,tags,cats,slug,code,blob}
_VOCAB: Dict[str, int] = {}                    # token -> DF (doc frequency)
_IDF: Dict[str, float] = {}                    # token -> idf
_ALL_CATEGORY_TERMS: Set[str] = set()

def _ensure_index():
    global _INDEX_READY, _INDEX, _VOCAB, _IDF, _ALL_CATEGORY_TERMS, PRODUCTOS
    if _INDEX_READY:
        return
    if not PRODUCTOS:
        load_products()

    _INDEX.clear()
    _VOCAB.clear()
    _ALL_CATEGORY_TERMS.clear()

    # construir índice a partir del blob del loader
    for code, p in PRODUCTOS.items():
        name = set(_tok(p.get("name_norm") or p.get("name") or ""))
        tags = set(_tok(" ".join(p.get("tags_norm") or p.get("tags") or [])))
        cats = set(_tok(" ".join(p.get("categories_norm") or p.get("categories") or [])))
        slug = set(p.get("slug_toks") or [])
        codef = set(_tok(p.get("code") or ""))

        blob = set(_tok(" ".join([
            p.get("search_blob") or "",
            p.get("name_norm") or "",
            " ".join(p.get("categories_norm") or []),
            " ".join(p.get("tags_norm") or []),
            " ".join(slug or []),
            p.get("code") or "",
        ])))

        _INDEX[code] = {
            "name": name, "tags": tags, "cats": cats, "slug": slug, "code": codef, "blob": blob
        }

        for t in set().union(name, tags, cats, slug, codef, blob):
            _VOCAB[t] = _VOCAB.get(t, 0) + 1

        _ALL_CATEGORY_TERMS |= cats

    N = max(1, len(_INDEX))
    _IDF.update({t: math.log((N + 1) / (df + 0.5)) + 1.0 for t, df in _VOCAB.items()})
    _INDEX_READY = True

def _idf(t: str) -> float:
    return _IDF.get(t, 0.5)

def _ngrams(s: str, n: int = 3) -> Set[str]:
    s = f" {s} "
    return {s[i:i+n] for i in range(max(0, len(s) - n + 1))}

def _char_sim(a: str, b: str) -> float:
    A = _ngrams(a); B = _ngrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)

def _expand_query_tokens(q_toks: List[str], k_fallback: int = 6) -> List[str]:
    _ensure_index()
    base = [t for t in q_toks if t not in _STOPWORDS_ES]
    if not base:
        return []
    cand: Dict[str, float] = {}
    for t in base:
        for v in _VOCAB.keys():
            sim = _char_sim(t, v)
            if sim >= 0.35:
                cand[v] = max(cand.get(v, 0.0), sim)
    return sorted(cand.keys(), key=lambda x: (-cand[x], -_idf(x)))[:k_fallback]

def _score_product(code: str, q_toks: List[str], expand: List[str]) -> float:
    f = _INDEX[code]
    name, tags, cats, slug, codef, blob = f["name"], f["tags"], f["cats"], f["slug"], f["code"], f["blob"]

    q = [t for t in q_toks if t not in _STOPWORDS_ES]
    q = list(dict.fromkeys(q + [e for e in expand if e not in q]))  # unique, preserve order
    if not q:
        return 0.0

    def field_match(field: Set[str]) -> float:
        score = 0.0
        for t in q:
            if t in field:
                score += _idf(t) * 1.0
            elif any(t in ft or ft in t for ft in field):
                score += _idf(t) * 0.5
        # pequeño premio por múltiples coincidencias
        exact = sum(1 for t in q if t in field)
        sub = 0
        for t in q:
            if any(t in ft or ft in t for ft in field):
                sub += 1
        return score + 0.15 * (exact + sub)

    s_name = field_match(name)
    s_tags = field_match(tags)
    s_cats = field_match(cats)
    s_slug = field_match(slug)
    s_code = field_match(codef)
    s_blob = field_match(blob) * 0.6

    return (1.6 * s_name) + (1.0 * s_cats) + (0.9 * s_slug) + (0.7 * s_tags) + (0.5 * s_code) + (1.2 * s_blob)

def _paginate(items: List[Dict], limit: int, offset: int, exclude_codes: Set[str] | None = None) -> List[Dict]:
    exclude_codes = exclude_codes or set()
    out = [it for it in items if it["code"] not in exclude_codes]
    return out[offset: offset + limit]

def search_candidates(user_msg: str, state: dict, limit: int = 5, offset: int = 0, exclude_codes: List[str] | None = None) -> List[Dict]:
    _ensure_index()
    text = _norm(user_msg)
    q_toks = _tok(text)
    # Sin términos útiles => no devolvemos productos
    if not [t for t in q_toks if t not in _STOPWORDS_ES]:
        return []

    expand = _expand_query_tokens(q_toks)

    rng = random.Random(state.get("result_seed") or 0)
    scored: List[Tuple[float, Dict]] = []
    for code, p in PRODUCTOS.items():
        score = _score_product(code, q_toks, expand)
        if score <= 0:
            continue
        payload = {
            "code": code,
            "name": p.get("name"),
            "price": p.get("price"),
            "url": p.get("url"),
            "img_url": p.get("img_url"),
        }
        jitter = rng.random() * 0.01  # desempate estable
        scored.append((score + jitter, payload))

    scored.sort(key=lambda x: (-x[0], x[1]["code"]))
    flattened = [it for _, it in scored]
    return _paginate(flattened, limit=limit, offset=offset, exclude_codes=set(exclude_codes or []))

def _detect_categories_from_text(user_msg: str) -> List[str]:
    _ensure_index()
    msg = _norm(user_msg)
    toks = set(_tok(user_msg))
    detected: Set[str] = set()
    for term in _ALL_CATEGORY_TERMS:
        if term in msg or any(term in t or t in term for t in toks):
            detected.add(term)
            if len(detected) >= 6:
                break
    return list(detected)
