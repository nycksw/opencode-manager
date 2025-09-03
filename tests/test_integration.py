"""Integration tests for opencode-server with real server instances.

[!] WARNING: These tests make REAL API calls that cost money!
They will consume credits from your configured AI provider.

These tests require configuration files in test_resources/.

To set up test resources:
    ./test_resources/setup.sh

This will copy your opencode configuration files for testing.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest
import requests
from opencode_manager import OpencodeServer


def check_opencode_version():
    """Show version info for debugging test failures."""
    config_file = Path("opencode_versions.json")
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
            expected = config["recommended_opencode_version"]

            # Check version of actual test binary
            result = subprocess.run(
                ["test_resources/opencode", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            actual = result.stdout.strip()

            if actual != expected:
                print(
                    f"\nWARNING: Testing with opencode {actual} "
                    f"(recommended: {expected})"
                )
                print("   If tests fail, consider: make update-api-spec\n")
        except Exception:
            pass  # Don't break tests over version display


def get_test_config() -> Dict[str, Any]:
    """Get test configuration from test_resources directory.

    Returns:
        Dict with paths and metadata for testing

    Raises:
        pytest.skip: If test_resources is not properly configured
    """
    test_resources = Path("test_resources")

    # Check if test_resources directory exists
    if not test_resources.exists():
        pytest.skip(
            "\n\n"
            "============================================================\n"
            "  Integration tests require test configuration files\n"
            "============================================================\n"
            "\n"
            "  The test_resources/ directory is missing.\n"
            "\n"
            "  This should have been included with the repository.\n"
            "  Please check that you have the complete source.\n"
            "============================================================\n"
        )

    # Check for required files
    auth_path = test_resources / "auth.json"
    config_path = test_resources / "opencode.json"
    binary_path = test_resources / "opencode"

    missing = []
    if not auth_path.exists():
        missing.append("auth.json")
    if not config_path.exists():
        missing.append("opencode.json")
    if not binary_path.exists():
        missing.append("opencode binary")

    if missing:
        # Provide helpful instructions for missing files
        pytest.skip(
            "\n\n"
            "============================================================\n"
            "  Integration tests require configuration files\n"
            "============================================================\n"
            "\n"
            f"  Missing files in test_resources/:\n"
            f"    • {', '.join(missing)}\n"
            "\n"
            "  To set up your test environment, run:\n"
            "\n"
            "    ./test_resources/setup.sh\n"
            "\n"
            "  This will safely copy your opencode configuration files\n"
            "  for testing. Your original files will not be modified.\n"
            "\n"
            "============================================================\n"
        )

    # All files exist - return configuration
    return {
        "auth": auth_path,
        "config": config_path,
        "opencode_dir": test_resources / ".opencode",
        "binary": binary_path,
        "source": "test_resources",
        "warning": "Using test resources (safe, isolated)",
    }


@pytest.mark.integration
class TestIntegrationWithRealServer:
    """Integration tests that run a real opencode server."""

    def setup_class(self):
        """Check version once before all tests."""
        check_opencode_version()

    def test_server_lifecycle(self, tmp_path, capsys):
        """Test basic server lifecycle with real server.

        This test:
        1. Gets test configuration (safely)
        2. Creates isolated environment in tmp_path
        3. Starts real opencode server
        4. Creates a session
        5. Sends a message
        6. Cleans up automatically
        """
        # Get configuration with safety checks
        config = get_test_config()

        # Print test header
        print("\n" + "=" * 70)
        print("TEST: Server Lifecycle")
        print("=" * 70)
        print(f"Configuration: {config['source']}")
        print(f"Safety: {config['warning']}")
        print("-" * 70)

        # Create unique test directory in pytest's tmp_path (auto-cleaned)
        test_dir = tmp_path / f"opencode_integration_{os.getpid()}"

        # Ensure we have an opencode directory to copy
        opencode_dir = config.get("opencode_dir")
        if not opencode_dir or not opencode_dir.exists():
            # Create minimal .opencode directory
            opencode_dir = tmp_path / "minimal_opencode"
            opencode_dir.mkdir()
            (opencode_dir / "config").touch()

        print(f"\nTest directory: {test_dir}")
        print("   (auto-deleted after test)")

        try:
            # Create server with safety features
            print("\nStarting opencode server...")
            print(f"   Binary: {config['binary']}")
            print("   Timeout: 30s")

            server = OpencodeServer(
                target_dir=test_dir,
                auth_file=config["auth"],
                opencode_config_dir=opencode_dir,
                opencode_json=config["config"],
                opencode_binary=config["binary"],
                delete_target_dir_on_exit=True,  # Extra safety
                startup_timeout=30.0,  # Longer timeout for real server
            )

            with server:
                print("\nServer started successfully!")
                print(f"   URL: {server.base_url}")
                pid = (
                    server.process_manager._process.pid
                    if server.process_manager._process
                    else "N/A"
                )
                print(f"   PID: {pid}")

                # Test basic operations
                print("\nCreating session...")
                session = server.create_session("Integration Test Session")
                print("Session created")
                print(f"   ID: {session.id}")
                print(f"   Title: {session.title}")

                # Send a simple message
                print("\nSending test message...")
                print(
                    "   Message: 'Say exactly: Integration test successful "
                    "and nothing else'"
                )

                response = session.send_message(
                    "Say exactly: 'Integration test successful' " "and nothing else"
                )

                print("\nAssistant response:")
                if response:
                    # Show full response (it should be short anyway)
                    for line in response.strip().split("\n"):
                        print(f"   {line}")
                else:
                    print("   (No response received)")

                # List sessions
                print("\nListing sessions...")
                sessions = server.list_sessions()
                assert len(sessions) > 0, "Should have at least one session"
                print(f"Found {len(sessions)} session(s):")
                for s in sessions[:3]:  # Show first 3
                    print(f"   - {s.title} ({s.id[:8]}...)")

                # Clean up session
                print("\nDeleting session...")
                session.delete()
                print("Session deleted")

                # Capture version and API spec if requested
                if os.environ.get("UPDATE_API_SPEC"):
                    print("\nUpdating API spec...")
                    try:
                        # Get version (runs in isolation)
                        version = server.get_opencode_version()

                        # Update version in config
                        config_file = Path("opencode_versions.json")
                        with open(config_file) as f:
                            config = json.load(f)

                        if config["recommended_opencode_version"] != version:
                            print("Warning: Version mismatch in config")
                            print(f"  Config: {config['recommended_opencode_version']}")
                            print(f"  Binary: {version}")

                        print(f"Captured version: {version}")

                        # Get API spec from running server
                        response = requests.get(f"{server.base_url}/doc")
                        response.raise_for_status()

                        # Try to parse as JSON
                        api_spec = response.json()
                        with open("opencode_api.json", "w") as f:
                            json.dump(api_spec, f, indent=2)

                        print(f"Updated API spec for opencode {version}")
                    except Exception as e:
                        print(f"Warning: Could not update API spec: {e}")
                        print(
                            "Note: /doc endpoint may not be available in this version"
                        )

                print("\n" + "=" * 70)
                print("Integration test completed successfully!")
                print("=" * 70)

        except Exception as e:
            print(f"\n[!] Integration test failed: {e}")
            raise

        finally:
            # Verify cleanup
            if test_dir.exists():
                auth_files = list(test_dir.glob("**/auth.json"))
                if auth_files:
                    print(
                        f"[!] Warning: Found {len(auth_files)} "
                        f"auth.json files after test"
                    )
                    for auth in auth_files:
                        auth.unlink()
                        print(f"  Removed: {auth}")

            print("\nCleanup completed")

    def test_message_tracking(self, tmp_path, capsys):
        """Test message tracking functionality with real server."""
        config = get_test_config()

        # Print test header
        print("\n" + "=" * 70)
        print("TEST: Message Tracking")
        print("=" * 70)
        print(f"Configuration: {config['source']}")
        print("-" * 70)

        test_dir = tmp_path / f"opencode_msgtrack_{os.getpid()}"

        # Get opencode dir
        opencode_dir = config.get("opencode_dir")
        if not opencode_dir or not opencode_dir.exists():
            opencode_dir = tmp_path / "minimal_opencode"
            opencode_dir.mkdir()
            (opencode_dir / "config").touch()

        print("\nStarting opencode server for message tracking test...")

        server = OpencodeServer(
            target_dir=test_dir,
            auth_file=config["auth"],
            opencode_config_dir=opencode_dir,
            opencode_json=config["config"],
            opencode_binary=config["binary"],
            delete_target_dir_on_exit=True,
            startup_timeout=30.0,
        )

        with server:
            print(f"Server started at: {server.base_url}")

            print("\nCreating session for message tracking...")
            session = server.create_session("Message Tracking Test")
            print(f"Session created: {session.id}")

            # Send first message
            print("\nSending first message...")
            print("   Message: 'Say First message received'")
            response1 = session.send_message("Say 'First message received'")
            assert response1 is not None, "Should get a response"
            print("\nResponse 1:")
            for line in (response1 or "").strip().split("\n"):
                print(f"   {line}")

            # Check message count
            print("\nChecking message history...")
            messages = session.get_messages()
            print(f"   Total messages: {len(messages)}")
            assert len(messages) >= 2, "Should have at least user message and response"

            # Track new messages
            print("\nGetting new messages (baseline)...")
            new_msgs = session.get_new_messages()
            initial_count = len(new_msgs)
            print(f"   Initial message count: {initial_count}")

            # Send another message
            print("\nSending second message...")
            print("   Message: 'Say Second message received'")
            response2 = session.send_message("Say 'Second message received'")
            print("\nResponse 2:")
            for line in (response2 or "").strip().split("\n"):
                print(f"   {line}")

            # Get only new messages
            print("\nGetting new messages since last check...")
            new_msgs = session.get_new_messages()
            print(f"   New messages: {len(new_msgs)}")
            assert len(new_msgs) >= 2, "Should have new user message and response"

            # Show message types
            for i, msg in enumerate(new_msgs[:4], 1):  # Show first 4
                msg_type = "unknown"
                if hasattr(msg, "info"):
                    msg_type = getattr(msg.info, "role", "unknown")
                print(f"     {i}. {msg_type} message")

            # Clean up
            print("\nCleaning up...")
            session.delete()
            print("Session deleted")

            print("\n" + "=" * 70)
            print("Message tracking test completed successfully!")
            print("=" * 70)
