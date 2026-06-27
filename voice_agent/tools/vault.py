"""
tools/vault.py — Voice-activated secret vault with obfuscated storage.

"Add to vault key MYPASS: my wifi password is XYZ"
"Open vault key MYPASS"
"Vault status"
"Clear vault key MYPASS"

XOR + base64 obfuscation — local-only, no network.
"""

import sqlite3
import base64
import datetime
import re
import config

DB_PATH = config.DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS vault (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content BLOB NOT NULL,
        date TEXT
    )""")
    c.commit()
    return c


def _xor_encode(text: str, key: str) -> bytes:
    kb = (key * 64).encode()[:max(len(text), 1)]
    return bytes(b ^ kb[i] for i, b in enumerate(text.encode()))


def _xor_decode(blob: bytes, key: str) -> str:
    kb = (key * 64).encode()[:max(len(blob), 1)]
    return bytes(b ^ kb[i] for i, b in enumerate(blob)).decode(errors="replace")


def _parse_key(query: str):
    """Extract passkey and content from query."""
    m = re.search(r'\bkey\s+(\S+)\s*[:\-]?\s*(.*)', query, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2).strip()
    return None, None


def add_to_vault(query: str) -> str:
    key, content = _parse_key(
        re.sub(r'^(add to vault|vault add|store secret)\s*', '', query, flags=re.IGNORECASE).strip()
    )
    if not key:
        return "Say: 'add to vault key YOURKEY: the secret'. I need a key to lock it."
    if not content:
        return "What's the secret? Say: 'add to vault key YOURKEY: the secret content'."

    blob = base64.b64encode(_xor_encode(content, key))
    c = _conn()
    c.execute("INSERT INTO vault (content, date) VALUES (?, ?)", (blob, str(datetime.date.today())))
    c.commit()
    total = c.execute("SELECT COUNT(*) FROM vault").fetchone()[0]
    c.close()
    return f"Locked with your key. Vault holds {total} secret{'s' if total != 1 else ''}. Don't forget your key."


def open_vault(query: str) -> str:
    key, _ = _parse_key(re.sub(r'^(open vault|read vault|show vault)\s*', '', query, flags=re.IGNORECASE).strip())
    if not key:
        return "Say: 'open vault key YOURKEY'."

    c = _conn()
    rows = c.execute("SELECT content, date FROM vault ORDER BY id DESC LIMIT 10").fetchall()
    c.close()
    if not rows:
        return "Vault is empty."

    entries = []
    for blob_b64, date in rows:
        try:
            blob = base64.b64decode(blob_b64)
            decrypted = _xor_decode(blob, key)
            entries.append(f"[{date}] {decrypted}")
        except Exception:
            entries.append(f"[{date}] [unreadable — wrong key?]")
    return "Vault: " + " | ".join(entries)


def vault_status() -> str:
    c = _conn()
    n = c.execute("SELECT COUNT(*) FROM vault").fetchone()[0]
    c.close()
    return f"Vault has {n} secret{'s' if n != 1 else ''}. Use 'open vault key YOURKEY' to read."


def clear_vault(query: str) -> str:
    key, _ = _parse_key(re.sub(r'^(clear vault|delete vault|wipe vault)\s*', '', query, flags=re.IGNORECASE).strip())
    if not key:
        return "Say: 'clear vault key YOURKEY'."
    c = _conn()
    c.execute("DELETE FROM vault")
    c.commit()
    c.close()
    return "Vault wiped."
