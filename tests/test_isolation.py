"""Tests for XDG directory isolation in OpencodeServer.

These tests verify that OpencodeServer NEVER touches the user's real
XDG directories or home directory, ensuring complete isolation.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from opencode_manager import OpencodeServer


class TestXDGIsolation:
    """Test that OpencodeServer provides complete XDG isolation."""

    @pytest.fixture
    def mock_paths(self, tmp_path):
        """Create mock paths for testing."""
        return {
            "target_dir": tmp_path / "test_env",
            "auth_file": tmp_path / "auth.json",
            "opencode_config_dir": tmp_path / ".opencode",
            "opencode_json": tmp_path / "opencode.json",
            "opencode_binary": tmp_path / "opencode",
        }

    @pytest.fixture
    def setup_mock_files(self, mock_paths):
        """Set up mock files."""
        mock_paths["auth_file"].write_text("{}")
        mock_paths["opencode_config_dir"].mkdir()
        mock_paths["opencode_json"].write_text("{}")
        mock_paths["opencode_binary"].touch()
        mock_paths["opencode_binary"].chmod(0o755)

    def test_creates_all_isolation_directories(
        self, mock_paths, setup_mock_files
    ):
        """Test that all isolation directories are created."""
        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
        )

        server._setup_environment()

        # Check XDG directories
        assert (mock_paths["target_dir"] / ".oc" / "config").exists()
        assert (mock_paths["target_dir"] / ".oc" / "data").exists()
        assert (mock_paths["target_dir"] / ".oc" / "state").exists()
        assert (mock_paths["target_dir"] / ".cache").exists()
        assert (mock_paths["target_dir"] / ".runtime").exists()

        # Check additional isolation directories
        assert (mock_paths["target_dir"] / ".home").exists()
        assert (mock_paths["target_dir"] / ".tmp").exists()

        # Verify runtime dir has restricted permissions
        runtime_dir = mock_paths["target_dir"] / ".runtime"
        assert oct(runtime_dir.stat().st_mode)[-3:] == "700"

    def test_isolation_verification_prevents_home_directory_usage(
        self, tmp_path
    ):
        """Test that server refuses to use real home directory as target."""
        # Try to use a subdirectory of home - use a unique name to avoid
        # conflicts
        import uuid

        home_subdir = (
            Path.home() / ".config" / f"test_violation_{uuid.uuid4().hex[:8]}"
        )

        auth_file = tmp_path / "auth.json"
        auth_file.write_text("{}")
        config_dir = tmp_path / ".opencode"
        config_dir.mkdir()
        config_json = tmp_path / "opencode.json"
        config_json.write_text("{}")
        binary = tmp_path / "opencode"
        binary.touch()
        binary.chmod(0o755)

        try:
            # This should raise an error during setup
            with pytest.raises(ValueError, match="ISOLATION VIOLATION"):
                server = OpencodeServer(
                    target_dir=home_subdir,
                    auth_file=auth_file,
                    opencode_config_dir=config_dir,
                    opencode_json=config_json,
                    opencode_binary=binary,
                )
                server._setup_environment()
        finally:
            # Clean up if the directory was created
            if home_subdir.exists():
                import shutil

                shutil.rmtree(home_subdir)

    @patch("subprocess.Popen")
    def test_environment_variables_are_isolated(
        self, mock_popen, mock_paths, setup_mock_files
    ):
        """Test that subprocess receives only isolated environment variables."""
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_process.stdout.readline = Mock(return_value="")
        mock_process.stderr.readline = Mock(return_value="")
        mock_popen.return_value = mock_process

        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
        )

        server._setup_environment()
        server._start_server()

        # Get the environment passed to subprocess
        call_args = mock_popen.call_args
        env = call_args.kwargs["env"]

        # Verify isolated environment
        assert "HOME" in env
        assert env["HOME"] == str(mock_paths["target_dir"] / ".home")

        assert "XDG_CONFIG_HOME" in env
        assert env["XDG_CONFIG_HOME"] == str(
            mock_paths["target_dir"] / ".oc" / "config"
        )

        assert "XDG_DATA_HOME" in env
        assert env["XDG_DATA_HOME"] == str(
            mock_paths["target_dir"] / ".oc" / "data"
        )

        assert "XDG_CACHE_HOME" in env
        assert env["XDG_CACHE_HOME"] == str(mock_paths["target_dir"] / ".cache")

        assert "TMPDIR" in env
        assert env["TMPDIR"] == str(mock_paths["target_dir"] / ".tmp")

        # Verify minimal PATH
        assert "PATH" in env
        assert "/usr/bin" in env["PATH"]
        assert "/bin" in env["PATH"]

        # Verify close_fds is True
        assert call_args.kwargs.get("close_fds") is True

        # Verify we're NOT copying os.environ
        # The environment should be minimal
        assert (
            len(env) < 20
        )  # Should have way fewer variables than full environment

    def test_no_environment_leakage(self, mock_paths, setup_mock_files):
        """Test that user environment variables don't leak into subprocess."""
        # Set a test environment variable
        os.environ["TEST_LEAK_VAR"] = "should_not_appear"

        try:
            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.poll.return_value = None
                mock_process.pid = 12345
                mock_process.stdout = Mock()
                mock_process.stderr = Mock()
                mock_process.stdout.readline = Mock(return_value="")
                mock_process.stderr.readline = Mock(return_value="")
                mock_popen.return_value = mock_process

                server = OpencodeServer(
                    target_dir=mock_paths["target_dir"],
                    auth_file=mock_paths["auth_file"],
                    opencode_config_dir=mock_paths["opencode_config_dir"],
                    opencode_json=mock_paths["opencode_json"],
                    opencode_binary=mock_paths["opencode_binary"],
                )

                server._setup_environment()
                server._start_server()

                # Get the environment passed to subprocess
                env = mock_popen.call_args.kwargs["env"]

                # Verify test variable didn't leak
                assert "TEST_LEAK_VAR" not in env

                # Verify no user-specific paths leak
                real_home = str(Path.home())
                for key, value in env.items():
                    if key not in ["USER", "LOGNAME"]:  # These are safe
                        assert real_home not in str(
                            value
                        ), f"Real home path leaked in {key}={value}"

        finally:
            # Clean up
            del os.environ["TEST_LEAK_VAR"]

    def test_auth_file_is_in_isolated_location(
        self, mock_paths, setup_mock_files
    ):
        """Test that auth.json is copied to isolated XDG data directory."""
        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
        )

        server._setup_environment()

        # Check auth.json is in the isolated data directory
        isolated_auth = (
            mock_paths["target_dir"] / ".oc" / "data" / "opencode" / "auth.json"
        )
        assert isolated_auth.exists()

        # Check permissions are restricted
        assert oct(isolated_auth.stat().st_mode)[-3:] == "600"

        # Verify it's not in the user's real XDG directories
        real_xdg_data = Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        )
        assert not str(isolated_auth).startswith(str(real_xdg_data))

    def test_target_dir_outside_home_is_allowed(self, tmp_path):
        """Test that target directories outside home are allowed."""
        # Use system temp directory (usually /tmp)
        with tempfile.TemporaryDirectory(prefix="opencode_test_") as temp_dir:
            target = Path(temp_dir) / "isolated_env"

            auth_file = tmp_path / "auth.json"
            auth_file.write_text("{}")
            config_dir = tmp_path / ".opencode"
            config_dir.mkdir()
            config_json = tmp_path / "opencode.json"
            config_json.write_text("{}")
            binary = tmp_path / "opencode"
            binary.touch()
            binary.chmod(0o755)

            # This should work fine
            server = OpencodeServer(
                target_dir=target,
                auth_file=auth_file,
                opencode_config_dir=config_dir,
                opencode_json=config_json,
                opencode_binary=binary,
            )

            server._setup_environment()

            # Verify directories were created
            assert target.exists()
            assert (target / ".oc" / "config").exists()
