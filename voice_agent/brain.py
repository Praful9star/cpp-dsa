"""
brain.py — Calls Groq API directly via requests (no Rust/pydantic needed).
Works on Android/Termux without build issues.
"""

import requests
import config

SYSTEM_PROMPT = """You are a close friend of the user — smart, curious, warm, and a bit witty.
You talk like a real person, not a customer-service bot. Keep replies natural and concise
(spoken out loud, so don't write essays). Have opinions. Joke around when it fits.
Be genuinely helpful without being sycophantic.

The user is talking to you through a voice interface on their Android tablet, so:
- Keep responses short enough to be comfortable to listen to.
- Avoid bullet points, markdown, or numbered lists — speak in natural sentences.
- If you don't know something, say so honestly."""

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def chat(conversation_history: list) -> str:
    """Send conversation history to Groq and return the reply text."""
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history,
        "max_tokens": 512,
        "temperature": 0.8,
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        return "I can't reach the internet right now. Check your connection?"
    except requests.exceptions.Timeout:
        return "That took too long. Try again?"
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            return "My API key seems wrong — check GROQ_API_KEY in your .env file."
        if response.status_code == 429:
            return "I'm being rate-limited. Give me a second and try again."
        return f"API error {response.status_code}. Try again?"
    except Exception as e:
        print(f"[Brain error] {e}")
        return "Something went wrong on my end. Try again?"
