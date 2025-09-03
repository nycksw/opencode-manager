#!/bin/bash
# Check if development dependencies are installed

EXIT_CODE=0

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv is not installed. See: https://github.com/astral-sh/uv"
    EXIT_CODE=1
else
    echo "[OK] uv is installed"
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed. Install from: https://nodejs.org/"
    EXIT_CODE=1
else
    echo "[OK] Node.js is installed ($(node --version))"
fi

# Check for npm
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm is not installed"
    EXIT_CODE=1
else
    echo "[OK] npm is installed ($(npm --version))"
fi

# Check for pyright (if package.json exists)
if [ -f package.json ]; then
    if [ ! -d node_modules ]; then
        echo "[WARNING] pyright not installed. Run: make install"
        EXIT_CODE=1
    else
        echo "[OK] Node modules installed"
    fi
fi

# Check Python virtual environment
if [ ! -d .venv ]; then
    echo "[WARNING] Python virtual environment not found. Run: uv sync"
    EXIT_CODE=1
else
    echo "[OK] Python virtual environment exists"
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "All development dependencies are installed!"
else
    echo ""
    echo "Some dependencies are missing. Run: make install"
fi

exit $EXIT_CODE
