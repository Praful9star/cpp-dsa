"""
tools/expenses.py — Voice expense tracker saved to SQLite.

"I spent 200 on food"
"Spent 500 on clothes"
"How much did I spend today / this week / this month"
"Show my expenses"
"Delete expenses"
"""
import sqlite3
import datetime
import re
import config

DB_PATH = config.DB_PATH


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            amount   REAL NOT NULL,
            category TEXT,
            note     TEXT,
            date     TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def add_expense(query: str) -> str:
    """Parse and save an expense from natural language."""
    amount, category, note = _parse_expense(query)
    if not amount:
        return "I couldn't figure out the amount. Say something like 'I spent 200 on food'."

    conn = _connect()
    conn.execute(
        "INSERT INTO expenses (amount, category, note, date) VALUES (?, ?, ?, date('now'))",
        (amount, category, note),
    )
    conn.commit()
    conn.close()
    return f"Logged: ₹{amount:.0f} on {category or note or 'misc'}."


def get_expenses(period: str = "today") -> str:
    """Summarize expenses for today / this week / this month."""
    conn = _connect()

    if "today" in period:
        where = "date = date('now')"
        label = "today"
    elif "week" in period:
        where = "date >= date('now', '-7 days')"
        label = "this week"
    elif "month" in period:
        where = "date >= date('now', 'start of month')"
        label = "this month"
    else:
        where = "date = date('now')"
        label = "today"

    rows = conn.execute(
        f"SELECT amount, category, note, date FROM expenses WHERE {where} ORDER BY id DESC"
    ).fetchall()
    conn.close()

    if not rows:
        return f"No expenses logged for {label}."

    total = sum(r[0] for r in rows)
    details = []
    for r in rows[:5]:
        cat = r[1] or r[2] or "misc"
        details.append(f"₹{r[0]:.0f} on {cat}")

    result = f"You spent ₹{total:.0f} {label}."
    if details:
        result += " Breakdown: " + ", ".join(details)
        if len(rows) > 5:
            result += f" and {len(rows)-5} more."
    return result


def delete_expenses() -> str:
    conn = _connect()
    conn.execute("DELETE FROM expenses")
    conn.commit()
    conn.close()
    return "All expense records deleted."


def _parse_expense(text: str):
    t = text.lower()

    # Amount: "200", "₹200", "rs 200", "rupees 200"
    m = re.search(r"(?:₹|rs\.?\s*|rupees?\s*)?([\d,]+(?:\.\d+)?)", t)
    amount = float(m.group(1).replace(",", "")) if m else None

    # Category keywords
    CATEGORIES = {
        "food": ["food", "eat", "lunch", "dinner", "breakfast", "snack", "restaurant", "swiggy", "zomato", "bhojan"],
        "transport": ["uber", "ola", "auto", "bus", "train", "metro", "petrol", "fuel", "cab", "taxi", "travel"],
        "shopping": ["clothes", "shirt", "shoes", "shopping", "amazon", "flipkart", "buy", "purchase"],
        "entertainment": ["movie", "netflix", "spotify", "game", "concert", "show"],
        "education": ["book", "course", "college", "fees", "stationary", "pen", "notebook"],
        "health": ["medicine", "doctor", "hospital", "gym", "pharmacy"],
        "utilities": ["recharge", "internet", "electricity", "phone", "bill"],
    }
    category = "misc"
    for cat, keywords in CATEGORIES.items():
        if any(k in t for k in keywords):
            category = cat
            break

    # Note: everything after "on" or "for"
    note_match = re.search(r"(?:on|for)\s+(.+?)(?:\s*$)", t)
    note = note_match.group(1).strip() if note_match else ""

    return amount, category, note
