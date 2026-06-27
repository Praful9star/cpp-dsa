"""
brain.py — The AI brain, powered by Groq (free tier).

Groq gives free access to Llama 3 with a generous daily limit.
Get your free key at: https://console.groq.com
"""

from groq import Groq
import config

SYSTEM_PROMPT = """You are a close friend of the user — smart, curious, warm, and a bit witty.
You talk like a real person, not a customer-service bot. Keep replies natural and concise
(spoken out loud, so don't write essays). Have opinions. Joke around when it fits.
Be genuinely helpful without being sycophantic.

The user is talking to you through a voice interface on their Android tablet, so:
- Keep responses short enough to be comfortable to listen to.
- Avoid bullet points, markdown, or numbered lists — speak in natural sentences.
- If you don't know something, say so honestly and offer to look it up."""

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


def chat(conversation_history: list[dict]) -> str:
    """Send conversation history to Groq/Llama and return the reply text."""
    client = _get_client()

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history,
            max_tokens=512,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[Brain error] {e}")
        # Give a natural spoken error instead of crashing
        msg = str(e).lower()
        if "auth" in msg or "key" in msg:
            return "My API key seems wrong — check GROQ_API_KEY in your .env file."
        if "connect" in msg or "network" in msg:
            return "I can't reach the internet right now. Check your connection?"
        if "rate" in msg:
            return "I'm being rate-limited. Give me a second and try again."
        return "Something went wrong on my end. Try again?"
