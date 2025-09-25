from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.state_manager import (
    get_state, update_state, maybe_extract_slots,
    classify_intent, is_keyword_signal, Intent
)
from backend.services.search_service import search_candidates, _detect_categories_from_text, is_offtopic
from backend.services.context_builder import build_context
from backend.services.openai_client import ask_chatgpt
from backend.routers import faq
import random
import re as _re 


_TALK_RE = _re.compile(r"^\s*(hablemos|hablamos|quiero\s+que\s+hablemos|quiero\s+hablar)\s+de\b", _re.I)

def _is_talk_request(text: str) -> bool:
    return bool(_TALK_RE.search(text or ""))

def _talk_small_reply() -> str:
    return (
        "¡Perfecto! Hablemos de iluminación 💡. "
        "Para guiarte mejor, dime: ¿qué espacio quieres iluminar (ej.: oficina, piscina, bodega, exterior) "
        "o el tipo de luz (ej.: reflector 200W IP65, panel 60x60, tira 24V)?"
    )

def _is_catalog_request(text: str) -> bool:
    t = (text or "").lower()
    return (
        "catalogo" in t or "catálogo" in t or
        _re.search(r'\b(ver|muestrame|mu[ée]strame|ense[ñn]ame)\s+el\s+cat[aá]logo\b', t) is not None
    )

def _catalog_link_reply() -> str:
    import os as _os
    url = _os.getenv("ECOLITE_CATALOGO_URL", "https://ecolite.com.co/catalogo")
    return f"Aquí puedes ver nuestro catálogo: {url}"


_MORE_PAT = _re.compile(
    r"\b("
    r"mas|más|"
    r"otras?|siguientes?|siguiente|"
    r"ver\s+mas|ver\s+más|"
    r"mu[eé]strame\s+otras?"
    r")\b",
    flags=_re.IGNORECASE
)

def is_more_signal(msg: str) -> bool:
    return bool(_MORE_PAT.search(msg or ""))

router = APIRouter(prefix="/chat", tags=["chat"])

PER_PAGE = 5

class ChatIn(BaseModel):
    message: str
    session_id: str = "default"

GREETING_PROMPT = (
    "Saluda breve en tono serio/amistoso; pregunta qué espacio desea iluminar "
    "(oficina, piscina, bodega…)."
)

SMALLTALK_PROMPT = (
    "Responde breve y ofrece ayuda. Pide 1–2 datos clave: espacio (oficina/piscina/bodega), "
    "tipo (decorativa/riel/industrial) o presupuesto."
)


def _fetch_and_reply(user_msg: str, state: dict, session_id: str) -> dict:
    """
    Trae productos con offset/limit, marca vistos y arma la respuesta.
    Devuelve también 'items' para que el front pinte cards.
    """
    seen = state.get("seen_codes", set())
    page = state.get("page", 0)

    offset = 0 if seen else page * PER_PAGE

    items = search_candidates(
        user_msg,
        state,
        limit=PER_PAGE,
        offset=offset,
        exclude_codes=seen
    )

    if not items:
        state["result_seed"] = random.getrandbits(32)
        items = search_candidates(
            user_msg,
            state,
            limit=PER_PAGE,
            offset=offset,
            exclude_codes=seen
        )

    if not items:
        reply = "No encontré productos para esa búsqueda. ¿Quieres que te sugiera otra categoría o revisar el catálogo completo?"
        update_state(session_id, {"role": "assistant", "content": reply})
        return {"reply": reply, "items": []}

    for it in items:
        state.setdefault("seen_codes", set()).add(it["code"])

    contexto = build_context(user_msg, state, items)
    reply = ask_chatgpt(contexto, "Redacta breve y lista solo estos productos.")
    update_state(session_id, {"role": "assistant", "content": reply})

    return {"reply": reply, "items": items}


