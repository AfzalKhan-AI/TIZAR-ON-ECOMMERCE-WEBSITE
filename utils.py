import os
import requests
from config import Config

def hash_password(pw):
    # utility wrapper if you want custom hashing; not used (models use werkzeug)
    from werkzeug.security import generate_password_hash
    return generate_password_hash(pw)

def verify_password(hash, pw):
    from werkzeug.security import check_password_hash
    return check_password_hash(hash, pw)

def ai_chat(prompt: str) -> str:
    """
    Simple proxy to an LLM. By default tries OpenAI-compatible API.
    Replace with Gemini API calls if needed. Use env keys in Config.
    """
    key = Config.OPENAI_API_KEY
    if not key:
        return "AI not configured. Set OPENAI_API_KEY in .env."

    # Example: Use OpenAI chat completions (HTTP) or any compatible API.
    # NOTE: This is a minimal example using OpenAI's REST; if you use Gemini,
    # change endpoint and payload accordingly.
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",  # change to whichever model you have access to
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.3
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # openai response path:
        msg = data["choices"][0]["message"]["content"]
        return msg
    except Exception as e:
        return f"AI call failed: {str(e)}"
