"""OpencodeServer - High-level server orchestration and management."""

import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from queue import Queue
from typing import List, Optional, Tuple

from opencode_ai import Opencode
from opencode_ai.types import TextPartInputParam

from .session import Session


class OpencodeServer:
    """Manages an isolated opencode server instance with full lifecycle."""

    def __init__(
        self,
        target_dir: Path,
        auth_file: Path,
        opencode_config_dir: Path,
        opencode_json: Path,
        opencode_binary: Path,
        port: Optional[int] = None,
        hostname: Optional[str] = None,
        delete_target_dir_on_exit: bool = False,
        startup_timeout: float = 10.0,
    ):
        """Initialize OpencodeServer with required configuration.

        Args:
            target_dir: Directory where isolated environment will be created
            auth_file: Path to auth.json file to copy
            opencode_config_dir: Path to .opencode directory to copy
            opencode_json: Path to opencode.json configuration file
            opencode_binary: Full path to opencode executable
            port: Optional specific port to bind to
            hostname: Optional specific hostname to bind to
            delete_target_dir_on_exit: Whether to remove target_dir on exit
            startup_timeout: Maximum seconds to wait for server startup

        Raises:
            FileNotFoundError: If any required files don't exist
            FileExistsError: If target_dir already exists
            ValueError: If opencode_binary is not executable
        """
        # Convert all paths to absolute
        target_dir = target_dir.resolve()
        auth_file = auth_file.resolve()
        opencode_config_dir = opencode_config_dir.resolve()
        opencode_json = opencode_json.resolve()
        opencode_binary = opencode_binary.resolve()

        # Validate inputs upfront
        if not auth_file.exists():
            raise FileNotFoundError(f"auth_file not found: {auth_file}")
        if not opencode_config_dir.is_dir():
            raise NotADirectoryError(
                f"opencode_config_dir not found: {opencode_config_dir}"
            )
        if not opencode_json.exists():
            raise FileNotFoundError(f"opencode_json not found: {opencode_json}")
        if not opencode_binary.exists():
            raise FileNotFoundError(
                f"opencode_binary not found: {opencode_binary}"
            )
        if not os.access(opencode_binary, os.X_OK):
            raise ValueError(
                f"opencode_binary not executable: {opencode_binary}"
            )
        if target_dir.exists():
            raise FileExistsError(f"target_dir already exists: {target_dir}")

        # Store configuration
        self.target_dir = target_dir
        self.auth_file = auth_file
        self.opencode_config_dir = opencode_config_dir
        self.opencode_json = opencode_json
        self.opencode_binary = opencode_binary
        self.port = port
        self.hostname = hostname
        self.delete_target_dir_on_exit = delete_target_dir_on_exit
        self.startup_timeout = startup_timeout

        # Runtime state
        self._process = None
        self._client = None
        self.base_url = None
        self._stdout_queue = Queue()
        self._stderr_queue = Queue()
        self._stdout_thread = None
        self._stderr_thread = None

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging to both file and console."""
        self.logger = logging.getLogger(f"OpencodeServer[{id(self)}]")
        self.logger.setLevel(logging.DEBUG)

        # Console handler - INFO and above
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)

        # File handler will be added after target_dir is created
        self.logger.addHandler(console_handler)

    def _add_file_logging(self):
        """Add file logging after target_dir is created."""
        log_file = self.target_dir / "opencode_server.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _setup_environment(self):
        """Create isolated XDG directories and copy required files.

        This creates a completely isolated environment to ensure the opencode
        server NEVER touches the user's real XDG directories or home directory.
        """
        self.logger.info(
            f"Setting up isolated environment in {self.target_dir}"
        )

        # Create comprehensive isolated directory structure
        xdg_dirs = {
            "config": self.target_dir / ".oc" / "config",
            "data": self.target_dir / ".oc" / "data",
            "state": self.target_dir / ".oc" / "state",
            "cache": self.target_dir / ".cache",
            "runtime": self.target_dir / ".runtime",
        }

        # Additional isolation directories
        isolated_dirs = {
            "home": self.target_dir / ".home",
            "tmp": self.target_dir / ".tmp",
        }

        # Create all directories
        for name, path in {**xdg_dirs, **isolated_dirs}.items():
            path.mkdir(parents=True, exist_ok=False)
            self.logger.debug(f"Created isolated {name} directory: {path}")

            # Set appropriate permissions for runtime dir
            if name == "runtime":
                os.chmod(path, 0o700)  # Only owner can access

        # Now add file logging
        self._add_file_logging()

        # Copy auth.json with restricted permissions
        auth_dest = xdg_dirs["data"] / "opencode" / "auth.json"
        auth_dest.parent.mkdir(parents=True)
        shutil.copy2(self.auth_file, auth_dest)
        os.chmod(auth_dest, 0o600)  # Owner read/write only
        self.logger.info("Copied auth.json with 0600 permissions")

        # Copy .opencode directory
        opencode_dest = self.target_dir / ".opencode"
        shutil.copytree(self.opencode_config_dir, opencode_dest)
        self.logger.info("Copied .opencode directory")

        # Copy opencode.json
        opencode_json_dest = self.target_dir / "opencode.json"
        shutil.copy2(self.opencode_json, opencode_json_dest)
        self.logger.info("Copied opencode.json")

        # Store paths for later use
        self.xdg_dirs = xdg_dirs
        self.isolated_dirs = isolated_dirs

        # Verify isolation - ensure we're not in user's real directories
        self._verify_isolation()

    def _verify_isolation(self):
        """Verify that the isolated environment is properly set up.

        Ensures that:
        1. Target directory is not in user's home
        2. All paths are under target_dir
        3. No accidental use of real XDG directories
        """
        real_home = Path.home()
        real_xdg_config = Path(
            os.environ.get("XDG_CONFIG_HOME", real_home / ".config")
        )
        real_xdg_data = Path(
            os.environ.get("XDG_DATA_HOME", real_home / ".local" / "share")
        )

        # Check that target_dir is not in any sensitive location
        sensitive_paths = [
            real_home / ".config",
            real_home / ".local",
            real_home / ".cache",
            real_xdg_config,
            real_xdg_data,
        ]

        for sensitive_path in sensitive_paths:
            try:
                if sensitive_path.exists() and self.target_dir.is_relative_to(
                    sensitive_path
                ):
                    raise ValueError(
                        f"ISOLATION VIOLATION: Target directory "
                        f"{self.target_dir} is inside sensitive path "
                        f"{sensitive_path}"
                    )
            except (ValueError, TypeError):
                # is_relative_to might not exist in older Python,
                # use string comparison
                if str(self.target_dir).startswith(str(sensitive_path)):
                    raise ValueError(
                        f"ISOLATION VIOLATION: Target directory "
                        f"{self.target_dir} is inside sensitive path "
                        f"{sensitive_path}"
                    )

        # Verify all our directories are under target_dir
        all_dirs = {**self.xdg_dirs, **self.isolated_dirs}
        for name, path in all_dirs.items():
            try:
                if not path.is_relative_to(self.target_dir):
                    raise ValueError(
                        f"ISOLATION VIOLATION: {name} directory {path} "
                        f"is outside target directory {self.target_dir}"
                    )
            except (AttributeError, TypeError):
                # is_relative_to might not exist in older Python
                if not str(path).startswith(str(self.target_dir)):
                    raise ValueError(
                        f"ISOLATION VIOLATION: {name} directory {path} "
                        f"is outside target directory {self.target_dir}"
                    )

        self.logger.info(
            "Isolation verification passed - "
            "all directories are properly isolated"
        )

    def _read_output(self, pipe, queue, name):
        """Read output from a pipe and put it in a queue."""
        try:
            for line in iter(pipe.readline, ""):
                if not line:
                    break
                line = line.rstrip("\n")
                queue.put((name, line))

                # Log the output
                if name == "stdout":
                    self.logger.debug(f"[STDOUT] {line}")
                else:
                    self.logger.debug(f"[STDERR] {line}")

                # Check for server URL in stdout
                if name == "stdout" and not self.base_url:
                    # Try multiple patterns for URL discovery
                    patterns = [
                        r"Server running at (https?://[^\s]+)",
                        r"listening on (https?://[^\s]+)",
                        r"server listening on (https?://[^\s]+)",
                        r"(https?://\d+\.\d+\.\d+\.\d+:\d+)",
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            self.base_url = match.group(1)
                            self.logger.info(
                                f"Discovered server URL: {self.base_url}"
                            )
                            break
        except Exception as e:
            self.logger.error(f"Error reading {name}: {e}")
        finally:
            pipe.close()

    def _start_server(self):
        """Start the opencode server process with complete isolation.

        Creates a minimal, isolated environment to ensure the server process
        cannot access the user's real home directory or XDG directories.
        """
        self.logger.info("Starting opencode server with enhanced isolation")

        # Build completely isolated environment (NOT a copy of os.environ)
        # This ensures NO leakage of user environment variables
        env = {
            # XDG Base Directory Specification - all isolated
            "XDG_CONFIG_HOME": str(self.xdg_dirs["config"]),
            "XDG_DATA_HOME": str(self.xdg_dirs["data"]),
            "XDG_STATE_HOME": str(self.xdg_dirs["state"]),
            "XDG_CACHE_HOME": str(self.xdg_dirs["cache"]),
            "XDG_RUNTIME_DIR": str(self.xdg_dirs["runtime"]),
            # Override HOME to prevent ANY access to real home directory
            "HOME": str(self.isolated_dirs["home"]),
            # Isolated temp directories
            "TMPDIR": str(self.isolated_dirs["tmp"]),
            "TEMP": str(self.isolated_dirs["tmp"]),
            "TMP": str(self.isolated_dirs["tmp"]),
            # Minimal PATH (only essential system binaries)
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            # Basic locale settings
            "LANG": os.environ.get("LANG", "en_US.UTF-8"),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            # Terminal type (if needed for output)
            "TERM": os.environ.get("TERM", "xterm-256color"),
            # User info (safe to include, just informational)
            "USER": os.environ.get("USER", "opencode"),
            "LOGNAME": os.environ.get("LOGNAME", "opencode"),
        }

        # Log isolation info in debug mode
        self.logger.debug("Isolation environment configured:")
        self.logger.debug(f"  HOME={env['HOME']}")
        self.logger.debug(f"  XDG_CONFIG_HOME={env['XDG_CONFIG_HOME']}")
        self.logger.debug(f"  XDG_DATA_HOME={env['XDG_DATA_HOME']}")
        self.logger.debug(f"  TMPDIR={env['TMPDIR']}")

        # Build command
        cmd = [str(self.opencode_binary), "serve"]
        if self.hostname is not None:
            cmd.extend(["--hostname", self.hostname])
        if self.port is not None:
            cmd.extend(["--port", str(self.port)])

        self.logger.info(f"Command: {' '.join(cmd)}")
        self.logger.debug(f"Working directory: {self.target_dir}")

        # Start process with complete isolation
        self._process = subprocess.Popen(
            cmd,
            cwd=self.target_dir,
            env=env,  # Use ONLY our minimal environment
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            close_fds=True,  # Don't inherit any file descriptors
        )

        # Start threads to read output
        self._stdout_thread = threading.Thread(
            target=self._read_output,
            args=(self._process.stdout, self._stdout_queue, "stdout"),
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._read_output,
            args=(self._process.stderr, self._stderr_queue, "stderr"),
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

        self.logger.info(f"Server process started with PID {self._process.pid}")

    def _wait_for_ready(self):
        """Wait for server to be ready by polling health endpoint."""
        start_time = time.time()

        # First wait for URL discovery
        while not self.base_url:
            if time.time() - start_time > self.startup_timeout:
                raise TimeoutError(
                    f"Server did not report URL within "
                    f"{self.startup_timeout} seconds"
                )
            time.sleep(0.1)

        # Create client with discovered URL
        self._client = Opencode(base_url=self.base_url)

        # Poll health endpoint
        self.logger.info("Waiting for server to be ready...")
        while time.time() - start_time < self.startup_timeout:
            try:
                # Try to get app info as health check
                app_info = self._client.app.get()
                if app_info:
                    # App object may not have version attribute
                    version = getattr(app_info, "version", "unknown")
                    self.logger.info(f"Server ready! Version: {version}")
                    return
            except Exception as e:
                self.logger.debug(f"Health check failed: {e}")
                time.sleep(0.5)

        raise TimeoutError(
            f"Server did not become ready within {self.startup_timeout} seconds"
        )

    def _shutdown_server(self):
        """Gracefully shutdown the server."""
        if not self._process:
            return

        self.logger.info("Shutting down server...")

        # Try graceful termination first
        self._process.terminate()
        try:
            self._process.wait(timeout=5)
            self.logger.info("Server terminated gracefully")
        except subprocess.TimeoutExpired:
            self.logger.warning("Server did not terminate, killing...")
            self._process.kill()
            self._process.wait()
            self.logger.info("Server killed")

        self._process = None

    def __enter__(self):
        """Enter context manager - setup and start server."""
        self._setup_environment()
        self._start_server()
        self._wait_for_ready()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - shutdown and optionally cleanup."""
        self._shutdown_server()

        if self.delete_target_dir_on_exit:
            self.logger.info(f"Removing target directory: {self.target_dir}")
            shutil.rmtree(self.target_dir)
        else:
            self.logger.info(f"Preserving target directory: {self.target_dir}")

    # Session Management Methods

    def create_session(self, title: Optional[str] = None) -> Session:
        """Create a new session."""
        if not self._client:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )

        # The SDK doesn't expose title as a parameter, but we can pass it
        # via extra_body
        body = {}
        if title:
            body["title"] = title

        session_data = self._client.session.create(
            extra_body=body if body else None
        )
        if not session_data:
            raise RuntimeError("Failed to create session")
        self.logger.info(f"Created session: {session_data.id}")
        return Session(self, session_data)

    def list_sessions(self) -> List[Session]:
        """List all sessions."""
        if not self._client:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        sessions_data = self._client.session.list()
        if sessions_data is None:
            return []
        return [Session(self, s) for s in sessions_data]

    def get_session(self, session_id: str) -> Session:
        """Get a specific session by filtering the list."""
        if not self._client:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        sessions_data = self._client.session.list()
        for session_data in sessions_data:
            if session_data.id == session_id:
                return Session(self, session_data)
        raise ValueError(f"Session not found: {session_id}")

    def update_session(self, session_id: str, title: str):
        """Update session title."""
        # SST SDK doesn't have session update, so we'll skip this for now
        self.logger.warning("Session update not supported in SST SDK")
        return None

    def delete_session(self, session_id: str):
        """Delete a session."""
        if not self._client:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        self._client.session.delete(id=session_id)
        self.logger.info(f"Deleted session: {session_id}")

    def abort_session(self, session_id: str):
        """Abort a session."""
        if not self._client:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        result = self._client.session.abort(id=session_id)
        self.logger.info(f"Aborted session: {session_id}")
        return result

    def abort_all_sessions(self):
        """Emergency kill switch - abort all sessions."""
        self.logger.warning("Aborting all sessions!")
        sessions = self.list_sessions()
        for session in sessions:
            try:
                self.abort_session(session.id)
            except Exception as e:
                self.logger.error(f"Failed to abort session {session.id}: {e}")

    # Chat Methods

    def _get_default_model(self) -> Tuple[str, str]:
        """Get provider/model from config or use cheap default."""
        import json

        # Check opencode.json for explicit model
        try:
            with open(self.opencode_json) as f:
                if model := json.load(f).get("model", "").split("/"):
                    if len(model) == 2:
                        return tuple(model)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # Use first available cheap model
        CHEAP = {
            "anthropic": "claude-3-5-haiku-20241022",
            "openai": "gpt-4o-mini",
            "google": "gemini-1.5-flash",
        }

        with open(self.auth_file) as f:
            auth = set(json.load(f).keys())

        if match := next((p for p in CHEAP if p in auth), None):
            self.logger.info(f"Using {match}/{CHEAP[match]} (cheap model)")
            return match, CHEAP[match]

        # Fallback
        return next(iter(auth), "anthropic"), "claude-3-5-haiku-20241022"

    def send_message(self, session_id: str, message: str) -> Optional[str]:
        """Send a message to a session and get response."""
        if not self._client:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )

        provider_id, model_id = self._get_default_model()

        # Send message using SST SDK
        response = self._client.session.chat(
            id=session_id,
            provider_id=provider_id,
            model_id=model_id,
            parts=[TextPartInputParam(type="text", text=message)],
        )

        # Extract text from response
        if response:
            # Handle response whether it has parts attribute or not
            parts = getattr(response, "parts", None)
            if parts:
                text_parts = []
                for part in parts:
                    # Parts can be dicts or objects
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part["text"])
                    elif hasattr(part, "text"):
                        text_parts.append(getattr(part, "text"))
                return "\n".join(text_parts) if text_parts else None
        return None

    def get_messages(self, session_id: str):
        """Get all messages from a session."""
        if not self._client:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        messages = self._client.session.messages(id=session_id)
        return messages or []
