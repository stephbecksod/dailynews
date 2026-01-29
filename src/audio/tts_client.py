"""ElevenLabs TTS client for generating podcast audio."""

import os
from pathlib import Path
from typing import Optional

import requests

from ..config import get_config


class TTSClient:
    """ElevenLabs Text-to-Speech client."""

    # ElevenLabs API endpoint
    BASE_URL = "https://api.elevenlabs.io/v1"

    # Good voices for news/podcast style
    # Rachel - calm, professional female voice
    # Adam - clear, professional male voice
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel

    def __init__(self):
        """Initialize the TTS client."""
        self.config = get_config()
        self.api_key = self.config.elevenlabs_api_key

        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")

    def generate_audio(
        self,
        text: str,
        output_path: Optional[Path] = None,
        voice_id: Optional[str] = None,
    ) -> Path:
        """
        Generate audio from text using ElevenLabs API.

        Args:
            text: The script text to convert to speech
            output_path: Where to save the MP3 file (default: temp file)
            voice_id: ElevenLabs voice ID (default: Rachel)

        Returns:
            Path to the generated MP3 file
        """
        voice_id = voice_id or self.DEFAULT_VOICE_ID

        # Set output path
        if output_path is None:
            output_path = Path("briefing_audio.mp3")

        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }

        # Request body with voice settings optimized for news reading
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.75,  # Higher = more consistent
                "similarity_boost": 0.75,  # Higher = closer to original voice
                "style": 0.0,  # Lower = more neutral/professional
                "use_speaker_boost": True,
            },
        }

        print(f"Generating audio ({len(text)} characters)...")

        response = requests.post(url, json=data, headers=headers, timeout=300)

        if response.status_code != 200:
            error_msg = response.text
            raise RuntimeError(
                f"ElevenLabs API error ({response.status_code}): {error_msg}"
            )

        # Save audio file
        with open(output_path, "wb") as f:
            f.write(response.content)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Audio generated: {output_path} ({file_size_mb:.2f} MB)")

        return output_path

    def get_character_count(self, text: str) -> int:
        """Get character count for cost estimation."""
        return len(text)

    def estimate_duration(self, text: str) -> float:
        """
        Estimate audio duration in minutes.
        Average speaking rate is ~150 words per minute.
        """
        word_count = len(text.split())
        return word_count / 150
