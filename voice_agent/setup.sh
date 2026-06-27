#!/data/data/com.termux/files/usr/bin/bash
# setup.sh — One-time Termux setup for the voice agent.
# Run this once after cloning the repo on your Android tablet.

set -e

echo "=== Voice Agent — Termux Setup ==="

# ── 1. Core Termux packages ───────────────────────────────────────────────────
echo "[1/4] Installing Termux packages..."
pkg update -y
pkg install -y python python-pip termux-api

# ── 2. Python dependencies ────────────────────────────────────────────────────
echo "[2/4] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# ── 3. .env file ──────────────────────────────────────────────────────────────
echo "[3/4] Checking .env file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "  *** .env created from .env.example ***"
    echo "  Open it and set your ANTHROPIC_API_KEY before running the agent:"
    echo "    nano .env"
    echo ""
else
    echo "  .env already exists — skipping."
fi

# ── 4. Verify Termux:API is installed ─────────────────────────────────────────
echo "[4/4] Checking Termux:API..."
if ! command -v termux-speech-to-text &>/dev/null; then
    echo ""
    echo "  *** WARNING: termux-speech-to-text not found ***"
    echo "  Make sure you have installed the Termux:API companion app from F-Droid:"
    echo "    https://f-droid.org/packages/com.termux.api/"
    echo "  Then run: pkg install termux-api"
    echo ""
else
    echo "  termux-api looks good."
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "To start the agent:"
echo "  cd voice_agent"
echo "  python agent.py"
echo ""
echo "To keep it running when the screen turns off:"
echo "  termux-wake-lock   # run once, keeps CPU awake"
echo "  python agent.py"
