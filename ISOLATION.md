# XDG Directory Isolation in opencode-manager

## Security Guarantee

**This library GUARANTEES complete isolation from your personal XDG directories and home directory.**

When you use `OpencodeServer`, it creates a completely isolated environment for the opencode server process. The server CANNOT and WILL NOT access:

- Your home directory (`~`)
- Your XDG config directory (`~/.config`)
- Your XDG data directory (`~/.local/share`)
- Your XDG cache directory (`~/.cache`)
- Any other personal files or directories

## How Isolation Works

### 1. Isolated Directory Structure

Each `OpencodeServer` instance creates its own isolated directory structure:

```
target_dir/
├── .oc/
│   ├── config/         # Isolated XDG_CONFIG_HOME
│   ├── data/           # Isolated XDG_DATA_HOME
│   │   └── opencode/
│   │       └── auth.json  # Copied auth credentials (0600 perms)
│   ├── state/          # Isolated XDG_STATE_HOME
│   ├── cache/          # Isolated XDG_CACHE_HOME
│   └── runtime/        # Isolated XDG_RUNTIME_DIR (0700 perms)
├── .home/              # Isolated HOME directory
├── .tmp/               # Isolated temp directory
├── .opencode/          # Copied opencode configuration
└── opencode.json       # Copied opencode config file
```

### 2. Environment Variable Isolation

The server subprocess runs with a **minimal, clean environment**:

```python
# ONLY these environment variables are passed:
{
    'XDG_CONFIG_HOME': 'target_dir/.oc/config',
    'XDG_DATA_HOME': 'target_dir/.oc/data',
    'XDG_STATE_HOME': 'target_dir/.oc/state',
    'XDG_CACHE_HOME': 'target_dir/.cache',
    'XDG_RUNTIME_DIR': 'target_dir/.runtime',
    'HOME': 'target_dir/.home',
    'TMPDIR': 'target_dir/.tmp',
    'PATH': '/usr/local/bin:/usr/bin:/bin',  # Minimal system paths only
    'LANG': 'en_US.UTF-8',
    'LC_ALL': 'C.UTF-8',
    'TERM': 'xterm-256color',
    'USER': 'opencode',
    'LOGNAME': 'opencode'
}
```

**Notable absences:**
- No `SSH_*` variables
- No `AWS_*` or cloud credentials
- No `DOCKER_*` variables
- No custom `PATH` additions
- No shell configuration variables

### 3. Process Isolation

The subprocess is started with:
- `close_fds=True` - No file descriptor inheritance
- Clean environment - Not a copy of parent environment
- Working directory set to `target_dir`

### 4. Runtime Verification

The library performs runtime checks to ensure:
- Target directory is NOT inside sensitive paths
- All created directories are under target_dir
- No symlinks point outside the isolated environment

## Usage Examples

### Safe Testing/Development

```python
from pathlib import Path
from opencode_server import OpencodeServer

# Use a temporary directory for complete isolation
with OpencodeServer(
    target_dir=Path("/tmp/opencode_test"),
    auth_file=Path("test_auth.json"),
    opencode_config_dir=Path("test_config"),
    opencode_json=Path("test_opencode.json"),
    opencode_binary=Path("opencode"),
    delete_target_dir_on_exit=True  # Auto-cleanup
) as server:
    # Server is completely isolated
    session = server.create_session("Test")
    # ... do testing ...
# Everything is cleaned up automatically
```

### Integration Testing

```python
import tempfile
from pathlib import Path

# Use pytest's tmp_path or tempfile for guaranteed isolation
with tempfile.TemporaryDirectory() as tmpdir:
    test_env = Path(tmpdir) / "isolated_env"

    with OpencodeServer(
        target_dir=test_env,
        # ... other params ...
    ) as server:
        # Run tests in complete isolation
        pass
```

## Verification

The library includes comprehensive tests to verify isolation:

```bash
# Run isolation tests
uv run pytest tests/test_isolation.py -v
```

Tests verify:
- All directories are created in isolation
- Environment variables are properly isolated
- No leakage of parent process environment
- Auth files are properly isolated with correct permissions
- Attempts to use home directory are rejected
- File descriptors are not inherited

## Security Notes

1. **Auth File**: Your auth.json is copied (not linked) into the isolated environment with `0600` permissions (owner read/write only).

2. **Binary Path**: The opencode binary path is the only external reference, but it's executed in the isolated environment.

3. **Network**: Network access is NOT restricted - the server can still make API calls to AI providers.

4. **Filesystem**: The server can only read/write within its target_dir.

## FAQ

**Q: Can the server access my SSH keys?**
A: No. The HOME directory is overridden to point to an isolated directory.

**Q: Can the server see my environment variables?**
A: No. Only a minimal set of safe environment variables are passed.

**Q: Can the server access my real .config directory?**
A: No. XDG_CONFIG_HOME points to the isolated directory.

**Q: What if I accidentally use my home directory as target_dir?**
A: The library will raise an error and refuse to run.

**Q: Is it safe to run untrusted code with this?**
A: This library provides filesystem and environment isolation only. It does not provide network isolation or system call filtering. Use additional sandboxing if running untrusted code.
