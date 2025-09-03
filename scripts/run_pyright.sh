#!/bin/bash
# Run pyright if it's installed

if [ -d node_modules ]; then
    npm run typecheck
else
    echo "Skipping pyright (not installed)"
    exit 0
fi
