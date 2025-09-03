#!/bin/bash
# Set up git configuration for this project

echo "Setting up git configuration for opencode-server-python..."

# Set local commit template
git config --local commit.template .gitmessage
echo "[OK] Commit template configured"

# Install pre-commit hooks
if command -v pre-commit &> /dev/null; then
    pre-commit install --install-hooks
    pre-commit install --hook-type commit-msg
    echo "[OK] Pre-commit hooks installed"
else
    echo "[WARNING] pre-commit not installed. Run: uv pip install pre-commit"
fi

echo ""
echo "Git setup complete! Remember:"
echo "  - Use conventional commits (feat:, fix:, docs:, etc.)"
echo "  - Follow the 50/72 rule for commit messages"
echo "  - Always use lowercase 'opencode'"
echo "  - Run 'make test' before committing"
