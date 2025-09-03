"""OpencodeClient - Client for connecting to an existing opencode server."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from opencode_ai import Opencode

logger = logging.getLogger(__name__)


class OpencodeClient:
    """Client for connecting to an already-running opencode server.

    This class provides a simplified interface for interacting with an existing
    opencode server, handling the complexity of the SDK's response structures.
    """

    def __init__(
        self,
        base_url: str,
        default_provider: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        """Initialize client with server URL.

        Args:
            base_url: Base URL of the running opencode server
            default_provider: Optional provider ID (auto-detects if not provided)
            default_model: Optional model ID (auto-detects if not provided)
        """
        self.base_url = base_url
        self.client = Opencode(base_url=base_url)

        # Auto-detect cheapest model if not specified
        self._detect_default_model(default_provider, default_model)
        logger.info(
            f"OpencodeClient initialized for {base_url} "
            f"with {self.default_provider}/{self.default_model}"
        )

    def _detect_default_model(
        self, provider: Optional[str], model: Optional[str]
    ) -> None:
        """Detect the default provider and model to use.

        If not specified, tries to find the cheapest available model.
        """
        if provider and model:
            self.default_provider = provider
            self.default_model = model
            return

        # Try to detect from server's available models
        # For now, use sensible defaults based on common providers
        # TODO: Query server for available models when SDK supports it
        self.default_provider = provider or "openai"
        self.default_model = model or "gpt-4o-mini"

    def _extract_text_from_parts(self, parts: Any) -> str:
        """Extract and concatenate text from message parts.

        Handles various part formats from the SDK.
        """
        if not parts:
            return ""

        text_parts = []
        for part in parts:
            if hasattr(part, "text"):
                text_parts.append(str(part.text))
            elif isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))

        return "".join(text_parts)

    def get_messages_since(
        self, session_id: str, last_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """Get all messages from a session since the given ID.

        Args:
            session_id: ID of the session to retrieve messages from
            last_id: If provided, only return messages after this ID

        Returns:
            Tuple of (list of message dicts, latest message ID)
            Message dicts contain 'role', 'text', and 'id' fields
        """
        try:
            # Get messages from the session
            msg_list = self.client.session.messages(id=session_id)
            messages = []
            latest_id = None
            found_last_id = last_id is None  # If no last_id, include all messages

            for msg in msg_list or []:
                # Messages have an 'info' attribute with the actual message data
                msg_info = getattr(msg, "info", None)
                if not msg_info:
                    continue

                msg_id = getattr(msg_info, "id", None)

                # Skip messages until we find the last_id
                if not found_last_id:
                    if msg_id == last_id:
                        found_last_id = True
                    continue

                # Extract message content
                text = ""
                if hasattr(msg_info, "parts"):
                    text = self._extract_text_from_parts(msg_info.parts)
                elif hasattr(msg_info, "text"):
                    text = str(msg_info.text)

                if text:
                    messages.append(
                        {
                            "role": getattr(msg_info, "role", "unknown"),
                            "text": text,
                            "id": msg_id or "",
                        }
                    )
                    if msg_id:
                        latest_id = msg_id

            logger.debug(
                f"Retrieved {len(messages)} messages from session {session_id}"
            )
            return messages, latest_id

        except Exception as e:
            logger.error(f"Failed to get messages from session {session_id}: {e}")
            raise

    def send_message(
        self,
        session_id: str,
        text: str,
        mode: Optional[str] = None,
        provider_id: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Optional[str]:
        """Send a message to a session and return the response.

        Args:
            session_id: ID of the session to send message to
            text: Text message to send
            mode: Optional agent mode (e.g. 'scout', 'wolf', 'reese')
            provider_id: Optional provider ID (uses default if not specified)
            model_id: Optional model ID (uses default if not specified)

        Returns:
            Response text from the assistant, or None if no response
        """
        if not text or not text.strip():
            logger.warning("Attempted to send empty message")
            return None

        try:
            from opencode_ai._types import NOT_GIVEN
            from opencode_ai.types import TextPartInputParam

            # Build chat parameters
            chat_params = {
                "id": session_id,
                "provider_id": provider_id or self.default_provider,
                "model_id": model_id or self.default_model,
                "parts": [TextPartInputParam(type="text", text=text)],
            }

            # Only add mode if it's specified
            if mode is not None:
                chat_params["mode"] = mode
            else:
                chat_params["mode"] = NOT_GIVEN

            result = self.client.session.chat(**chat_params)

            if not result:
                logger.warning(f"No response from session {session_id}")
                return None

            # Extract response text from the result
            response_text = ""
            parts = getattr(result, "parts", None)
            if parts:
                response_text = self._extract_text_from_parts(parts)
            elif hasattr(result, "text"):
                response_text = str(getattr(result, "text", ""))

            if response_text:
                logger.debug(
                    f"Sent message to session {session_id}, "
                    f"got {len(response_text)} chars"
                )
            else:
                logger.warning(f"Empty response from session {session_id}")

            return response_text or None

        except Exception as e:
            logger.error(f"Failed to send message to session {session_id}: {e}")
            return None

    def create_session(self, title: Optional[str] = None) -> str:
        """Create a new session and return its ID.

        Args:
            title: Optional title for the session

        Returns:
            The new session ID
        """
        try:
            # The SDK doesn't expose title as a parameter directly
            extra_body = {"title": title} if title else None
            session = self.client.session.create(extra_body=extra_body)

            if not session or not session.id:
                raise ValueError("Failed to create session: no ID returned")

            session_msg = f"Created session {session.id}"
            if title:
                session_msg += f" with title: {title}"
            logger.info(session_msg)
            return session.id

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions on the server.

        Returns:
            List of session info dictionaries
        """
        try:
            sessions = self.client.session.list() or []
            return [
                {
                    "id": s.id,
                    "title": getattr(s, "title", "Untitled"),
                    "status": getattr(s, "status", "unknown"),
                    "created_at": getattr(s, "created_at", None),
                }
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def abort_session(self, session_id: str) -> bool:
        """Abort a running session.

        Args:
            session_id: ID of the session to abort

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.session.abort(id=session_id)
            logger.info(f"Aborted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to abort session {session_id}: {e}")
            return False

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get basic information about a session.

        Args:
            session_id: ID of the session to get info for

        Returns:
            Dictionary with session information, or None if not found
        """
        try:
            # Find session in list (SDK limitation: no direct retrieve)
            sessions = self.client.session.list() or []
            session = next((s for s in sessions if s.id == session_id), None)

            if not session:
                logger.warning(f"Session {session_id} not found")
                return None

            # Build info dict from available attributes
            info = {"id": session_id}

            # Copy standard attributes if they exist
            standard_attrs = [
                "status",
                "title",
                "version",
                "created_at",
                "updated_at",
                "metadata",
            ]
            for attr in standard_attrs:
                if hasattr(session, attr):
                    value = getattr(session, attr)
                    if value is not None:  # Only include non-None values
                        info[attr] = value

            logger.debug(f"Retrieved info for session {session_id}")
            return info

        except Exception as e:
            logger.error(f"Failed to get info for session {session_id}: {e}")
            return None
