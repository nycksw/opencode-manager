"""Session management for opencode server instances."""

import logging
from typing import List, Optional

from opencode_ai import Opencode
from opencode_ai.types import TextPartInputParam

from .exceptions import SessionError, SessionNotFoundError
from .models import ModelSelector
from .session import Session


class SessionManager:
    """Manages sessions for an opencode server instance."""

    def __init__(
        self,
        client: Opencode,
        model_selector: ModelSelector,
        logger: logging.Logger,
    ):
        """Initialize the session manager.

        Args:
            client: Opencode API client
            model_selector: Model selector instance
            logger: Logger instance for output
        """
        self.client = client
        self.model_selector = model_selector
        self.logger = logger

    def create_session(self, title: Optional[str] = None) -> Session:
        """Create a new session.

        Args:
            title: Optional title for the session

        Returns:
            New Session instance

        Raises:
            SessionError: If session creation fails
        """
        # The SDK doesn't expose title as a parameter, but we can pass it
        # via extra_body
        body = {}
        if title:
            body["title"] = title

        try:
            session_data = self.client.session.create(
                extra_body=body if body else None
            )
        except Exception as e:
            raise SessionError(f"Failed to create session: {e}")

        if not session_data:
            raise SessionError("Failed to create session: No data returned")

        self.logger.info(f"Created session: {session_data.id}")
        return Session(self, session_data)

    def list_sessions(self) -> List[Session]:
        """List all sessions.

        Returns:
            List of Session instances
        """
        try:
            sessions_data = self.client.session.list()
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return []

        if sessions_data is None:
            return []

        return [Session(self, s) for s in sessions_data]

    def get_session(self, session_id: str) -> Session:
        """Get a specific session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session instance

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        sessions_data = self.client.session.list()
        for session_data in sessions_data:
            if session_data.id == session_id:
                return Session(self, session_data)

        raise SessionNotFoundError(f"Session not found: {session_id}")

    def update_session(self, session_id: str, title: str) -> None:
        """Update session title.

        Args:
            session_id: Session ID to update
            title: New title for the session

        Note:
            The opencode-ai SDK doesn't currently expose a session update
            method. This is a placeholder for when it's added. You can work
            around this by using the raw HTTP client if needed.
        """
        # TODO: Implement when SDK adds session update support
        # For now, we could use self.client._client.patch() with raw HTTP
        # but that's using private API
        self.logger.info(
            f"Session rename not yet implemented in SDK. "
            f"Would rename {session_id} to: {title}"
        )

    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session ID to delete

        Raises:
            SessionError: If deletion fails
        """
        try:
            self.client.session.delete(id=session_id)
            self.logger.info(f"Deleted session: {session_id}")
        except Exception as e:
            raise SessionError(f"Failed to delete session: {e}")

    def abort_session(self, session_id: str) -> None:
        """Abort a session.

        Args:
            session_id: Session ID to abort

        Raises:
            SessionError: If abort fails
        """
        try:
            self.client.session.abort(id=session_id)
            self.logger.info(f"Aborted session: {session_id}")
        except Exception as e:
            raise SessionError(f"Failed to abort session: {e}")

    def abort_all_sessions(self) -> None:
        """Emergency kill switch - abort all sessions."""
        self.logger.warning("Aborting all sessions!")
        sessions = self.list_sessions()
        for session in sessions:
            try:
                self.abort_session(session.id)
            except SessionError as e:
                self.logger.error(
                    f"Failed to abort session {session.id}: {e}"
                )

    def send_message(
        self, session_id: str, message: str
    ) -> Optional[str]:
        """Send a message to a session and get response.

        Args:
            session_id: Session ID to send message to
            message: Message text to send

        Returns:
            Assistant's response text, or None if no response

        Raises:
            SessionError: If message sending fails
        """
        provider_id, model_id = self.model_selector.get_default_model()

        try:
            response = self.client.session.chat(
                id=session_id,
                provider_id=provider_id,
                model_id=model_id,
                parts=[TextPartInputParam(type="text", text=message)],
            )
        except Exception as e:
            raise SessionError(f"Failed to send message: {e}")

        # Extract text from response
        if response:
            # Handle response whether it has parts attribute or not
            parts = getattr(response, "parts", None)
            if parts:
                text_parts = []
                for part in parts:
                    # Parts can be dicts or objects
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    elif hasattr(part, "type") and getattr(part, "type") == "text":
                        text_parts.append(getattr(part, "text", ""))
                    elif hasattr(part, "text"):
                        text_parts.append(str(getattr(part, "text", "")))
                
                # Return joined text if we found any, otherwise try direct text attribute
                if text_parts:
                    return "\n".join(text_parts)
            
            # If no parts, try to get text directly from response
            if hasattr(response, "text"):
                return str(getattr(response, "text"))
            
            # Last resort: return string representation if response exists
            return str(response) if response else None
        return None

    def get_messages(self, session_id: str) -> List:
        """Get all messages from a session.

        Args:
            session_id: Session ID to get messages from

        Returns:
            List of message objects

        Raises:
            SessionError: If retrieval fails
        """
        try:
            messages = self.client.session.messages(id=session_id)
            return messages or []
        except Exception as e:
            raise SessionError(f"Failed to get messages: {e}")