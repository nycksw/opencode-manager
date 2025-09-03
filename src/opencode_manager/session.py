"""Session wrapper with convenience methods."""

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .server import OpencodeServer


class Session:
    """Wrapper around a session with convenience methods and message
    tracking."""

    def __init__(self, server: "OpencodeServer", session_data):
        """Initialize session wrapper.

        Args:
            server: The OpencodeServer instance managing this session
            session_data: Raw session data from the API
        """
        self._server = server
        self._data = session_data
        self._last_read_id = None
        self._message_cache = []

    @property
    def id(self) -> str:
        """Get session ID."""
        return self._data.id

    @property
    def title(self) -> str:
        """Get session title."""
        return self._data.title

    @property
    def version(self) -> str:
        """Get session version."""
        return self._data.version

    def send_message(self, message: str) -> Optional[str]:
        """Send a message and return the response.

        Args:
            message: The message text to send

        Returns:
            The assistant's response text, or None if no response
        """
        return self._server.send_message(self.id, message)

    def get_messages(self, limit: Optional[int] = None) -> List:
        """Get all or last N messages from the session.

        Args:
            limit: Optional maximum number of messages to return (most recent)

        Returns:
            List of message objects
        """
        messages = self._server.get_messages(self.id)

        # Update last read ID if we got messages
        if messages and len(messages) > 0:
            # Messages have an 'info' attribute with the actual message data
            last_msg = messages[-1]
            if hasattr(last_msg, "info") and hasattr(last_msg.info, "id"):
                self._last_read_id = last_msg.info.id

        # Cache for future reference
        self._message_cache = messages

        # Return limited set if requested
        if limit and len(messages) > limit:
            return messages[-limit:]
        return messages

    def get_new_messages(self) -> List:
        """Get messages since last read.

        Returns:
            List of new message objects since last read
        """
        all_messages = self._server.get_messages(self.id)

        if not self._last_read_id:
            # First read - return all and update cursor
            if all_messages and len(all_messages) > 0:
                last_msg = all_messages[-1]
                if hasattr(last_msg, "info") and hasattr(last_msg.info, "id"):
                    self._last_read_id = last_msg.info.id
            return all_messages

        # Find index of last read message
        last_idx = -1
        for i, msg in enumerate(all_messages):
            if hasattr(msg, "info") and hasattr(msg.info, "id"):
                if msg.info.id == self._last_read_id:
                    last_idx = i
                    break

        # Get messages after last read
        if last_idx >= 0:
            new_messages = all_messages[last_idx + 1 :]
        else:
            # Last read message not found, return all
            new_messages = all_messages

        # Update cursor to latest
        if new_messages and len(new_messages) > 0:
            last_msg = new_messages[-1]
            if hasattr(last_msg, "info") and hasattr(last_msg.info, "id"):
                self._last_read_id = last_msg.info.id

        return new_messages

    def rename(self, new_title: str):
        """Update the session title.

        Args:
            new_title: The new title for the session
        """
        # SST SDK doesn't support updating sessions
        self._server.logger.warning(
            f"Session rename not supported in SST SDK. "
            f"Would rename {self.id} to: {new_title}"
        )

    def abort(self):
        """Abort this session (stop any running operations)."""
        self._server.abort_session(self.id)

    def delete(self):
        """Delete this session permanently."""
        self._server.delete_session(self.id)

    def __repr__(self) -> str:
        """String representation of the session."""
        return f"Session(id={self.id}, title={self.title})"
