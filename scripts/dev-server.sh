#!/usr/bin/env bash
# Run the service (with a simulated USB stick) and the web UI locally for development.
# Requires python3 with the "cryptography" package and php with the curl extension.
#
#   ./scripts/dev-server.sh            # UI on http://127.0.0.1:8080
#   PORT=9000 ./scripts/dev-server.sh
#
# The simulated stick is the folder .dev/lib/usb-sim – copy files into it to
# simulate recordings. The setup code is printed below.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8080}"
export NETUSBFLASH_HOME="$ROOT/.dev"
export NETUSBFLASH_SIMULATE=1
export NETUSBFLASH_SOCKET="$NETUSBFLASH_HOME/run/api.sock"
mkdir -p "$NETUSBFLASH_HOME"

PYTHONPATH="$ROOT/daemon" python3 -m netusbflash --simulate &
DAEMON_PID=$!
trap 'kill $DAEMON_PID 2>/dev/null || true' EXIT

for _ in $(seq 1 50); do
    [ -S "$NETUSBFLASH_SOCKET" ] && break
    sleep 0.1
done

if [ -f "$NETUSBFLASH_HOME/etc/setup-token" ]; then
    echo "Setup code: $(cat "$NETUSBFLASH_HOME/etc/setup-token")"
fi
echo "Simulated USB stick: $NETUSBFLASH_HOME/lib/usb-sim"
echo "Web UI: http://127.0.0.1:$PORT"

php -S "127.0.0.1:$PORT" -t "$ROOT/web/public" "$ROOT/web/dev-router.php"
