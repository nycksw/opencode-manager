#!/usr/bin/env bash
#
# Setup script for test_resources - copies your real opencode configs for testing
# Usage: ./test_resources/setup.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo "OpenCode Test Resources Setup"
echo "=============================="
echo ""
echo "This script will copy your opencode configuration files for testing."
echo "Your original files will NOT be modified."
echo ""

# Get the script directory (test_resources/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check for required source files
AUTH_SOURCE="$HOME/.local/share/opencode/auth.json"
CONFIG_SOURCE="$HOME/.config/opencode/opencode.json"

# Check auth.json
if [ ! -f "$AUTH_SOURCE" ]; then
    echo -e "${RED}[!] Error: auth.json not found at $AUTH_SOURCE${NC}"
    echo "   Please ensure opencode is configured first."
    echo "   Run: opencode auth"
    exit 1
fi

# Check opencode.json
if [ ! -f "$CONFIG_SOURCE" ]; then
    echo -e "${YELLOW}[!] Warning: opencode.json not found at $CONFIG_SOURCE${NC}"
    echo "   Looking for project-local opencode.json..."

    # Try to find a project opencode.json
    # Check parent directories
    if [ -f "$SCRIPT_DIR/../opencode.json" ]; then
        CONFIG_SOURCE="$SCRIPT_DIR/../opencode.json"
        echo -e "   Found: ${GREEN}$(realpath "$CONFIG_SOURCE")${NC}"
    elif [ -f "$SCRIPT_DIR/../../opencode.json" ]; then
        CONFIG_SOURCE="$SCRIPT_DIR/../../opencode.json"
        echo -e "   Found: ${GREEN}$(realpath "$CONFIG_SOURCE")${NC}"
    else
        echo -e "${YELLOW}   No opencode.json found. Tests will use default configuration.${NC}"
        CONFIG_SOURCE=""
    fi
fi

# Warning about costs
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}[!] WARNING: Integration tests use REAL API calls${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Integration tests will:"
echo "  • Make real requests to your configured AI provider"
echo "  • Consume API credits (costs money)"
echo "  • Count against your rate limits"
echo ""
echo "  Consider using a test API key with spending limits."
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Confirm before copying
echo ""
echo "Ready to copy:"
echo "  • auth.json from: $AUTH_SOURCE"
if [ -n "$CONFIG_SOURCE" ]; then
    echo "  • opencode.json from: $(realpath "$CONFIG_SOURCE")"
fi
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Copy files
echo ""
echo "Copying files..."

# Copy auth.json (secure method - create with permissions first)
touch "$SCRIPT_DIR/auth.json"
chmod 600 "$SCRIPT_DIR/auth.json"
cp "$AUTH_SOURCE" "$SCRIPT_DIR/auth.json"
echo "Copied auth.json (permissions: 600)"

# Copy opencode.json if found (also secure)
if [ -n "$CONFIG_SOURCE" ]; then
    touch "$SCRIPT_DIR/opencode.json"
    chmod 600 "$SCRIPT_DIR/opencode.json"
    cp "$CONFIG_SOURCE" "$SCRIPT_DIR/opencode.json"
    echo "Copied opencode.json (permissions: 600)"
else
    echo "Skipped opencode.json (not found)"
fi

# Handle opencode binary
echo ""
echo "Setting up opencode binary..."

# Check if symlink/binary already exists
if [ -L "$SCRIPT_DIR/opencode" ]; then
    EXISTING_TARGET=$(readlink "$SCRIPT_DIR/opencode")
    echo "Existing symlink found: opencode -> $EXISTING_TARGET"
    read -p "   Keep this? (Y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        rm "$SCRIPT_DIR/opencode"
        echo "   Removed existing symlink"
    else
        echo "Keeping existing symlink"
    fi
elif [ -f "$SCRIPT_DIR/opencode" ]; then
    echo "Existing opencode binary found"
    read -p "   Keep this? (Y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        rm "$SCRIPT_DIR/opencode"
        echo "   Removed existing binary"
    else
        echo "Keeping existing binary"
    fi
fi

# If no binary/symlink exists (or user removed it), set it up
if [ ! -e "$SCRIPT_DIR/opencode" ]; then
    # Try to find opencode in PATH
    DEFAULT_OPENCODE=""
    if command -v opencode &> /dev/null; then
        DEFAULT_OPENCODE=$(which opencode)
        echo "Found opencode at: $DEFAULT_OPENCODE"
    else
        echo -e "${YELLOW}[!] Warning: opencode not found in PATH${NC}"
    fi

    # Ask user for path
    echo ""
    if [ -n "$DEFAULT_OPENCODE" ]; then
        echo "Use $DEFAULT_OPENCODE for integration tests?"
        read -p "Press Enter to accept, or enter path to different binary: " OPENCODE_PATH
        if [ -z "$OPENCODE_PATH" ]; then
            OPENCODE_PATH="$DEFAULT_OPENCODE"
        fi
    else
        read -p "Enter path to opencode binary: " OPENCODE_PATH
    fi

    # Validate the path
    if [ ! -f "$OPENCODE_PATH" ]; then
        echo -e "${RED}[!] Error: File not found: $OPENCODE_PATH${NC}"
        exit 1
    fi

    if [ ! -x "$OPENCODE_PATH" ]; then
        echo -e "${RED}[!] Error: File is not executable: $OPENCODE_PATH${NC}"
        exit 1
    fi

    # Try to create symlink first, fall back to copy
    echo ""
    echo "Setting up opencode binary..."
    if ln -s "$OPENCODE_PATH" "$SCRIPT_DIR/opencode" 2>/dev/null; then
        echo "Created symlink: opencode -> $OPENCODE_PATH"
    else
        echo "   Symlink failed (might be on Windows or cross-filesystem)"
        echo "   Copying binary instead..."
        cp "$OPENCODE_PATH" "$SCRIPT_DIR/opencode"
        chmod +x "$SCRIPT_DIR/opencode"
        echo "Copied opencode binary"
    fi
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "You can now run integration tests:"
echo "   uv run pytest tests/test_integration.py"
echo ""
echo -e "${YELLOW}[!] Remember:${NC}"
echo "   • auth.json and opencode.json are in .gitignore"
echo "   • These files should NEVER be committed to version control"
echo "   • Integration tests will make REAL API calls that cost money!"
