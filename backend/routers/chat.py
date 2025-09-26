# backend/routers/chat.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import hashlib

from backend.services.search_service import search_candidates
from backend.services.context_builder import build_context
from backend.services.openai_client import ask_chatgpt
from backend.services.state_manager import maybe_extract_slots  # solo reusa los extractores (no estado)

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatIn(BaseModel):
    session_id: str
    message: str
    page: Optional[int] = 0
    last_query: Optional[str] = None

def _stable_seed(session_id: str, q: str) -> int:
    h = hashlib.md5((session_id + "|" + (q or "")).encode("utf-8")).hexdigest()
    return int(h[:8], 16)

def _as_bot_message(text: str, products: List[Dict], page: int, last_query: str) -> Dict:
    return {"content": text, "products": products, "page": page, "last_query": last_query}

@router.post("/")
def chat(in_: ChatIn):
    msg = (in_.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is required")

    # Stateless: el cliente controla paginación
    page = max(0, int(in_.page or 0))
    effective_query = in_.last_query if page > 0 and in_.last_query else msg

    # Estado efímero para el motor de ranking (no persiste)
    state = {
        "page": page,
        "result_seed": _stable_seed(in_.session_id, effective_query),
        "preferencias": (maybe_extract_slots(effective_query).get("preferencias") or {}),
        "last_user_msg": effective_query
    }

    limit = 5
    offset = page * limit

    cand = search_candidates(effective_query, state, limit=limit, offset=offset, exclude_codes=[])

    # Redacción breve de respuesta + listado (si hay productos)
    system_prompt = build_context(state, cand)
    reply = ask_chatgpt(system_prompt)

    return _as_bot_message(reply, cand, page, effective_query)
