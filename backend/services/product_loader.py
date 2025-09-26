# backend/services/product_loader.py
from __future__ import annotations
import os
import json
import unicodedata
import re
from pathlib import Path
from typing import Dict, Tuple, Any, List

# -------------------------------------------------
# Rutas configurables para el catálogo (sin hardcodear categorías)
# -------------------------------------------------
# 1) Variable de entorno ECOLITE_PRODUCTS_PATH (recomendada)
# 2) backend/data/productos.json
# 3) ./productos.json (raíz del repo)
ENV_PATH = os.getenv("ECOLITE_PRODUCTS_PATH")
DEFAULT_PATHS = [
    Path(__file__).parent.parent / "data" / "productos.json",
    Path(__file__).parent.parent.parent / "productos.json",
]

DATA_PATH: Path | None = None
PRODUCTOS: Dict[str, dict] = {}

# -------------------------------------------------
# Utilidades de normalización
# -------------------------------------------------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")

def norm_txt(s: str) -> str:
    s = _strip_accents((s or "").lower())
    s = re.sub(r"[\s_]+", " ", s).strip()
    return s

def tok(s: str) -> List[str]:
    s = norm_txt(s)
    # separa 3000k / ip65 / 12v de forma robusta
    s = re.sub(r"([0-9]+)([a-z]+)", r"\1 \2", s)
    s = re.sub(r"([a-z]+)([0-9]+)", r"\1 \2", s)
    parts = re.split(r"[^a-z0-9]+", s)
    return [p for p in parts if p and len(p) >= 2]

def url_slug_tokens(url: str | None) -> List[str]:
    if not url:
        return []
    try:
        path = re.sub(r"^https?://[^/]+", "", url or "")
        segs = [seg for seg in path.split("/") if seg]
        toks: List[str] = []
        for seg in segs:
            toks.extend(tok(seg.replace("-", " ")))
        return toks
    except Exception:
        return []

# -------------------------------------------------
# Carga y cache del catálogo
# -------------------------------------------------
def _resolve_path() -> Path:
    global DATA_PATH
    if DATA_PATH:
        return DATA_PATH
    if ENV_PATH and Path(ENV_PATH).exists():
        DATA_PATH = Path(ENV_PATH)
        return DATA_PATH
    for p in DEFAULT_PATHS:
        if p.exists():
            DATA_PATH = p
            return DATA_PATH
    # último intento: junto al módulo (útil en dev)
    fallback = Path(__file__).parent / "productos.json"
    if fallback.exists():
        DATA_PATH = fallback
        return DATA_PATH
    raise FileNotFoundError(
        "No se encontró productos.json. Configure ECOLITE_PRODUCTS_PATH o "
        "coloque el archivo en backend/data/ o en la raíz del repo."
    )

def _postprocess_record(rec: dict) -> dict:
    """
    Enriquecemos cada producto con campos normalizados SIN imponer categorías estáticas.
    - name_norm / code_norm
    - categories_norm / tags_norm
    - slug_toks a partir de la URL (si existe)
    - search_blob con todo para indexado global
    """
    name = rec.get("name") or ""
    code = rec.get("code") or ""
    cats = rec.get("categories") or []
    tags = rec.get("tags") or []
    cat_url = rec.get("category") or ""

    name_norm = norm_txt(name)
    code_norm = norm_txt(code)
    cats_norm = [norm_txt(c) for c in cats if c]
    tags_norm = [norm_txt(t) for t in tags if t]
    slug_toks = url_slug_tokens(cat_url)

    blob_parts: List[str] = [name_norm, code_norm]
    if cats_norm:
        blob_parts.append(" ".join(cats_norm))
    if tags_norm:
        blob_parts.append(" ".join(tags_norm))
    if slug_toks:
        blob_parts.append(" ".join(slug_toks))

    rec["name_norm"] = name_norm
    rec["code_norm"] = code_norm
    rec["categories_norm"] = cats_norm
    rec["tags_norm"] = tags_norm
    rec["slug_toks"] = slug_toks
    rec["search_blob"] = " ".join([p for p in blob_parts if p]).strip()
    return rec

def _load_from_disk() -> Dict[str, dict]:
    path = _resolve_path()
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # admite tanto dict plano {CODE: {...}} como lista [{code:,...}]
    data: Dict[str, Any]
    if isinstance(raw, list):
        data = {str(it.get("code") or it.get("sku") or f"ITEM{i}"): it for i, it in enumerate(raw)}
    else:
        data = dict(raw)

    out: Dict[str, dict] = {}
    for code, rec in data.items():
        if not isinstance(rec, dict):
            continue
        rec = {**rec}
        rec.setdefault("code", code)
        out[code] = _postprocess_record(rec)

    if not out:
        raise RuntimeError("El catálogo cargó vacío.")
    return out

def load_products() -> Tuple[Dict[str, dict], Path]:
    """Devuelve (PRODUCTOS, DATA_PATH) usando la caché si existe."""
    global PRODUCTOS
    if not PRODUCTOS:
        PRODUCTOS = _load_from_disk()
    return PRODUCTOS, _resolve_path()

def reload_products() -> Tuple[Dict[str, dict], Path]:
    """Fuerza recarga desde disco y devuelve (PRODUCTOS, DATA_PATH)."""
    global PRODUCTOS
    PRODUCTOS = _load_from_disk()
    return PRODUCTOS, _resolve_path()
