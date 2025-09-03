"""Isolation management for opencode server instances."""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict

from .constants import AUTH_FILE_PERMISSIONS, RUNTIME_DIR_PERMISSIONS
from .exceptions import ConfigurationError, IsolationError


class IsolationManager:
    """Manages XDG directory isolation for opencode server instances."""

    def __init__(self, target_dir: Path, logger: logging.Logger):
        """Initialize the isolation manager.

        Args:
            target_dir: Directory where isolated environment will be created
            logger: Logger instance for output

        Raises:
            FileExistsError: If target_dir already exists
        """
        self.target_dir = target_dir.resolve()
        self.logger = logger

        if self.target_dir.exists():
            raise FileExistsError(f"Target directory already exists: {self.target_dir}")

        self.xdg_dirs: Dict[str, Path] = {}
        self.isolated_dirs: Dict[str, Path] = {}

    def setup_environment(
        self,
        auth_file: Path,
        opencode_config_dir: Path,
        opencode_json: Path,
    ) -> None:
        """Create isolated XDG directories and copy required files.

        Args:
            auth_file: Path to auth.json file to copy
            opencode_config_dir: Path to .opencode directory to copy
            opencode_json: Path to opencode.json configuration file

        Raises:
            IsolationError: If isolation requirements are violated
            ConfigurationError: If required files don't exist
        """
        # Validate inputs
        if not auth_file.exists():
            raise ConfigurationError(f"Auth file not found: {auth_file}")
        if not opencode_config_dir.is_dir():
            raise ConfigurationError(
                f"Config directory not found: {opencode_config_dir}"
            )
        if not opencode_json.exists():
            raise ConfigurationError(f"Config file not found: {opencode_json}")

        self.logger.info(f"Setting up isolated environment in {self.target_dir}")

        # Create comprehensive isolated directory structure
        self.xdg_dirs = {
            "config": self.target_dir / ".oc" / "config",
            "data": self.target_dir / ".oc" / "data",
            "cache": self.target_dir / ".cache",
            "runtime": self.target_dir / ".runtime",
        }

        # Additional isolation directories
        self.isolated_dirs = {
            "home": self.target_dir / ".home",
            "tmp": self.target_dir / ".tmp",
        }

        # Create all directories
        all_dirs = {**self.xdg_dirs, **self.isolated_dirs}
        for name, path in all_dirs.items():
            path.mkdir(parents=True, exist_ok=False)
            self.logger.debug(f"Created isolated {name} directory: {path}")

            # Set appropriate permissions for runtime dir
            if name == "runtime":
                os.chmod(path, RUNTIME_DIR_PERMISSIONS)

        # Copy auth.json with restricted permissions
        auth_dest = self.xdg_dirs["data"] / "opencode" / "auth.json"
        auth_dest.parent.mkdir(parents=True)
        shutil.copy2(auth_file, auth_dest)
        os.chmod(auth_dest, AUTH_FILE_PERMISSIONS)
        self.logger.info(
            f"Copied auth.json with {oct(AUTH_FILE_PERMISSIONS)} permissions"
        )

        # Copy .opencode directory
        opencode_dest = self.target_dir / ".opencode"
        shutil.copytree(opencode_config_dir, opencode_dest)
        self.logger.info("Copied .opencode directory")

        # Copy opencode.json
        opencode_json_dest = self.target_dir / "opencode.json"
        shutil.copy2(opencode_json, opencode_json_dest)
        self.logger.info("Copied opencode.json")

        # Verify isolation
        self._verify_isolation()

    def _verify_isolation(self) -> None:
        """Verify that the isolated environment is properly set up.

        Raises:
            IsolationError: If isolation requirements are violated
        """
        real_home = Path.home()
        real_xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", real_home / ".config"))
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
            if sensitive_path.exists() and self.target_dir.is_relative_to(
                sensitive_path
            ):
                raise IsolationError(
                    f"ISOLATION VIOLATION: Target directory "
                    f"{self.target_dir} is inside sensitive path "
                    f"{sensitive_path}"
                )

        # Verify all our directories are under target_dir
        all_dirs = {**self.xdg_dirs, **self.isolated_dirs}
        for name, path in all_dirs.items():
            if not path.is_relative_to(self.target_dir):
                raise IsolationError(
                    f"ISOLATION VIOLATION: {name} directory {path} "
                    f"is outside target directory {self.target_dir}"
                )

        self.logger.info(
            "Isolation verification passed - " "all directories are properly isolated"
        )

    def get_environment(self) -> Dict[str, str]:
        """Get the isolated environment variables.

        Returns:
            Dictionary of environment variables for the isolated process
        """
        from .constants import (
            DEFAULT_LOCALE,
            DEFAULT_TERM,
            DEFAULT_USER,
            SYSTEM_PATH,
        )

        return {
            # XDG Base Directory Specification - all isolated
            "XDG_CONFIG_HOME": str(self.xdg_dirs["config"]),
            "XDG_DATA_HOME": str(self.xdg_dirs["data"]),
            "XDG_CACHE_HOME": str(self.xdg_dirs["cache"]),
            "XDG_RUNTIME_DIR": str(self.xdg_dirs["runtime"]),
            # Override HOME to prevent ANY access to real home directory
            "HOME": str(self.isolated_dirs["home"]),
            # Isolated temp directories
            "TMPDIR": str(self.isolated_dirs["tmp"]),
            "TEMP": str(self.isolated_dirs["tmp"]),
            "TMP": str(self.isolated_dirs["tmp"]),
            # Minimal PATH (only essential system binaries)
            "PATH": SYSTEM_PATH,
            # Basic locale settings
            "LANG": os.environ.get("LANG", DEFAULT_LOCALE),
            "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
            # Terminal type (if needed for output)
            "TERM": os.environ.get("TERM", DEFAULT_TERM),
            # User info (safe to include, just informational)
            "USER": os.environ.get("USER", DEFAULT_USER),
            "LOGNAME": os.environ.get("LOGNAME", DEFAULT_USER),
        }

    def cleanup(self, preserve: bool = False) -> None:
        """Clean up the isolated environment.

        Args:
            preserve: If True, preserve the target directory
        """
        if preserve:
            self.logger.info(f"Preserving target directory: {self.target_dir}")
        else:
            self.logger.info(f"Removing target directory: {self.target_dir}")
            shutil.rmtree(self.target_dir)
