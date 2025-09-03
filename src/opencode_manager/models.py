"""Model selection logic for opencode sessions."""

import json
import logging
from pathlib import Path
from typing import Tuple

from .constants import CHEAP_MODELS
from .exceptions import ConfigurationError


class ModelSelector:
    """Handles model selection for chat sessions."""

    def __init__(
        self,
        auth_file: Path,
        opencode_json: Path,
        logger: logging.Logger,
    ):
        """Initialize the model selector.

        Args:
            auth_file: Path to auth.json file
            opencode_json: Path to opencode.json configuration
            logger: Logger instance for output
        """
        self.auth_file = auth_file.resolve()
        self.opencode_json = opencode_json.resolve()
        self.logger = logger

    def get_default_model(self) -> Tuple[str, str]:
        """Get provider/model from config or use cheap default.

        Returns:
            Tuple of (provider_id, model_id)

        Raises:
            ConfigurationError: If no valid model can be determined
        """
        # Check opencode.json for explicit model configuration
        try:
            with open(self.opencode_json) as f:
                config = json.load(f)
                if model_str := config.get("model", ""):
                    parts = model_str.split("/")
                    if len(parts) == 2:
                        self.logger.info(f"Using configured model: {model_str}")
                        return (parts[0], parts[1])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.debug(f"Could not load model from config: {e}")

        # Load available providers from auth file
        try:
            with open(self.auth_file) as f:
                auth_providers = set(json.load(f).keys())
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ConfigurationError(f"Failed to load auth file: {e}")

        # Find first available cheap model
        for provider, model in CHEAP_MODELS.items():
            if provider in auth_providers:
                self.logger.info(f"Using {provider}/{model} (cheap model)")
                return (provider, model)

        # Fallback to first available provider with default model
        if auth_providers:
            provider = next(iter(auth_providers))
            model = CHEAP_MODELS.get(provider, "claude-3-5-haiku-20241022")
            self.logger.warning(f"Using fallback: {provider}/{model}")
            return (provider, model)

        raise ConfigurationError("No valid authentication providers found")
