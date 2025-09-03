# Development Guidelines for opencode-manager

## Core Principles

### The Golden Rule: Isolation is Sacred
The server must NEVER touch the user's real XDG directories or home directory. All file operations must be confined to the target directory. This is non-negotiable.

### Code Philosophy
- **Elegance and minimalism** - Write clean, simple code that does exactly what's needed, nothing more
- **Explicit over implicit** - No magic, no hidden behavior
- **Fail fast** - Clear errors are better than uncertain state

## Coding Standards

### Style Guides
- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- Follow the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) for scripts
- Python 3.9+ with type hints for all public methods
- Line length: 80 characters (Google standard)

### Naming and Formatting
- Always use lowercase `opencode` (never OpenCode or Opencode)
- Use ASCII characters only (no em-dashes, no emojis)
- Terminal color codes are acceptable where appropriate
- Use `black` for formatting, `ruff` for linting

### Git Commits
- Use [Conventional Commits](https://www.conventionalcommits.org/) format
- Follow the 50/72 rule (50 char subject, 72 char wrapped body)
- Examples:
  ```
  feat: add session pooling for concurrent operations

  Implement SessionPool class to manage multiple concurrent sessions
  within a single server instance. This allows better resource
  management and session lifecycle tracking.
  ```

## Development Workflow

### Before Committing
1. **All tests must pass** - Never skip tests, never commit with failing tests
2. **Run pre-commit hooks** - `make precommit` (automatically runs on commit)
3. **Fix any issues** - Pre-commit will check formatting, linting, types
4. **Human review required** - Always have changes reviewed before comitting

Pre-commit automatically runs:
- Unit tests (EVERY commit - no broken commits allowed!)
- Black formatter (80 char lines)
- Ruff linter
- Pyright type checker
- Trailing whitespace removal
- Correct "opencode" capitalization check

### Testing
```bash
# Unit tests (required before any commit)
uv run pytest tests/test_server.py tests/test_isolation.py

# Integration tests (costs API credits)
uv run pytest tests/test_integration.py
```

Minimum 80% code coverage for new code. Every public method needs a test.

## Project Structure

```
src/opencode_manager/   # Source code
tests/                  # Test files
  test_*.py            # Unit tests
  test_isolation.py    # Isolation tests (critical)
  test_integration.py  # Integration tests
```

## Common Patterns

### Path Handling
```python
# Good
from pathlib import Path
config_dir = Path("/tmp/test") / "config"

# Bad
config_dir = "/tmp/test/config"
```

### Resource Management
```python
# Always use context managers
with OpencodeServer(config) as server:
    # Server is running
    pass
# Server is stopped and cleaned up
```

### Error Messages
```python
# Provide actionable errors
if not auth_file.exists():
    raise FileNotFoundError(
        f"Auth file not found at {auth_file}. "
        f"Please ensure the file exists or provide a valid path."
    )
```

## API Design

### Method Signatures
Keep interfaces simple and consistent:
```python
def create_session(self, title: Optional[str] = None) -> Session:
def delete_session(self, session_id: str) -> None:
def get_session(self, session_id: str) -> Session:
```

### Return Values
- Return `None` for operations without meaningful results
- Return objects (not dicts) for data
- Raise exceptions for errors (don't return error codes)

## Security Considerations

- Never log authentication credentials
- Copy sensitive files with 0600 permissions
- Use minimal environment variables in subprocesses
- Validate all paths to prevent directory traversal

## Quick Reference

### Commands
```bash
make test          # Run unit tests
make format        # Format code
make lint          # Lint code
make typecheck     # Type check code
make clean         # Remove artifacts
```

### Files to Update
When making changes, update:
1. Tests (always first)
2. Documentation (README.md if user-facing)
3. ISOLATION.md (if touching isolation code)
4. This file (if adding new patterns)

## Remember

The primary goal is to provide a safe, isolated environment for opencode server testing and development. Every decision should support this goal. Keep it simple, keep it tested, keep it isolated.
