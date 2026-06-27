"""
tools/apps.py — Open Android apps, make calls, send WhatsApp messages.

Uses Android intents via 'am' command (available in Termux).
Also wraps termux-telephony-call and termux-sms-send.
"""
import subprocess
import re

# Map of spoken app names to package names
APP_MAP = {
    "youtube":      "com.google.android.youtube",
    "whatsapp":     "com.whatsapp",
    "chrome":       "com.android.chrome",
    "google":       "com.google.android.googlequicksearchbox",
    "spotify":      "com.spotify.music",
    "instagram":    "com.instagram.android",
    "twitter":      "com.twitter.android",
    "x":            "com.twitter.android",
    "telegram":     "org.telegram.messenger",
    "maps":         "com.google.android.apps.maps",
    "google maps":  "com.google.android.apps.maps",
    "camera":       "com.android.camera2",
    "gallery":      "com.google.android.apps.photos",
    "photos":       "com.google.android.apps.photos",
    "calculator":   "com.google.android.calculator",
    "settings":     "com.android.settings",
    "files":        "com.google.android.documentsui",
    "clock":        "com.google.android.deskclock",
    "gmail":        "com.google.android.gm",
    "email":        "com.google.android.gm",
    "play store":   "com.android.vending",
    "playstore":    "com.android.vending",
    "facebook":     "com.facebook.katana",
    "snapchat":     "com.snapchat.android",
    "netflix":      "com.netflix.mediaclient",
    "zoom":         "us.zoom.videomeetings",
    "discord":      "com.discord",
    "reddit":       "com.reddit.frontpage",
    "linkedin":     "com.linkedin.android",
    "amazon":       "com.amazon.mShop.android.shopping",
    "flipkart":     "com.flipkart.android",
    "paytm":        "net.one97.paytm",
    "gpay":         "com.google.android.apps.nbu.paisa.user",
    "google pay":   "com.google.android.apps.nbu.paisa.user",
    "phonepe":      "com.phonepe.app",
    "swiggy":       "in.swiggy.android",
    "zomato":       "com.application.zomato",
    "termux":       "com.termux",
}


def open_app(query: str) -> str:
    """Open an Android app by name."""
    q = query.lower().strip()

    # Find best match
    package = None
    for name, pkg in APP_MAP.items():
        if name in q:
            package = pkg
            break

    if not package:
        return f"I don't know how to open '{query}'. Try saying the exact app name."

    try:
        result = subprocess.run(
            ["am", "start", "-n", f"{package}/{package}.MainActivity"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 or "Starting" in result.stdout:
            app_name = query.strip().title()
            return f"Opening {app_name}."

        # Fallback: use monkey (simpler launch)
        result2 = subprocess.run(
            ["monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
            capture_output=True, text=True, timeout=10,
        )
        return f"Opening {query.strip().title()}."
    except Exception as e:
        return f"Couldn't open that app: {e}"


def make_call(contact_name: str) -> str:
    """Initiate a phone call via termux-telephony-call."""
    try:
        # Try to find number from contacts
        contacts = _get_contacts()
        number = _find_contact(contact_name, contacts)

        if not number:
            return f"I couldn't find '{contact_name}' in your contacts. Ask me to call a specific number instead."

        subprocess.Popen(
            ["termux-telephony-call", number],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return f"Calling {contact_name}."
    except FileNotFoundError:
        return "Phone calls need Termux:API with phone permission enabled."
    except Exception as e:
        return f"Call failed: {e}"


def send_whatsapp(contact_name: str, message: str) -> str:
    """Open WhatsApp with a pre-filled message to a contact."""
    try:
        contacts = _get_contacts()
        number   = _find_contact(contact_name, contacts)

        if not number:
            return f"Couldn't find '{contact_name}' in contacts."

        # Strip non-digits, add country code if needed
        clean = re.sub(r"\D", "", number)
        if len(clean) == 10:
            clean = "91" + clean  # India default

        subprocess.Popen([
            "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", f"https://api.whatsapp.com/send?phone={clean}&text={message}",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return f"Opening WhatsApp to message {contact_name}: '{message}'"
    except Exception as e:
        return f"WhatsApp failed: {e}"


def _get_contacts() -> list[dict]:
    try:
        import json
        result = subprocess.run(
            ["termux-contact-list"], capture_output=True, text=True, timeout=10
        )
        return json.loads(result.stdout)
    except Exception:
        return []


def _find_contact(name: str, contacts: list[dict]) -> str | None:
    name_lower = name.lower()
    for c in contacts:
        if name_lower in c.get("name", "").lower():
            numbers = c.get("number", [])
            if isinstance(numbers, list) and numbers:
                return numbers[0].get("number") or numbers[0]
            if isinstance(numbers, str):
                return numbers
    return None
