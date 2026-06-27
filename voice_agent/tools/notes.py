"""
tools/notes.py — Voice-friendly notes saved to a local text file.

"Note that I need to buy earphones"
"Save a note: call Rahul tomorrow"
"Read my notes"
"Delete my notes"
"How many notes do I have"
"""

import datetime
import os

NOTES_FILE = os.path.expanduser("~/voice_agent_notes.txt")


def add_note(text: str) -> str:
    """Save a new note with a timestamp."""
    timestamp = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    line = f"[{timestamp}] {text.strip()}\n"
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    return f"Saved: \"{text.strip()}\""


def read_notes() -> str:
    """Read all notes aloud."""
    if not os.path.exists(NOTES_FILE):
        return "You don't have any notes yet."
    with open(NOTES_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    if not lines:
        return "Your notes are empty."
    count = len(lines)
    result = f"You have {count} note{'s' if count > 1 else ''}:\n"
    result += "\n".join(lines[-10:])  # read last 10 to avoid super long output
    if count > 10:
        result += f"\n...and {count - 10} older notes."
    return result


def delete_notes() -> str:
    """Wipe all notes."""
    if os.path.exists(NOTES_FILE):
        os.remove(NOTES_FILE)
        return "All notes deleted."
    return "No notes to delete."


def count_notes() -> str:
    if not os.path.exists(NOTES_FILE):
        return "You have zero notes."
    with open(NOTES_FILE, "r", encoding="utf-8") as f:
        n = sum(1 for l in f if l.strip())
    return f"You have {n} note{'s' if n != 1 else ''}."
