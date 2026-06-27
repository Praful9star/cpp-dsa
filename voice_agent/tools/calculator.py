"""
tools/calculator.py — Math, unit conversions, and percentages.

"What is 15 percent of 3500"
"Convert 5 km to miles"
"What's 234 times 17"
"Square root of 144"
"""

import re
import math


def calculate(text: str) -> str:
    """Try to evaluate a math or conversion expression from natural language."""

    t = text.lower().strip()

    # ── Unit conversions ──────────────────────────────────────────────────────
    conv = _try_conversion(t)
    if conv:
        return conv

    # ── Percentage ────────────────────────────────────────────────────────────
    pct = _try_percentage(t)
    if pct:
        return pct

    # ── Square root ───────────────────────────────────────────────────────────
    m = re.search(r"sqrt|square root of\s+([\d.]+)", t)
    if m:
        try:
            n = float(m.group(1))
            return f"Square root of {n} is {math.sqrt(n):.4g}"
        except Exception:
            pass

    # ── Power ─────────────────────────────────────────────────────────────────
    m = re.search(r"([\d.]+)\s*(?:to the power of|power|raised to|\^)\s*([\d.]+)", t)
    if m:
        try:
            result = float(m.group(1)) ** float(m.group(2))
            return f"{m.group(1)} to the power of {m.group(2)} is {result:.6g}"
        except Exception:
            pass

    # ── General math expression ───────────────────────────────────────────────
    expr = _to_math_expr(t)
    if expr:
        try:
            # Safe eval — only math operations
            allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
            result = eval(expr, {"__builtins__": {}}, allowed)  # noqa: S307
            return f"That's {result:.6g}"
        except Exception:
            pass

    return "I couldn't work that out. Try rephrasing — like 'what is 23 times 4'."


# ── Conversions ───────────────────────────────────────────────────────────────

CONVERSIONS = {
    # distance
    ("km", "miles"):      lambda x: x * 0.621371,
    ("miles", "km"):      lambda x: x * 1.60934,
    ("meters", "feet"):   lambda x: x * 3.28084,
    ("feet", "meters"):   lambda x: x / 3.28084,
    ("cm", "inches"):     lambda x: x / 2.54,
    ("inches", "cm"):     lambda x: x * 2.54,
    # weight
    ("kg", "pounds"):     lambda x: x * 2.20462,
    ("pounds", "kg"):     lambda x: x / 2.20462,
    ("grams", "ounces"):  lambda x: x / 28.3495,
    # temperature
    ("celsius", "fahrenheit"): lambda x: x * 9/5 + 32,
    ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,
    ("celsius", "kelvin"):     lambda x: x + 273.15,
    # speed
    ("kmph", "mph"):      lambda x: x * 0.621371,
    ("mph", "kmph"):      lambda x: x * 1.60934,
    # data
    ("mb", "gb"):         lambda x: x / 1024,
    ("gb", "mb"):         lambda x: x * 1024,
    ("gb", "tb"):         lambda x: x / 1024,
}

def _try_conversion(t: str) -> str | None:
    m = re.search(r"([\d.]+)\s*(\w+)\s+(?:to|in|into)\s+(\w+)", t)
    if not m:
        return None
    val  = float(m.group(1))
    frm  = m.group(2).lower().rstrip("s")  # remove plural
    to   = m.group(3).lower().rstrip("s")

    # Normalize some aliases
    alias = {"kilometer": "km", "kilometre": "km", "mile": "miles",
             "pound": "pounds", "kilogram": "kg", "meter": "meters",
             "metre": "meters", "foot": "feet", "inch": "inches",
             "celsius": "celsius", "centigrade": "celsius",
             "fahrenheit": "fahrenheit", "kelvin": "kelvin"}
    frm = alias.get(frm, frm)
    to  = alias.get(to, to)

    fn = CONVERSIONS.get((frm, to))
    if fn:
        result = fn(val)
        return f"{val} {frm} = {result:.4g} {to}"
    return None


def _try_percentage(t: str) -> str | None:
    # "15 percent of 3500" or "15% of 3500"
    m = re.search(r"([\d.]+)\s*(?:percent|%)\s+of\s+([\d.]+)", t)
    if m:
        pct = float(m.group(1))
        of  = float(m.group(2))
        result = pct / 100 * of
        return f"{pct}% of {of} is {result:.4g}"

    # "what percent is 30 of 200"
    m = re.search(r"what\s+percent\s+is\s+([\d.]+)\s+of\s+([\d.]+)", t)
    if m:
        part  = float(m.group(1))
        whole = float(m.group(2))
        pct   = part / whole * 100
        return f"{part} is {pct:.4g}% of {whole}"
    return None


def _to_math_expr(t: str) -> str | None:
    """Convert natural language math to a Python expression string."""
    replacements = [
        (r"\bplus\b",      "+"),
        (r"\bminus\b",     "-"),
        (r"\btimes\b",     "*"),
        (r"\bmultiplied by\b", "*"),
        (r"\bdivided by\b",   "/"),
        (r"\bover\b",         "/"),
        (r"\bmod\b",          "%"),
        (r"\bto the power\b", "**"),
        (r"what(?:'s| is| are)?\s+", ""),
        (r"[,?!]", ""),
    ]
    expr = t
    for pattern, repl in replacements:
        expr = re.sub(pattern, repl, expr)

    # Remove anything that's not a safe math character
    expr = re.sub(r"[^\d\s\+\-\*\/\%\.\(\)\*\*]", "", expr).strip()
    if expr and any(c.isdigit() for c in expr):
        return expr
    return None
