#!/bin/bash

# Find the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Check if the virtual environment python interpreter exists
if [ -f "./.venv/bin/python" ]; then
    echo "Starting game using local virtual environment..."
    ./.venv/bin/python rogue.py
else
    echo "Virtual environment not found, falling back to system python3..."
    python3 rogue.py
fi
