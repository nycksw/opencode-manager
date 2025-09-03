# opencode-manager

**opencode-manager** is designed to help orchestrate multiple AI agents working in parallel to solve complex tasks. The system manages 5-10 concurrent opencode sessions, each running an independent agent that can be monitored and controlled by an external coordination system. This project provides the interface for such a system.

**Complete XDG/Config/Data Isolation:** Server instances run in fully isolated environments, never touching your personal files or directories. [Learn more →](ISOLATION.md)

## Version Compatibility

The system automatically manages opencode versions for compatibility:

| Component | Version | Notes |
|-----------|---------|-------|
| opencode-ai SDK | 0.1.0a36 | Latest available SDK |
| opencode binary | v0.5.28 | Automatically downloaded via `make setup` |
| Python | 3.9+ | Type hints require 3.9+ |

**Important:** opencode v0.6.0+ has breaking API changes incompatible with the current SDK. See [API_CHANGES.md](API_CHANGES.md) for details.

## Prerequisites

- [`uv`](https://github.com/astral-sh/uv) for Python package management
- Python 3.9 or higher
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

# Install dependencies and setup everything (opencode binary + test resources)
make install
make setup

# Run tests
make test

# Run example
make example
```

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd opencode-manager

# Install all dependencies (Python + dev tools)
make install

# Setup everything (download opencode binary + configure test resources)
make setup

# Or setup components individually:
make setup-bin        # Download compatible opencode binary to ./bin
make setup-test       # Setup test resources in ./test_resources

# Or manually:
uv sync                          # Python dependencies
npm install                      # Dev tools (pyright)
python scripts/download_opencode.py  # Download recommended version
```

## Usage

See [`examples/basic_usage.py`](examples/basic_usage.py) for a complete working example that demonstrates:
- Server initialization with isolated environment
- Session creation and management
- Sending messages and receiving responses
- Proper resource cleanup

Run the example with:
```bash
make example
# Or directly:
uv run python examples/basic_usage.py
```

## Running Tests

### Unit Tests

```bash
# Run unit tests (no API calls, no costs)
make test

# Or explicitly:
make test-unit
```

### Integration Tests

**[!] Warning:** Integration tests make REAL API calls and will incur costs!

Integration tests use real opencode server instances and show detailed progress.
They will consume API credits from your configured provider (OpenAI, Anthropic, etc.).

First, ensure test resources are setup (automatically done by `make setup`):
```bash
make setup-test  # Only needed if you haven't run `make setup`
```

Then run tests:
```bash
# Run integration tests (shows test names and detailed operation progress)
make test-integration

# Or run directly with less output (hide operation details)
uv run python -m pytest tests/test_integration.py --capture=sys
```

### Run All Tests

```bash
# Run all tests
make test-all

# Run all tests except integration (using Python module syntax)
uv run python -m pytest -m "not integration"
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
make example

# Or run directly
uv run python examples/basic_usage.py
```

## API Specification

The project tracks the OpenAPI specification and version of the opencode binary:

```bash
# Update API spec and version (runs integration test)
make update-api-spec

# Check if API spec has changed (useful in CI)
make check-api-spec
```

The system automatically uses the compatible opencode version from `./bin/opencode` with full isolation.

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
