"""Configuration constants for opencode-manager."""

from typing import Dict

# Timeout configurations (in seconds)
DEFAULT_STARTUP_TIMEOUT = 10.0
PROCESS_TERMINATION_TIMEOUT = 5.0
HEALTH_CHECK_INTERVAL = 0.5
URL_DISCOVERY_POLL_INTERVAL = 0.1

# File permissions
AUTH_FILE_PERMISSIONS = 0o600  # Owner read/write only
RUNTIME_DIR_PERMISSIONS = 0o700  # Owner only access

# Default model configurations by provider
CHEAP_MODELS: Dict[str, str] = {
    "anthropic": "claude-3-5-haiku-20241022",
    "openai": "gpt-4o-mini",
    "google": "gemini-1.5-flash",
}

# URL discovery patterns
URL_PATTERNS = [
    r"Server running at (https?://[^\s]+)",
    r"listening on (https?://[^\s]+)",
    r"server listening on (https?://[^\s]+)",
    r"(https?://\d+\.\d+\.\d+\.\d+:\d+)",
]

# Environment configuration
DEFAULT_LOCALE = "en_US.UTF-8"
DEFAULT_TERM = "xterm-256color"
DEFAULT_USER = "opencode"
SYSTEM_PATH = "/usr/local/bin:/usr/bin:/bin"
