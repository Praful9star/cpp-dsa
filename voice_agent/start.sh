#!/data/data/com.termux/files/usr/bin/bash
# start.sh — Auto-restart wrapper for the voice agent.
# If the agent crashes for any reason, this brings it back up after 3 seconds.
#
# Usage:  bash start.sh
#   Quit: Ctrl+C  (kills both this script and the agent)

cd "$(dirname "$0")"

termux-wake-lock 2>/dev/null &

echo ""
echo "╔══════════════════════════════════╗"
echo "║   Buddy — Voice Agent Launcher   ║"
echo "╚══════════════════════════════════╝"
echo "  Press Ctrl+C to stop."
echo ""

CRASHES=0

trap 'echo ""; echo "Stopping..."; termux-wake-unlock 2>/dev/null; exit 0' INT TERM

while true; do
    python agent.py
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        # Clean exit (Ctrl+C inside Python propagated up)
        echo "Agent exited cleanly."
        break
    fi

    CRASHES=$((CRASHES + 1))
    echo ""
    echo "[Launcher] Agent crashed (exit $EXIT_CODE). Restart #$CRASHES in 3s..."
    sleep 3
done

termux-wake-unlock 2>/dev/null
