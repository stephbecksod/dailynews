"""Configuration management for Daily News Synthesizer."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager that combines config.yaml with environment variables."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config.yaml. Defaults to project root.
        """
        if config_path is None:
            # Find config.yaml relative to this file
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config.yaml"

        self._config = self._load_yaml(config_path)
        self._env = os.environ.get("ENVIRONMENT", "local")

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(path, "r") as f:
            return yaml.safe_load(f)

    @property
    def is_github_actions(self) -> bool:
        """Check if running in GitHub Actions."""
        return self._env == "github_actions"

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return os.environ.get("DEBUG", "false").lower() == "true"

    # Newsletter sources
    @property
    def newsletter_sources(self) -> List[Dict[str, str]]:
        """Get list of newsletter sources with email and name."""
        return self._config.get("newsletter_sources", [])

    @property
    def newsletter_emails(self) -> List[str]:
        """Get list of newsletter email addresses."""
        return [src["email"] for src in self.newsletter_sources]

    def get_source_name(self, email: str) -> str:
        """Get display name for a newsletter source email."""
        email_lower = email.lower()
        for src in self.newsletter_sources:
            if src["email"].lower() in email_lower or email_lower in src["email"].lower():
                return src["name"]
        return email

    # Briefing settings
    @property
    def recipient_email(self) -> str:
        """Get recipient email address."""
        return os.environ.get(
            "RECIPIENT_EMAIL",
            self._config.get("briefing", {}).get("recipient", "")
        )

    @property
    def subject_prefix(self) -> str:
        """Get email subject prefix."""
        return self._config.get("briefing", {}).get("subject_prefix", "[AI Briefing]")

    @property
    def top_stories_count(self) -> int:
        """Get number of top stories to highlight."""
        return self._config.get("briefing", {}).get("top_stories_count", 5)

    # Claude settings
    @property
    def claude_model(self) -> str:
        """Get Claude model to use."""
        return self._config.get("claude", {}).get("model", "claude-sonnet-4-5-20250929")

    @property
    def claude_max_tokens(self) -> int:
        """Get max tokens for Claude responses."""
        return self._config.get("claude", {}).get("max_tokens", 8000)

    @property
    def claude_temperature(self) -> float:
        """Get temperature for Claude responses."""
        return self._config.get("claude", {}).get("temperature", 0.3)

    @property
    def anthropic_api_key(self) -> str:
        """Get Anthropic API key."""
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        return key

    # Gmail settings
    @property
    def gmail_credentials_path(self) -> Optional[str]:
        """Get path to Gmail credentials file (local development)."""
        return os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json")

    @property
    def gmail_token_json(self) -> Optional[str]:
        """Get Gmail token JSON (GitHub Actions)."""
        return os.environ.get("GMAIL_TOKEN_JSON")

    # ElevenLabs settings
    @property
    def elevenlabs_api_key(self) -> Optional[str]:
        """Get ElevenLabs API key for audio generation."""
        return os.environ.get("ELEVENLABS_API_KEY")

    @property
    def audio_enabled(self) -> bool:
        """Check if audio generation is enabled (API key is set)."""
        return bool(self.elevenlabs_api_key)

    # Major AI companies (for context)
    @property
    def major_ai_companies(self) -> List[str]:
        """Get list of major AI companies."""
        return self._config.get("major_ai_companies", [])

    # Retry settings
    @property
    def max_retry_attempts(self) -> int:
        """Get max retry attempts for API calls."""
        return self._config.get("retry", {}).get("max_attempts", 3)

    @property
    def retry_base_delay(self) -> int:
        """Get base delay in seconds for retries."""
        return self._config.get("retry", {}).get("base_delay_seconds", 5)

    @property
    def retry_max_delay(self) -> int:
        """Get max delay in seconds for retries."""
        return self._config.get("retry", {}).get("max_delay_seconds", 60)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
