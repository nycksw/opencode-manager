"""OpencodeServer - High-level server orchestration and management."""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import List, Optional

from opencode_ai import Opencode

from .constants import DEFAULT_STARTUP_TIMEOUT, HEALTH_CHECK_INTERVAL
from .isolation import IsolationManager
from .models import ModelSelector
from .process import ProcessManager
from .session import Session
from .session_manager import SessionManager


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
        startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
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
        self.target_dir = target_dir.resolve()
        self.auth_file = auth_file.resolve()
        self.opencode_config_dir = opencode_config_dir.resolve()
        self.opencode_json = opencode_json.resolve()
        self.opencode_binary = opencode_binary.resolve()

        # Store configuration
        self.port = port
        self.hostname = hostname
        self.delete_target_dir_on_exit = delete_target_dir_on_exit
        self.startup_timeout = startup_timeout

        # Setup logging
        self._setup_logging()

        # Check version compatibility
        self._check_version_compatibility()

        # Initialize components
        self.isolation_manager = IsolationManager(self.target_dir, self.logger)
        self.process_manager = ProcessManager(
            self.opencode_binary,
            self.target_dir,
            self.logger,
            self.startup_timeout,
        )
        self.model_selector = ModelSelector(
            self.auth_file, self.opencode_json, self.logger
        )

        # Runtime state
        self._client: Optional[Opencode] = None
        self._session_manager: Optional[SessionManager] = None

    def _setup_logging(self) -> None:
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
        self.logger.addHandler(console_handler)

    def _check_version_compatibility(self) -> None:
        """Check opencode binary version against compatibility configuration."""
        # Load version configuration
        config_path = Path(__file__).parent.parent.parent / "opencode_versions.json"
        if not config_path.exists():
            self.logger.warning(
                "Version configuration not found. Skipping compatibility check."
            )
            return

        try:
            with open(config_path) as f:
                version_config = json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load version config: {e}")
            return

        # Get binary version
        try:
            result = subprocess.run(
                [str(self.opencode_binary), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            binary_version = result.stdout.strip()
        except Exception as e:
            self.logger.warning(f"Failed to check opencode version: {e}")
            return

        # Check compatibility
        recommended = version_config.get("recommended_opencode_version")
        current_sdk = version_config.get("current_sdk_version", "unknown")

        if binary_version == recommended:
            self.logger.info(
                f"Using opencode v{binary_version} "
                f"(recommended for SDK {current_sdk})"
            )
        elif binary_version.startswith("0.5."):
            self.logger.info(
                f"Using opencode v{binary_version} "
                f"(compatible with SDK {current_sdk})"
            )
        elif binary_version.startswith("0.6."):
            self.logger.warning(
                f"Using opencode v{binary_version} - "
                f"POTENTIAL COMPATIBILITY ISSUES\n"
                f"  SDK {current_sdk} was built for opencode v{recommended}\n"
                f"  Version 0.6.0+ has breaking API changes:\n"
                f"  - Removed /app endpoints\n"
                f"  - Changed session.chat to session.prompt\n"
                f"  - Changed model parameter structure\n"
                f"  Consider downgrading to v{recommended}"
            )
        else:
            self.logger.warning(
                f"Using opencode v{binary_version} - untested version\n"
                f"  Recommended: v{recommended} for SDK {current_sdk}"
            )

    def _add_file_logging(self) -> None:
        """Add file logging after target_dir is created."""
        log_file = self.target_dir / "opencode_server.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _wait_for_ready(self) -> None:
        """Wait for server to be ready by polling health endpoint.

        Raises:
            TimeoutError: If server doesn't become ready within timeout
        """
        # Wait for URL discovery
        base_url = self.process_manager.wait_for_url()

        # Create client with discovered URL
        self._client = Opencode(base_url=base_url)

        # Poll health endpoint
        self.logger.info("Waiting for server to be ready...")
        start_time = time.time()

        while time.time() - start_time < self.startup_timeout:
            try:
                # Use session list as health check - it's a simple endpoint
                # that should always work if the server is up
                sessions = self._client.session.list()
                if sessions is not None:  # Empty list is fine, just need a response
                    self.logger.info("Server ready!")
                    return
            except Exception as e:
                self.logger.debug(f"Health check failed: {e}")
                time.sleep(HEALTH_CHECK_INTERVAL)

        raise TimeoutError(
            f"Server did not become ready within " f"{self.startup_timeout} seconds"
        )

    def __enter__(self):
        """Enter context manager - setup and start server."""
        # Setup isolated environment
        self.isolation_manager.setup_environment(
            self.auth_file,
            self.opencode_config_dir,
            self.opencode_json,
        )

        # Add file logging after directories are created
        self._add_file_logging()

        # Start server process
        env = self.isolation_manager.get_environment()
        self.process_manager.start(env, self.port, self.hostname)

        # Wait for server to be ready
        self._wait_for_ready()

        # Initialize session manager
        if self._client:
            self._session_manager = SessionManager(
                self._client, self.model_selector, self.logger
            )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - shutdown and optionally cleanup."""
        # Shutdown server
        self.process_manager.shutdown()

        # Clean up environment
        self.isolation_manager.cleanup(preserve=not self.delete_target_dir_on_exit)

    # Public properties

    @property
    def base_url(self) -> Optional[str]:
        """Get the server's base URL."""
        return self.process_manager.base_url

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self.process_manager.is_running

    # Session Management Methods (delegate to SessionManager)

    def create_session(self, title: Optional[str] = None) -> Session:
        """Create a new session.

        Args:
            title: Optional title for the session

        Returns:
            New Session instance

        Raises:
            RuntimeError: If server not started
            SessionError: If creation fails
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.create_session(title)

    def list_sessions(self) -> List[Session]:
        """List all sessions.

        Returns:
            List of Session instances

        Raises:
            RuntimeError: If server not started
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.list_sessions()

    def get_session(self, session_id: str) -> Session:
        """Get a specific session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session instance

        Raises:
            RuntimeError: If server not started
            SessionNotFoundError: If session doesn't exist
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.get_session(session_id)

    def update_session(self, session_id: str, title: str) -> None:
        """Update session title.

        Args:
            session_id: Session ID to update
            title: New title for the session

        Raises:
            RuntimeError: If server not started
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.update_session(session_id, title)

    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session ID to delete

        Raises:
            RuntimeError: If server not started
            SessionError: If deletion fails
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.delete_session(session_id)

    def abort_session(self, session_id: str):
        """Abort a session.

        Args:
            session_id: Session ID to abort

        Returns:
            Abort result

        Raises:
            RuntimeError: If server not started
            SessionError: If abort fails
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.abort_session(session_id)

    def abort_all_sessions(self) -> None:
        """Emergency kill switch - abort all sessions.

        Raises:
            RuntimeError: If server not started
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.abort_all_sessions()

    def send_message(self, session_id: str, message: str) -> Optional[str]:
        """Send a message to a session and get response.

        Args:
            session_id: Session ID to send message to
            message: Message text to send

        Returns:
            Assistant's response text, or None if no response

        Raises:
            RuntimeError: If server not started
            SessionError: If message sending fails
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.send_message(session_id, message)

    def get_messages(self, session_id: str) -> List:
        """Get all messages from a session.

        Args:
            session_id: Session ID to get messages from

        Returns:
            List of message objects

        Raises:
            RuntimeError: If server not started
            SessionError: If retrieval fails
        """
        if not self._session_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )
        return self._session_manager.get_messages(session_id)

    def get_opencode_version(self) -> str:
        """Get version of opencode binary in isolated environment.

        Returns:
            Version string (e.g., "0.6.3")

        Raises:
            RuntimeError: If server not started
        """
        if not self.isolation_manager:
            raise RuntimeError(
                "Server not started. Use context manager or call __enter__"
            )

        if not hasattr(self, "_version"):
            # Run version check with isolation environment vars
            env = self.isolation_manager.get_environment()
            result = subprocess.run(
                [str(self.opencode_binary), "--version"],
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Output is just "0.6.3" - clean version string
            self._version = result.stdout.strip()
        return self._version
