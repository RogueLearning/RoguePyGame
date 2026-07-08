#!/bin/bash

# Build and serve the WEB (WebAssembly) version of the game.
# The original start.sh still runs the native desktop version.

# Find the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Pick the Python interpreter (prefer the local virtual environment)
if [ -f "./.venv/bin/python" ]; then
    PY="./.venv/bin/python"
else
    echo "Virtual environment not found, falling back to system python3..."
    PY="python3"
fi

# Ensure pygbag (the pygame -> WebAssembly packager) is installed
if ! "$PY" -c "import pygbag" >/dev/null 2>&1; then
    echo "pygbag not found; installing it into the current environment..."
    "$PY" -m pip install pygbag || { echo "Failed to install pygbag."; exit 1; }
fi

# Build the slim web bundle into build/web (staged so .venv isn't packaged)
echo "Building web (WASM) build..."
./build_web.sh || { echo "Web build failed."; exit 1; }

# Serve it with the cross-origin isolation headers pygame-web requires.
# First page load downloads the pygame-ce WASM runtime, so internet is needed.
PORT="${1:-8000}"
echo ""
echo "Serving the web version. Open it at:"
echo "    http://localhost:$PORT"
echo "On a phone/tablet on the same Wi-Fi, use this computer's LAN IP, e.g.:"
echo "    http://192.168.x.x:$PORT"
echo "Press Ctrl+C to stop."
echo ""
"$PY" serve_web.py "$PORT" build/web
