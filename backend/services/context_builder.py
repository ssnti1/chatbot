# backend/services/context_builder.py
import json

BASE_RULES = """
Eres el asistente de Ecolite (Colombia). Sé claro, breve y profesional con tono cercano.
Usa emojis con moderación (💡👌✨). Ayuda a elegir el producto correcto.

REGLAS:
- SOLO puedes recomendar productos de la sección CANDIDATOS_PROD que te pasa el sistema.
- No inventes productos.
- Muestra máximo 5 productos.
- Si faltan datos (espacio, instalación, vatios, temperatura, presupuesto), haz 1 pregunta concreta.
- Formato ESTRICTO de cada producto (una línea por ítem, sin markdown, sin viñetas):
  Nombre — Precio — URL — IMG_URL
"""

def build_context(state: dict, candidates: list[dict]) -> str:
    state_snapshot = {
        "espacio": state.get("espacio"),
        "necesidad": state.get("necesidad"),
        "preferencias": state.get("preferencias"),
    }
    return f"""
{BASE_RULES}

ESTADO:
{json.dumps(state_snapshot, ensure_ascii=False)}

CANDIDATOS_PROD (elige SOLO de esta lista):
{json.dumps(candidates, ensure_ascii=False)}

Redacta una respuesta corta (1–2 frases) y luego lista los productos en el formato indicado.
"""
