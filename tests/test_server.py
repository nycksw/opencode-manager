"""Tests for OpencodeServer."""

from unittest.mock import Mock, patch

import pytest

from opencode_manager import OpencodeServer


class TestOpencodeServer:
    """Test OpencodeServer functionality."""

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

    def test_server_initialization(self, mock_paths, setup_mock_files):
        """Test server can be initialized with required parameters."""
        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
        )

        assert server.target_dir == mock_paths["target_dir"]
        assert server.auth_file == mock_paths["auth_file"]
        assert server.opencode_binary == mock_paths["opencode_binary"]
        assert server.port is None  # Default
        assert server.hostname is None  # Default

    def test_server_initialization_with_optional_params(
        self, mock_paths, setup_mock_files
    ):
        """Test server initialization with optional parameters."""
        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
            port=8080,
            hostname="localhost",
            delete_target_dir_on_exit=True,
            startup_timeout=5.0,
        )

        assert server.port == 8080
        assert server.hostname == "localhost"
        assert server.delete_target_dir_on_exit is True
        assert server.startup_timeout == 5.0

    @patch("subprocess.Popen")
    def test_server_start(self, mock_popen, mock_paths, setup_mock_files):
        """Test server startup process."""
        # Mock the subprocess
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_process.stdout = Mock()
        mock_process.stderr = Mock()
        mock_popen.return_value = mock_process

        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
        )

        # Setup environment through isolation manager
        server.isolation_manager.setup_environment(
            mock_paths["auth_file"],
            mock_paths["opencode_config_dir"],
            mock_paths["opencode_json"],
        )

        # Verify target directory structure was created
        assert (mock_paths["target_dir"] / ".oc" / "config").exists()
        assert (mock_paths["target_dir"] / ".oc" / "data").exists()
        assert (mock_paths["target_dir"] / ".cache").exists()

    def test_environment_setup(self, mock_paths, setup_mock_files):
        """Test environment setup creates proper directory structure."""
        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
        )

        server.isolation_manager.setup_environment(
            mock_paths["auth_file"],
            mock_paths["opencode_config_dir"],
            mock_paths["opencode_json"],
        )

        # Check XDG directories
        xdg_config = mock_paths["target_dir"] / ".oc" / "config"
        xdg_data = mock_paths["target_dir"] / ".oc" / "data"
        xdg_cache = mock_paths["target_dir"] / ".cache"

        assert xdg_config.exists()
        assert xdg_data.exists()
        assert xdg_cache.exists()

        # Check copied files
        assert (xdg_data / "opencode" / "auth.json").exists()
        assert (mock_paths["target_dir"] / ".opencode").exists()
        assert (mock_paths["target_dir"] / "opencode.json").exists()

    @patch("opencode_manager.session_manager.SessionManager")
    def test_session_creation(
        self, mock_session_manager_class, mock_paths, setup_mock_files
    ):
        """Test session creation."""
        mock_session_manager = Mock()
        mock_session_manager_class.return_value = mock_session_manager

        mock_session = Mock()
        mock_session.id = "test-session-id"
        mock_session.title = "Test Session"
        mock_session_manager.create_session.return_value = mock_session

        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
        )
        server._session_manager = mock_session_manager

        session = server.create_session("Test Session")

        assert session.id == "test-session-id"
        assert session.title == "Test Session"
        mock_session_manager.create_session.assert_called_once_with(
            "Test Session"
        )

    @patch("opencode_manager.session_manager.SessionManager")
    def test_session_list(
        self, mock_session_manager_class, mock_paths, setup_mock_files
    ):
        """Test listing sessions."""
        mock_session_manager = Mock()
        mock_session_manager_class.return_value = mock_session_manager

        mock_session1 = Mock()
        mock_session1.id = "session-1"
        mock_session1.title = "Session 1"

        mock_session2 = Mock()
        mock_session2.id = "session-2"
        mock_session2.title = "Session 2"

        mock_session_manager.list_sessions.return_value = [
            mock_session1,
            mock_session2,
        ]

        server = OpencodeServer(
            target_dir=mock_paths["target_dir"],
            auth_file=mock_paths["auth_file"],
            opencode_config_dir=mock_paths["opencode_config_dir"],
            opencode_json=mock_paths["opencode_json"],
            opencode_binary=mock_paths["opencode_binary"],
        )
        server._session_manager = mock_session_manager

        sessions = server.list_sessions()

        assert len(sessions) == 2
        assert sessions[0].id == "session-1"
        assert sessions[1].id == "session-2"
