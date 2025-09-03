"""Process management for opencode server instances."""

import logging
import re
import select
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from .constants import (
    PROCESS_TERMINATION_TIMEOUT,
    URL_DISCOVERY_POLL_INTERVAL,
    URL_PATTERNS,
)
from .exceptions import ServerStartupError


class ProcessManager:
    """Manages the opencode server subprocess lifecycle."""

    def __init__(
        self,
        opencode_binary: Path,
        target_dir: Path,
        logger: logging.Logger,
        startup_timeout: float,
    ):
        """Initialize the process manager.

        Args:
            opencode_binary: Full path to opencode executable
            target_dir: Working directory for the server
            logger: Logger instance for output
            startup_timeout: Maximum seconds to wait for server startup

        Raises:
            FileNotFoundError: If opencode_binary doesn't exist
            ValueError: If opencode_binary is not executable
        """
        self.opencode_binary = opencode_binary.resolve()
        self.target_dir = target_dir.resolve()
        self.logger = logger
        self.startup_timeout = startup_timeout

        # Validate binary
        if not self.opencode_binary.exists():
            raise FileNotFoundError(
                f"opencode binary not found: {self.opencode_binary}"
            )
        if not self.opencode_binary.is_file():
            raise ValueError(f"opencode binary is not a file: {self.opencode_binary}")
        if not self.opencode_binary.stat().st_mode & 0o111:
            raise ValueError(f"opencode binary not executable: {self.opencode_binary}")

        # Runtime state
        self._process: Optional[subprocess.Popen] = None
        self.base_url: Optional[str] = None

    def start(
        self,
        env: Dict[str, str],
        port: Optional[int] = None,
        hostname: Optional[str] = None,
    ) -> None:
        """Start the opencode server process.

        Args:
            env: Environment variables for the process
            port: Optional specific port to bind to
            hostname: Optional specific hostname to bind to

        Raises:
            ServerStartupError: If the server fails to start
        """
        if self._process and self._process.poll() is None:
            raise ServerStartupError("Server is already running")

        self.logger.info("Starting opencode server process")

        # Build command
        cmd = [str(self.opencode_binary), "serve"]
        if hostname is not None:
            cmd.extend(["--hostname", hostname])
        if port is not None:
            cmd.extend(["--port", str(port)])

        self.logger.info(f"Command: {' '.join(cmd)}")
        self.logger.debug(f"Working directory: {self.target_dir}")

        # Start process
        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=self.target_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                close_fds=True,  # Don't inherit any file descriptors
            )
        except Exception as e:
            raise ServerStartupError(f"Failed to start server: {e}")

        self.logger.info(f"Server process started with PID {self._process.pid}")

    def wait_for_url(self) -> str:
        """Wait for the server to report its URL.

        Returns:
            The server's base URL

        Raises:
            TimeoutError: If URL is not discovered within timeout
            ServerStartupError: If server process not started or dies
        """
        if not self._process or not self._process.stdout:
            raise ServerStartupError("Server process not started")

        start_time = time.time()

        while time.time() - start_time < self.startup_timeout:
            # Use select for non-blocking read with timeout
            ready, _, _ = select.select(
                [self._process.stdout], [], [], URL_DISCOVERY_POLL_INTERVAL
            )

            if ready:
                line = self._process.stdout.readline()
                if not line:  # EOF
                    break

                line = line.rstrip("\n")
                self.logger.debug(f"[STDOUT] {line}")

                # Check for URL pattern
                for pattern in URL_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        url = match.group(1)
                        self.base_url = url
                        self.logger.info(f"Discovered server URL: {url}")
                        return url

        # Check if process died
        if self._process.poll() is not None:
            # Try to get error output
            stderr_output = ""
            if self._process.stderr:
                stderr_output = self._process.stderr.read()
            raise ServerStartupError(
                f"Server process died during startup. "
                f"Exit code: {self._process.returncode}. "
                f"Stderr: {stderr_output}"
            )

        raise TimeoutError(
            f"Server did not report URL within {self.startup_timeout} seconds"
        )

    def get_output(self, limit: int = 100) -> List[str]:
        """Get recent output from the server (non-blocking).

        Args:
            limit: Maximum number of lines to read

        Returns:
            List of output lines from the server
        """
        if not self._process:
            return []

        output = []

        # Check both stdout and stderr
        streams = []
        if self._process.stdout:
            streams.append(self._process.stdout)
        if self._process.stderr:
            streams.append(self._process.stderr)

        if not streams:
            return []

        while limit > 0:
            # Non-blocking check for available data
            ready, _, _ = select.select(streams, [], [], 0)
            if not ready:
                break

            for stream in ready:
                line = stream.readline()
                if line:
                    output.append(line.rstrip("\n"))
                    limit -= 1
                    if limit <= 0:
                        break

        return output

    def shutdown(self) -> None:
        """Gracefully shutdown the server process."""
        if not self._process:
            return

        self.logger.info("Shutting down server...")

        # Try graceful termination first
        self._process.terminate()
        try:
            self._process.wait(timeout=PROCESS_TERMINATION_TIMEOUT)
            self.logger.info("Server terminated gracefully")
        except subprocess.TimeoutExpired:
            self.logger.warning("Server did not terminate, killing...")
            self._process.kill()
            self._process.wait()
            self.logger.info("Server killed")

        self._process = None
        self.base_url = None

    @property
    def is_running(self) -> bool:
        """Check if the server process is running."""
        return self._process is not None and self._process.poll() is None
