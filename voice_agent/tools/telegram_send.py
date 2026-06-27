"""
tools/telegram_send.py — Send a Telegram message via Bot API.

Setup (one-time):
  1. Message @BotFather on Telegram → /newbot → copy the token
  2. Start a chat with your bot, then visit:
     https://api.telegram.org/bot<TOKEN>/getUpdates
     to find your chat_id
  3. Add to .env:
       TELEGRAM_BOT_TOKEN=...
       TELEGRAM_CHAT_ID=...

Trigger phrase examples:
  "message mom saying I'll be late"
  "tell Rahul I'm on my way"

Note: In Phase 3 the agent sends to YOUR chat by default.
      Multi-contact support (address book) can come later.
"""

import requests
import config


def send_telegram(message: str, recipient: str = "") -> str:
    """
    Send a Telegram message to the configured chat.
    recipient is noted in the message for context but all messages
    go to TELEGRAM_CHAT_ID for now.
    Returns a status string for the LLM to relay to the user.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return (
            "Telegram isn't set up yet. "
            "Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to your .env file."
        )

    # Build the actual message text
    if recipient:
        text = f"[To {recipient}]: {message}"
    else:
        text = message

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
        resp.raise_for_status()
        return f"Done — sent to {recipient or 'your Telegram'}: \"{message}\""
    except requests.exceptions.ConnectionError:
        return "Couldn't reach Telegram — check your internet."
    except Exception as e:
        return f"Telegram send failed: {e}"
