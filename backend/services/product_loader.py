# backend/services/product_loader.py
from __future__ import annotations
import json
import unicodedata
import re
from pathlib import Path
from typing import Dict, Tuple, Any, List


# Ruta fija (sin ENV): coloca tu productos.json aquí
DATA_PATH = Path(__file__).parent.parent / "data" / "productos.json"

# Caché (carga perezosa). Debe ser: dict[str, dict] para compatibilidad con search_service.
PRODUCTOS: Dict[str, dict] = {}



# -----------------------------
# Utilidades
# -----------------------------
def _require_dict(d: Any, msg: str) -> dict:
    if not isinstance(d, dict):
        raise RuntimeError(msg)
    return d

def _norm(s: str) -> str:
    """Normaliza texto: minúsculas, sin tildes, espacios colapsados."""
    s = "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _normalize_product(code: str, rec: dict) -> dict:
    """
    Garantiza que cada producto tenga los campos mínimos y tipos esperados por search_service.
    """
    code_up = (code or "").strip().upper()
    if not code_up:
        raise RuntimeError("Producto con clave vacía")

    name = (rec.get("name") or rec.get("title") or code_up)
    price = (rec.get("price") or rec.get("precio") or "").strip()
    url = (rec.get("url") or "").strip()
    img_url = (rec.get("img_url") or rec.get("image") or "").strip()

    def _to_list(v):
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return [str(v).strip()]

    categories: List[str] = _to_list(rec.get("categories") or rec.get("category"))
    tags: List[str] = _to_list(rec.get("tags"))

    # Normalización de categorías originales
    categories_norm: List[str] = [_norm(c) for c in categories if c]

    semantic_rules = {
        "piscina": ["jacuzzi", "acuática", "acuaticas", "sumergible"],
        "decorativa": ["cuarto", "habitacion", "habitación", "alcoba", "pieza",
                       "dormitorio", "sala", "comedor", "living"],
        "interior": ["oficina", "consultorio", "estudio", "recepcion", "recepción"],
        "industrial": ["bodega", "taller", "fabrica", "fábrica",
                       "planta", "nave", "galpon", "galpón"],
    }

    extra_norms: List[str] = []
    for base, synonyms in semantic_rules.items():
        if any(base in c for c in categories_norm):
            extra_norms.extend(synonyms)

    categories_norm = list(set(categories_norm + [_norm(e) for e in extra_norms]))

    return {
        "code": code_up,
        "name": str(name).strip(),
        "price": str(price),
        "url": url,
        "img_url": img_url,
        "categories": categories,
        "categories_norm": categories_norm,
        "tags": tags,
        "category": rec.get("category") if isinstance(rec.get("category"), str) else None,
    }

# -----------------------------
# Carga desde disco (perezosa)
# -----------------------------
def _load_from_disk() -> Dict[str, dict]:
    if not DATA_PATH.exists():
        raise RuntimeError(
            "No se encontró el catálogo de productos.\n"
            f"Coloca el archivo en: {DATA_PATH}\n"
            "Sugerencia: crea la carpeta backend/data y copia allí tu productos.json"
        )
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    data = _require_dict(raw, "productos.json debe ser un objeto {code: {...}}")

    out: Dict[str, dict] = {}
    for code, rec in data.items():
        if not isinstance(rec, dict):
            continue
        try:
            normalized = _normalize_product(code, rec)
        except Exception:
            continue
        out[normalized["code"]] = normalized

    if not out:
        raise RuntimeError("productos.json cargó vacío o inválido")

    return out

def load_products() -> Tuple[Dict[str, dict], Path]:
    """Carga (o devuelve caché) y retorna (PRODUCTOS, DATA_PATH)."""
    global PRODUCTOS
    if not PRODUCTOS:
        PRODUCTOS = _load_from_disk()
    return PRODUCTOS, DATA_PATH

def reload_products() -> Tuple[Dict[str, dict], Path]:
    """Fuerza recarga desde disco."""
    global PRODUCTOS
    PRODUCTOS = _load_from_disk()
    return PRODUCTOS, DATA_PATH



for p in PRODUCTOS.values():
    raw_cats = p.get("categories", [])
    p["categories_norm"] = [_norm(c) for c in raw_cats if c]
