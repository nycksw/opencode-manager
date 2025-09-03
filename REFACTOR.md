# Refactoring Plan for opencode-manager

## Current State Analysis

### Project Overview

The opencode-manager library provides a Python interface for managing isolated opencode server instances. The primary use case is running multiple concurrent sessions within a single server instance for automation and testing purposes.

### Codebase Metrics

- **Main class**: `OpencodeServer` - 429 lines, 20 methods
- **Supporting class**: `Session` - 133 lines, wrapper with convenience methods
- **Test coverage**: 12 unit tests, comprehensive isolation testing
- **API coverage**: Approximately 20% of available OpenAPI endpoints

### Strengths

1. **Complete XDG isolation** - Server instances run in fully isolated environments, never touching user directories
2. **Stable process management** - Single server instance handles multiple sessions reliably
3. **Session management basics** - Can create, list, delete sessions
4. **Good test coverage** - Unit and integration tests with clear separation
5. **Modern tooling** - Uses uv package manager, pyproject.toml configuration

### What Actually Needs Work

1. **Missing session operations** - Critical endpoints for concurrent session work not implemented
2. **No event streaming** - Cannot monitor multiple sessions in real-time
3. **Limited session state tracking** - Difficult to manage multiple concurrent sessions
4. **Session error recovery** - Sessions can fail without good recovery mechanisms
5. **Constructor complexity** - Takes 9 parameters, could benefit from configuration object

## Focused Refactoring Strategy

### Design Principles

1. **Focus on session concurrency** - Multiple sessions, single server
2. **Stability over architecture** - Current structure works, don't fix what isn't broken
3. **Incremental additions** - Add missing features without breaking existing code
4. **Isolation remains sacred** - Never compromise the XDG isolation guarantees

### Phase 1: Critical Session Operations (HIGH Priority)

These are the missing operations needed for concurrent session management:

#### 1.1 Session Command Execution

```python
def execute_command(self, session_id: str, command: str, args: str) -> Response:
    """Execute a command in a specific session."""
    pass

def execute_shell(self, session_id: str, command: str) -> str:
    """Execute a shell command in a session context."""
    pass
```

#### 1.2 Session State Management

```python
def revert_message(self, session_id: str, message_id: str) -> None:
    """Revert to a previous message state."""
    pass

def get_session_state(self, session_id: str) -> SessionState:
    """Get detailed state of a session."""
    pass
```

#### 1.3 Enhanced Session Wrapper

Improve the Session class to track state better:

```python
class Session:
    def __init__(self, server, session_data):
        self._server = server
        self._data = session_data
        self._state = "active"  # active, idle, error
        self._last_activity = time.time()

    def execute_command(self, command: str, args: str):
        """Execute command in this session."""
        pass

    def is_alive(self) -> bool:
        """Check if session is still responsive."""
        pass
```

### Phase 2: Event Streaming (HIGH Priority)

Essential for monitoring multiple concurrent sessions:

```python
# src/opencode_manager/events.py
import asyncio
from typing import AsyncIterator

class EventMonitor:
    """Monitor events from all sessions."""

    def __init__(self, server_url: str):
        self.server_url = server_url

    async def stream_events(self) -> AsyncIterator[dict]:
        """Stream events from the server."""
        # SSE implementation
        pass

    def get_session_events(self, session_id: str):
        """Filter events for specific session."""
        pass
```

### Phase 3: Configuration Simplification (MEDIUM Priority)

Simplify server setup:

```python
# src/opencode_manager/config.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class ServerConfig:
    """Configuration for opencode server instance."""
    target_dir: Path
    auth_file: Path
    opencode_config_dir: Path
    opencode_json: Path
    opencode_binary: Path
    port: Optional[int] = None
    hostname: Optional[str] = None
    delete_target_dir_on_exit: bool = False
    startup_timeout: float = 10.0
```

### Phase 4: Session Pool Management (MEDIUM Priority)

Helper for managing multiple sessions:

```python
# src/opencode_manager/pool.py
class SessionPool:
    """Manage multiple concurrent sessions."""

    def __init__(self, server: OpencodeServer, max_sessions: int = 10):
        self.server = server
        self.max_sessions = max_sessions
        self.sessions = {}

    def create_session(self, title: str = None) -> Session:
        """Create and track a new session."""
        pass

    def get_idle_session(self) -> Optional[Session]:
        """Get an idle session or None."""
        pass

    def cleanup_dead_sessions(self):
        """Remove unresponsive sessions."""
        pass
```

## What We're NOT Doing

1. **Class decomposition** - Current monolithic structure is fine for single server
2. **Pydantic models** - Overkill for internal use
3. **Provider management** - Current simple approach works
4. **File operations API** - Unless specifically needed
5. **TUI operations** - Not relevant for automation

## Implementation Order

### Immediate (This Week)

1. Add session command execution methods
2. Add session state management/revert
3. Enhance Session wrapper class

### Next Priority (Next Week)

1. Implement event streaming (async)
2. Create SessionPool helper
3. Add session health checks

### When Convenient

1. Create ServerConfig dataclass
2. Add backward compatible constructor
3. Documentation updates

## Testing Strategy

1. **Test concurrent sessions** - Multiple sessions running simultaneously
2. **Test session recovery** - Handle failed/stuck sessions
3. **Test event streaming** - Monitor multiple session events
4. **Maintain isolation tests** - These must always pass

## Success Metrics

1. **Can run 5+ concurrent sessions** reliably
2. **Can monitor all session events** in real-time
3. **Can recover from session failures** gracefully
4. **Zero XDG pollution** (already achieved, maintain it)
5. **Server remains stable** under concurrent load

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Session interference | High | Test concurrent session isolation |
| Memory leaks from sessions | High | Implement session cleanup/pooling |
| Event stream overwhelming | Medium | Add event filtering/buffering |
| Breaking existing code | Low | All changes are additions |

## Decision Log

1. **Single server, multiple sessions** - More efficient than multiple servers
2. **Keep monolithic class** - Works fine for single server management
3. **Prioritize session operations** - Critical for concurrent automation
4. **Skip architectural refactoring** - Current structure is adequate

## Next Steps

1. Implement missing session operations
2. Add event streaming support
3. Create session pool manager
4. Test with concurrent workloads

## Notes

- Focus on practical improvements for concurrent session use
- Don't refactor working code without clear benefit
- Maintain the excellent isolation already achieved
- Keep changes incremental and testable