@router.post("/")
def chat(in_: ChatIn):
    user_msg = (in_.message or "").strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="message is required")

    state = get_state(in_.session_id)
    update_state(in_.session_id, {"role": "user", "content": user_msg})
    state["last_user_msg"] = user_msg

    if _is_catalog_request(user_msg):
        reply = _catalog_link_reply()
        state["last_intent"] = "catalog"
        update_state(in_.session_id, {"role": "assistant", "content": reply})
        return {"reply": reply, "items": []}

    if _is_talk_request(user_msg):
        state["last_intent"] = "faq_or_smalltalk"
        state["last_query"] = None
        state["page"] = 0
        reply = _talk_small_reply()
        update_state(in_.session_id, {"role": "assistant", "content": reply})
        return {"reply": reply, "items": []}

    if is_more_signal(user_msg):
        if is_keyword_signal(user_msg):  
            state["page"] = 0
            state["last_query"] = user_msg
            state["result_seed"] = random.getrandbits(32)
            return _fetch_and_reply(user_msg, state, in_.session_id)

        if state.get("last_query"):
            state["page"] = state.get("page", 0) + 1
            return _fetch_and_reply(state["last_query"], state, in_.session_id)
        else:
            reply = "Aún no tengo una lista para ‘mostrar más’. Dime qué buscas (p. ej., ‘lámparas decorativas’, ‘reflector 100W IP65’)."
            update_state(in_.session_id, {"role": "assistant", "content": reply})
            return {"reply": reply, "items": []}

    maybe_extract_slots(state, user_msg)

    early_intent: Intent = classify_intent(user_msg)
    if early_intent == "greeting":
        if is_keyword_signal(user_msg) or state.get("espacio_source") in {"alias", "direct"}:
            intent = "product_search"
        else:
            state["last_intent"] = None
            reply = ask_chatgpt(f"SOS SISTEMA: {GREETING_PROMPT}", user_msg)
            update_state(in_.session_id, {"role": "assistant", "content": reply})
            return {"reply": reply}
    else:
        intent = early_intent

    try:
        if intent == "product_search" and is_offtopic(user_msg):
            intent = "faq_or_smalltalk"
    except Exception:
        pass

    try:
        if intent != "product_search" and is_offtopic(user_msg):
            reply = (
                "No tengo información sobre ese tema. "
                "Puedo ayudarte con iluminación y productos Ecolite 💡. "
                "Por ejemplo: ‘lámparas decorativas’, ‘paneles solares’."
            )
            update_state(in_.session_id, {"role": "assistant", "content": reply})
            return {"reply": reply, "items": []}
    except Exception:
        pass

    if intent == "faq_or_smalltalk":
        low = user_msg.lower()
        if any(w in low for w in ("sugiere", "sugiéreme", "sugiereme", "recomiéndame", "recomiendame", "recomienda")) and state.get("espacio"):
            intent = "product_search"
            user_msg = state["espacio"]

    if intent == "greeting":
        state["last_intent"] = None
        reply = ask_chatgpt(f"SOS SISTEMA: {GREETING_PROMPT}", user_msg)
        update_state(in_.session_id, {"role": "assistant", "content": reply})
        return {"reply": reply}

    faq_reply = faq.try_answer(user_msg)
    if faq_reply:
        state["last_intent"] = "faq"
        update_state(in_.session_id, {"role": "assistant", "content": faq_reply})
        return {"reply": faq_reply}

    if intent == "product_search":
        state["last_intent"] = None
        try:
            from backend.services.state_manager import _detect_focuses_from_text
            detected = _detect_focuses_from_text(user_msg)
            if detected:
                state["focus"] = set(detected)
        except Exception:
            pass

        q = user_msg
        if not is_keyword_signal(user_msg) and state.get("espacio"):
            q = state["espacio"]

        state["page"] = 0
        state["last_query"] = q
        state["result_seed"] = random.getrandbits(32)
        return _fetch_and_reply(q, state, in_.session_id)

    reply = "¿Quieres que te sugiera algo del catálogo o prefieres resolver otra duda (ej.: garantía, cambios, envíos)?"
    update_state(in_.session_id, {"role": "assistant", "content": reply})
    return {"reply": reply}
