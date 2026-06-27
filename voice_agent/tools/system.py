"""
tools/system.py — Device control via Termux:API.

Supports:
  Battery      → "what's my battery"
  Volume       → "turn it up / down / set volume to 80"
  Flashlight   → "torch on / off"
  Clipboard    → "what's in my clipboard" / "copy this to clipboard: ..."
  Time & Date  → "what time is it" / "what's today's date"
  Wifi info    → "what's my IP"
  Joke         → "tell me a joke"
"""

import subprocess
import datetime
import json
import random
import requests


# ── Battery ───────────────────────────────────────────────────────────────────

def get_battery() -> str:
    try:
        result = subprocess.run(
            ["termux-battery-status"], capture_output=True, text=True, timeout=5
        )
        data    = json.loads(result.stdout)
        pct     = data.get("percentage", "?")
        status  = data.get("status", "").lower()
        health  = data.get("health", "").lower()
        plug    = data.get("plugged", "").lower()

        msg = f"Battery is at {pct}%"
        if "charging" in status or "ac" in plug or "usb" in plug:
            msg += ", currently charging"
        elif pct < 20:
            msg += " — getting low, plug it in soon"
        if health and health not in ("good", "unknown"):
            msg += f". Health: {health}"
        return msg + "."
    except Exception as e:
        return f"Couldn't read battery: {e}"


# ── Volume ────────────────────────────────────────────────────────────────────

def set_volume(direction: str, level: int | None = None) -> str:
    """
    direction: 'up', 'down', 'set', 'mute', 'max'
    level: 0-100 for 'set'
    """
    try:
        # Get current volume first
        result = subprocess.run(
            ["termux-volume"], capture_output=True, text=True, timeout=5
        )
        volumes = json.loads(result.stdout)
        # Find media volume
        media = next((v for v in volumes if v.get("stream") == "music"), None)
        current = media["volume"] if media else 5
        max_vol = media["maxVolume"] if media else 15

        if direction == "set" and level is not None:
            # Convert percentage to device scale
            new_vol = int(level / 100 * max_vol)
        elif direction == "up":
            new_vol = min(current + 2, max_vol)
        elif direction == "down":
            new_vol = max(current - 2, 0)
        elif direction == "mute":
            new_vol = 0
        elif direction == "max":
            new_vol = max_vol
        else:
            new_vol = current

        subprocess.run(
            ["termux-volume", "music", str(new_vol)],
            capture_output=True, timeout=5
        )
        pct = int(new_vol / max_vol * 100)
        return f"Volume set to {pct}%."
    except Exception as e:
        return f"Volume control failed: {e}"


# ── Flashlight / Torch ────────────────────────────────────────────────────────

def torch(on: bool) -> str:
    try:
        state = "on" if on else "off"
        subprocess.run(
            ["termux-torch", state],
            capture_output=True, timeout=5
        )
        return f"Torch {'on' if on else 'off'}."
    except FileNotFoundError:
        return "Torch not available — make sure Termux:API is installed."
    except Exception as e:
        return f"Torch error: {e}"


# ── Clipboard ─────────────────────────────────────────────────────────────────

def get_clipboard() -> str:
    try:
        result = subprocess.run(
            ["termux-clipboard-get"], capture_output=True, text=True, timeout=5
        )
        text = result.stdout.strip()
        if not text:
            return "Your clipboard is empty."
        short = text[:200] + ("..." if len(text) > 200 else "")
        return f"Clipboard says: {short}"
    except Exception as e:
        return f"Couldn't read clipboard: {e}"


def set_clipboard(text: str) -> str:
    try:
        subprocess.run(
            ["termux-clipboard-set", text],
            capture_output=True, timeout=5
        )
        return f"Copied to clipboard: \"{text[:80]}\""
    except Exception as e:
        return f"Couldn't set clipboard: {e}"


# ── Time & Date ───────────────────────────────────────────────────────────────

def get_time() -> str:
    now = datetime.datetime.now()
    return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %d %B %Y')}."


# ── Network / IP ──────────────────────────────────────────────────────────────

def get_ip() -> str:
    try:
        resp = requests.get("https://api.ipify.org?format=json", timeout=5)
        ip   = resp.json()["ip"]
        return f"Your public IP is {ip}."
    except Exception:
        return "Couldn't fetch IP — check your connection."


# ── Jokes ─────────────────────────────────────────────────────────────────────

def tell_joke() -> str:
    try:
        resp = requests.get(
            "https://official-joke-api.appspot.com/random_joke",
            timeout=8,
        )
        data = resp.json()
        return f"{data['setup']} ... {data['punchline']}"
    except Exception:
        # Fallback offline jokes
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "A SQL query walks into a bar, walks up to two tables and asks... can I join you?",
            "Why did the developer go broke? Because he used up all his cache.",
            "There are only 10 kinds of people in the world — those who understand binary and those who don't.",
            "Why do Java developers wear glasses? Because they don't C sharp.",
            "How many programmers does it take to change a light bulb? None — that's a hardware problem.",
            "I told my wife she was drawing her eyebrows too high. She looked surprised.",
            "Why can't you trust an atom? Because they make up everything.",
        ]
        return random.choice(jokes)
