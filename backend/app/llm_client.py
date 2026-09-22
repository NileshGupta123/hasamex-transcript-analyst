import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_client = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY missing hai. backend\\.env check karo.")
        _client = Groq(api_key=api_key)
    return _client


def get_model() -> str:
    return os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def call_json(system_prompt: str, user_prompt: str, max_retries: int = 1) -> dict:
    """LLM ko call karta hai aur strict JSON object return karwata hai.
    Invalid JSON aaye toh ek dobara try karta hai."""
    client = get_client()
    model = get_model()
    last_error = None

    for attempt in range(max_retries + 1):
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

    raise ValueError(f"LLM ne {max_retries + 1} attempts me bhi valid JSON nahi diya: {last_error}")