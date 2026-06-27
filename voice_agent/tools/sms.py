"""
tools/sms.py — Send and read SMS via Termux:API.
Requires: termux-sms-send, termux-sms-list (from termux-api package)
Android permission: SMS (grant in Android Settings → Apps → Termux:API → Permissions)
"""
import subprocess
import json
import re
from tools.apps import _get_contacts, _find_contact


def send_sms(contact_name: str, message: str) -> str:
    """Send an SMS to a contact by name."""
    contacts = _get_contacts()
    number   = _find_contact(contact_name, contacts)

    if not number:
        return f"Couldn't find '{contact_name}' in your contacts."

    try:
        subprocess.run(
            ["termux-sms-send", "-n", number, message],
            capture_output=True, timeout=15,
        )
        return f"SMS sent to {contact_name}: '{message}'"
    except FileNotFoundError:
        return "SMS needs Termux:API with SMS permission. Go to Android Settings → Apps → Termux:API → Permissions → SMS."
    except Exception as e:
        return f"SMS failed: {e}"


def read_sms(count: int = 5) -> str:
    """Read the most recent SMS messages."""
    try:
        result = subprocess.run(
            ["termux-sms-list", "-l", str(count), "-t", "inbox"],
            capture_output=True, text=True, timeout=10,
        )
        messages = json.loads(result.stdout)

        if not messages:
            return "No messages in your inbox."

        lines = [f"Your last {len(messages)} messages:"]
        for msg in messages:
            sender  = msg.get("number", "Unknown")
            body    = msg.get("body", "")[:100]
            received = msg.get("received", "")
            lines.append(f"From {sender}: {body}")

        return " ".join(lines)
    except FileNotFoundError:
        return "Can't read SMS — Termux:API SMS permission needed."
    except Exception as e:
        return f"Couldn't read messages: {e}"
