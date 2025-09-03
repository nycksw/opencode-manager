"""Custom exceptions for opencode-manager."""


class OpencodeManagerError(Exception):
    """Base exception for all opencode-manager errors."""

    pass


class IsolationError(OpencodeManagerError):
    """Raised when isolation requirements are violated."""

    pass


class ServerStartupError(OpencodeManagerError):
    """Raised when the server fails to start properly."""

    pass


class SessionError(OpencodeManagerError):
    """Base exception for session-related errors."""

    pass


class SessionNotFoundError(SessionError):
    """Raised when a requested session doesn't exist."""

    pass


class ConfigurationError(OpencodeManagerError):
    """Raised when configuration is invalid or missing."""

    pass