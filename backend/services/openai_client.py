import os
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("Falta OPENAI_API_KEY (configura .env)")

_client = OpenAI(api_key=OPENAI_API_KEY)

def ask_chatgpt(system_prompt: str, user_message: str) -> str:
    resp = _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content
