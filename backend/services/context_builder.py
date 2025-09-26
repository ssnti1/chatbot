# backend/services/context_builder.py
import json

BASE_RULES = """
Eres el asistente de Ecolite (Colombia). Sé claro, breve y profesional con tono cercano.
Usa emojis con moderación (💡👌✨). Ayuda a elegir el producto correcto.

REGLAS:
- SOLO puedes recomendar productos de la sección CANDIDATOS_PROD que te pasa el sistema.
- No inventes productos.
- Si faltan datos (espacio, instalación, vatios, temperatura, presupuesto), haz 1 pregunta concreta.
"""

def build_context(state: dict, candidates: list[dict]) -> str:
    state_snapshot = {
        "ultima_consulta": state.get("last_user_msg"),
        "preferencias": state.get("preferencias"),
        "page": state.get("page"),
    }
    return f"""
{BASE_RULES}

ESTADO:
{json.dumps(state_snapshot, ensure_ascii=False, indent=2)}

CANDIDATOS_PROD (elige SOLO de esta lista):
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Redacta una respuesta corta (1–2 frases). Si no hay productos, pide un dato faltante.
"""
