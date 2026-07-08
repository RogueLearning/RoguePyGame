#!/usr/bin/env bash
# Build the web (WASM) version with pygbag.
#
# pygbag bundles the whole app folder and does NOT reliably exclude .venv, so
# we stage just the game sources + assets in a clean directory and build there,
# then copy the result back to ./build/web. Serve it with:
#     python -m http.server -d build/web 8000
# ...or run `.venv/bin/python -m pygbag main.py` to build+serve at :8000.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
STAGE="${TMPDIR:-/tmp}/roguepygame_web"

rm -rf "$STAGE"
mkdir -p "$STAGE/build"

# Game sources + assets only.
cp "$ROOT/main.py" "$ROOT/game.py" "$ROOT/save_system.py" "$STAGE/"
for d in Entities Map Items UI assets; do
  rsync -a --exclude='__pycache__' "$ROOT/$d" "$STAGE/"
done

# Reuse the already-downloaded WASM runtime cache to avoid re-downloading.
[ -d "$ROOT/build/web-cache" ] && cp -R "$ROOT/build/web-cache" "$STAGE/build/" || true

cd "$STAGE"
# --ume_block 0: don't wait for a user "media engagement" click before running
# (otherwise the loader can sit on "Loading, please wait...").
"$PY" -m pygbag --build --ume_block 0 main.py

rm -rf "$ROOT/build/web"
mkdir -p "$ROOT/build"
cp -R "$STAGE/build/web" "$ROOT/build/web"
echo "=== Built: $ROOT/build/web ==="
du -sh "$ROOT/build/web"/*.apk 2>/dev/null || true
