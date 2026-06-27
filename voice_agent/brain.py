"""
brain.py — The Claude API wrapper (the "brain" of the agent).

Sends a conversation history to Claude and returns the assistant's reply text.
In Phase 1 this is pure conversation — no tools yet (those come in Phase 3).
"""

import anthropic
import config

# System prompt: gives the agent its personality.
# Warm, casual, like a smart friend — NOT a corporate assistant.
SYSTEM_PROMPT = """You are a close friend of the user — smart, curious, warm, and a bit witty.
You talk like a real person, not a customer-service bot. Keep replies natural and concise
(spoken out loud, so don't write essays). Use first names if you know them. Have opinions.
Joke around when it fits. Be genuinely helpful without being sycophantic.

The user is talking to you through a voice interface on their Android tablet, so:
- Keep responses short enough to be comfortable to listen to.
- Avoid bullet points, markdown, or numbered lists — speak in natural sentences.
- If you don't know something, say so honestly and offer to look it up.

You have a continuous memory of past chats (managed externally), so you can refer back
to things the user told you before."""

# Module-level Anthropic client — created once, reused across turns
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def chat(conversation_history: list[dict]) -> str:
    """
    Send the full conversation history to Claude and return the reply text.

    conversation_history is a list of dicts:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]

    The most recent message should be role="user".
    Returns the assistant's reply as a plain string.
    """
    client = _get_client()

    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation_history,
        )
        # response.content is a list of content blocks; grab the first text block
        for block in response.content:
            if block.type == "text":
                return block.text.strip()

        return "Hmm, I got a response but couldn't read it. Try again?"

    except anthropic.AuthenticationError:
        return "My API key seems wrong — can you check the ANTHROPIC_API_KEY in your .env file?"

    except anthropic.RateLimitError:
        return "I'm being rate-limited right now. Give me a second and try again."

    except anthropic.APIConnectionError:
        return "I can't reach the internet right now. Check your connection?"

    except Exception as e:
        # Don't crash the loop — report the error and keep going
        print(f"[Brain error] {e}")
        return f"Something went wrong on my end: {e}"
