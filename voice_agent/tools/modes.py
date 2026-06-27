"""
tools/modes.py — Agent personality modes.

focus  → short replies only, no jokes, no filler
chill  → casual, fun, relaxed
study  → DSA/C++ mode, prioritizes learning, explains concepts
normal → default balanced mode

"Focus mode" / "I'm studying" / "Chill mode" / "Study mode"
"""

_current_mode = "normal"

MODE_PROMPTS = {
    "normal": "",
    "focus": (
        "\n\nCURRENT MODE: FOCUS. Keep all replies extremely short — one sentence max. "
        "No jokes, no filler, no small talk. Be a tool, not a friend right now."
    ),
    "chill": (
        "\n\nCURRENT MODE: CHILL. Praful is relaxing. Be extra casual, funny, use slang if it fits. "
        "This is hangout time, not work time."
    ),
    "study": (
        "\n\nCURRENT MODE: STUDY. Praful is studying C++ and DSA. Prioritize explaining concepts clearly "
        "and simply. Use analogies. When he asks anything technical, give the clearest beginner-friendly "
        "explanation. Encourage him — he's building solid foundations."
    ),
}


def set_mode(mode: str) -> str:
    global _current_mode
    mode = mode.lower().strip()

    if "focus" in mode:
        _current_mode = "focus"
        return "Focus mode on. I'll keep it short and sharp."
    elif "chill" in mode or "relax" in mode or "casual" in mode:
        _current_mode = "chill"
        return "Chill mode activated. Let's vibe."
    elif "study" in mode or "learning" in mode or "dsa" in mode:
        _current_mode = "study"
        return "Study mode on. Let's get those concepts locked in, Praful."
    elif "normal" in mode or "default" in mode or "off" in mode:
        _current_mode = "normal"
        return "Back to normal mode."
    else:
        return f"I don't know that mode. Try: focus, chill, study, or normal."


def get_mode() -> str:
    return _current_mode


def get_mode_prompt() -> str:
    return MODE_PROMPTS.get(_current_mode, "")


def current_mode_status() -> str:
    return f"Current mode: {_current_mode}."
