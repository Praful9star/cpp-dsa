"""
tools/fun.py — Roast, story, rap battle, debate, quote, speedtest.

These all return special markers that brain.py handles by calling Groq
with a specific creative prompt.
"""
import requests
import subprocess
import re
import random


# Markers for brain.py to detect and handle with Groq
def roast_me()   -> str: return "FUN:ROAST"
def tell_story() -> str: return "FUN:STORY"
def rap_battle() -> str: return "FUN:RAP"

def start_debate(topic: str) -> str:
    return f"FUN:DEBATE:{topic}"

def get_quote() -> str:
    """Fetch a random quote from quotable.io (free API)."""
    try:
        resp = requests.get("https://api.quotable.io/random?maxLength=150", timeout=8)
        data = resp.json()
        return f"{data['content']} — {data['author']}"
    except Exception:
        quotes = [
            "The secret of getting ahead is getting started. — Mark Twain",
            "It always seems impossible until it's done. — Nelson Mandela",
            "Don't watch the clock; do what it does. Keep going. — Sam Levenson",
            "You don't have to be great to start, but you have to start to be great.",
            "The harder you work, the luckier you get.",
            "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        ]
        import random
        return random.choice(quotes)


def internet_speed() -> str:
    """Quick internet speed check using curl to a known endpoint."""
    try:
        result = subprocess.run(
            ["curl", "-o", "/dev/null", "-s", "-w", "%{speed_download}",
             "--max-time", "8",
             "https://speed.cloudflare.com/__down?bytes=1000000"],
            capture_output=True, text=True, timeout=15,
        )
        speed_bytes = float(result.stdout.strip())
        speed_mbps  = speed_bytes * 8 / 1_000_000
        if speed_mbps < 1:
            quality = "quite slow"
        elif speed_mbps < 10:
            quality = "decent"
        elif speed_mbps < 50:
            quality = "good"
        else:
            quality = "fast"
        return f"Your download speed is about {speed_mbps:.1f} Mbps — {quality}."
    except Exception as e:
        return f"Couldn't run speed test: {e}"


def days_until(event: str) -> str:
    """Calculate days until a named or described future event."""
    import datetime, re
    t = event.lower()

    # Built-in known events for Praful
    targets = {
        "chandigarh university": datetime.date(2025, 7, 1),
        "cu":                    datetime.date(2025, 7, 1),
        "college":               datetime.date(2025, 7, 1),
        "new year":              datetime.date(datetime.date.today().year + 1, 1, 1),
        "christmas":             datetime.date(datetime.date.today().year, 12, 25),
        "diwali":                datetime.date(2025, 10, 20),
        "holi":                  datetime.date(2026, 3, 2),
    }

    today = datetime.date.today()
    for name, target_date in targets.items():
        if name in t:
            delta = (target_date - today).days
            if delta < 0:
                return f"{name.title()} was {abs(delta)} days ago."
            if delta == 0:
                return f"Today is {name.title()}! Let's go!"
            return f"{name.title()} is in {delta} days!"

    # Try to parse a date from text like "15 august" or "december 25"
    months = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
              "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
    for month_name, month_num in months.items():
        if month_name in t:
            m = re.search(r"(\d{1,2})", t)
            day = int(m.group(1)) if m else 1
            year = today.year
            target = datetime.date(year, month_num, day)
            if target < today:
                target = datetime.date(year + 1, month_num, day)
            delta = (target - today).days
            return f"That date is in {delta} days."

    return f"I couldn't figure out the date for '{event}'. Try saying 'how many days until July 15'."
