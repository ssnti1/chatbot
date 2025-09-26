# backend/services/openai_client.py
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def ask_chatgpt(system_prompt: str, user_message: str | None = None) -> str:
    """
    Stub seguro: si no hay API key, devuelve un texto corto
    para no romper el servidor.
    """
    if not OPENAI_API_KEY:
        return "Aquí tienes algunas opciones recomendadas:"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        msgs = [{"role": "system", "content": system_prompt}]
        if user_message:
            msgs.append({"role": "user", "content": user_message})
        resp = client.chat.completions.create(model=OPENAI_MODEL, messages=msgs, temperature=0.3)
        return resp.choices[0].message.content
    except Exception:
        return "Aquí tienes algunas opciones recomendadas:"


