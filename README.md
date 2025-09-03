# opencode-manager

Python library for managing isolated opencode server instances with full lifecycle control.

** Complete XDG Isolation:** Server instances run in fully isolated environments, never touching your personal files or directories. [Learn more →](ISOLATION.md)

## Prerequisites

- [`uv`](https://github.com/astral-sh/uv) for Python package management
- Node.js/npm (for development tools like pyright)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd opencode-manager
uv sync

# Run tests
uv run pytest

# Run example
uv run python examples/basic_usage.py
```

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd opencode-manager

# Install all dependencies (Python + dev tools)
make install

# Or manually:
uv sync             # Python dependencies
npm install         # Dev tools (pyright)
```

## Usage

```python
from pathlib import Path
from opencode_manager import OpencodeServer

# Start a server with isolated environment
with OpencodeServer(
    target_dir=Path("./test_env"),
    auth_file=Path("./auth.json"),
    opencode_config_dir=Path("./.opencode"),
    opencode_json=Path("./opencode.json"),
    opencode_binary=Path("./opencode"),
    delete_target_dir_on_exit=True
) as server:
    # Create a session
    session = server.create_session("Test Session")

    # Send message and get response
    response = session.send_message("Hello!")
    print(response)

    # Get messages
    messages = session.get_messages()
```

## Running Tests

### Unit Tests

```bash
# Run all unit tests
uv run pytest tests/test_server.py -v

# Run with coverage
uv run pytest tests/test_server.py --cov=opencode_manager
```

### Integration Tests

**[!] Warning:** Integration tests make REAL API calls and will incur costs!

Integration tests use real opencode server instances and show detailed progress.
They will consume API credits from your configured provider (OpenAI, Anthropic, etc.).

First, set up test resources:
```bash
./test_resources/setup.sh
```

Then run tests:
```bash
# Run integration tests (shows test names and detailed operation progress)
uv run pytest tests/test_integration.py

# Run with less output (hide operation details)
uv run pytest tests/test_integration.py --capture=sys
```

### Run All Tests

```bash
# Run all tests except integration
uv run pytest -m "not integration"

# Run everything
uv run pytest
```

## Development

```bash
# Install development dependencies
make install

# Format code
make format

# Lint
make lint

# Type check
make typecheck
```

## Running Examples

```bash
# Run the basic usage example
uv run python examples/basic_usage.py
```

## Features

- **Complete isolation** - Server NEVER touches your real home or XDG directories
- Isolated XDG-compliant environments for each server instance
- Full server lifecycle management (start/stop/health checks)
- Session management (create/list/delete/abort)
- Message tracking with read cursors
- Automatic port discovery
- Comprehensive logging
- Automatic selection of cheapest models for testing (Haiku, GPT-4o-mini, Gemini Flash)
- Comprehensive isolation testing and verification

## Requirements

- Python 3.9+
- `opencode-ai` SDK (automatically installed)
- `opencode` binary (must be available)
- `uv` package manager
