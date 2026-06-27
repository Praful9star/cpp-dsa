"""
brain.py — Groq API with tool/function calling (Phase 3).

The LLM decides on its own when to:
  - web_search    → look something up
  - send_telegram → send a message
  - play_youtube  → play music or a YouTube video
  - stop_media    → stop playing audio
"""

import json
import requests
import config
from tools.web_search    import web_search
from tools.telegram_send import send_telegram
from tools.play_media    import play_youtube, stop_media

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

BASE_SYSTEM_PROMPT = """You are a close friend of Praful — smart, curious, warm, and witty.
Talk like a real person. Keep replies short and natural (this is spoken out loud).
No bullet points, no markdown — just normal sentences.
Use his name occasionally but not every reply.
If you don't know something current, use the web_search tool.{facts}"""

# ── Tool definitions (OpenAI function-calling format, supported by Groq) ──────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current information, news, facts, or anything "
                "you don't know. Use this whenever Praful asks something that requires "
                "up-to-date or specific knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_telegram",
            "description": (
                "Send a Telegram message on Praful's behalf. "
                "Use when he says things like 'tell X...', 'message X saying...', "
                "'send X a message that...'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Name of the person to message (e.g. 'mom', 'Rahul').",
                    },
                    "message": {
                        "type": "string",
                        "description": "The message text to send.",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube",
            "description": (
                "Play music or a YouTube video by search query or URL. "
                "Use when Praful says 'play [song/artist/genre]', "
                "'put on some music', 'play a YouTube video of ...', etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Song name, artist, genre, or YouTube URL to play.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_media",
            "description": "Stop whatever music or audio is currently playing.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ── Tool dispatcher ────────────────────────────────────────────────────────────

def _run_tool(name: str, args: dict) -> str:
    """Execute a tool by name and return its string result."""
    print(f"[Tool] {name}({args})")
    if name == "web_search":
        return web_search(args.get("query", ""))
    if name == "send_telegram":
        return send_telegram(args.get("message", ""), args.get("recipient", ""))
    if name == "play_youtube":
        return play_youtube(args.get("query", ""))
    if name == "stop_media":
        return stop_media()
    return f"Unknown tool: {name}"


# ── Main chat function ─────────────────────────────────────────────────────────

def chat(conversation_history: list, facts_context: str = "") -> str:
    """
    Send conversation to Groq. If the model wants to call a tool,
    run it and send the result back for a final spoken reply.
    Returns the final reply text.
    """
    system = BASE_SYSTEM_PROMPT.format(facts=facts_context)
    messages = [{"role": "system", "content": system}] + conversation_history

    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # ── First call: may return tool_calls ─────────────────────────────────────
    payload = {
        "model": config.GROQ_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": 1024,
        "temperature": 0.8,
    }

    try:
        resp = _post(headers, payload)
        choice = resp["choices"][0]

        # ── No tool needed — plain reply ──────────────────────────────────────
        if choice["finish_reason"] != "tool_calls":
            return choice["message"]["content"].strip()

        # ── Tool call(s) requested ────────────────────────────────────────────
        assistant_msg = choice["message"]
        messages.append(assistant_msg)  # add assistant's tool-call message

        for tool_call in assistant_msg.get("tool_calls", []):
            fn_name = tool_call["function"]["name"]
            fn_args = json.loads(tool_call["function"]["arguments"])
            result  = _run_tool(fn_name, fn_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })

        # ── Second call: get the final spoken reply ───────────────────────────
        payload2 = {
            "model": config.GROQ_MODEL,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.8,
        }
        resp2 = _post(headers, payload2)
        return resp2["choices"][0]["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        return "I can't reach the internet right now. Check your connection?"
    except requests.exceptions.Timeout:
        return "That took too long. Try again?"
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        if code == 401:
            return "My API key seems wrong — check GROQ_API_KEY in your .env file."
        if code == 429:
            return "I'm being rate-limited. Give me a second and try again."
        return f"API error {code}. Try again?"
    except Exception as e:
        print(f"[Brain error] {e}")
        return "Something went wrong on my end. Try again?"


def _post(headers: dict, payload: dict) -> dict:
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
