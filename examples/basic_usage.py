#!/usr/bin/env python3
"""Basic usage example for opencode-server.

Run this example with uv:
    uv run python examples/basic_usage.py

Make sure test_resources/ contains the required files first!
"""

import sys
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from opencode_manager import OpencodeServer


def main():
    """Run basic opencode server example."""
    print("Starting opencode server example...")
    print("-" * 40)

    # Setup paths
    test_dir = Path("./test_run")
    resources = Path("./test_resources")

    # Check required files exist
    required_files = [
        (resources / "auth.json", "auth.json"),
        (resources / ".opencode", ".opencode directory"),
        (resources / "opencode.json", "opencode.json"),
        (resources / "opencode", "opencode binary"),
    ]

    for path, name in required_files:
        if not path.exists():
            print(f"Error: {name} not found at {path}")
            print("Please ensure test_resources/ contains all required files")
            return 1

    try:
        # Create server instance
        # Note: Will automatically use the cheapest model from your
        # configured providers (e.g., claude-3-5-haiku for Anthropic,
        # gpt-4o-mini for OpenAI, gemini-1.5-flash for Google)
        server = OpencodeServer(
            target_dir=test_dir,
            auth_file=resources / "auth.json",
            opencode_config_dir=resources / ".opencode",
            opencode_json=resources / "opencode.json",
            opencode_binary=resources / "opencode",
            port=None,  # Let opencode pick
            hostname=None,  # Let opencode pick
            delete_target_dir_on_exit=False,  # Preserve for inspection
            startup_timeout=15.0,
        )

        print("\nStarting server...")
        with server:
            print(f"Server running at: {server.base_url}")

            # Create a test session
            print("\nCreating test session...")
            session = server.create_session("Test Session")
            print(f"Created: {session}")

            # Send a message
            print("\nSending message...")
            message = "Write a simple Python hello world program"
            response = session.send_message(message)

            if response:
                print(f"Response received: {response[:100]}...")
            else:
                print("No response received")

            # List sessions
            print("\nListing all sessions...")
            sessions = server.list_sessions()
            for s in sessions:
                print(f"  - {s}")

            # Get messages
            messages = session.get_messages()
            print(f"\nTotal messages in session: {len(messages)}")

            # Clean up
            print("\nCleaning up...")
            session.delete()
            print("Session deleted")

    except Exception as e:
        print(f"\nError: {e}")
        return 1

    print("\nExample completed successfully!")
    print(f"Test artifacts preserved in: {test_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
