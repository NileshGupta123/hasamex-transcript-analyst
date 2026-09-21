import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

if not api_key:
    raise SystemExit("GROQ_API_KEY missing hai. backend\\.env me apni key daalo.")

client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model=model,
    temperature=0,
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": "You reply only with valid JSON."},
        {"role": "user", "content": 'Return this JSON: {"status": "ok", "message": "hello"}'},
    ],
)

content = response.choices[0].message.content
print("Model:", model)
print("Raw reply:", content)
print("Parsed JSON:", json.loads(content))