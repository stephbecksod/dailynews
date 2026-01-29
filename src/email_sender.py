"""Email sender for briefings using Gmail API."""

from pathlib import Path
from typing import Dict, Optional, Union

from .config import get_config
from .gmail_client import GmailClient


class EmailSender:
    """Send briefing emails via Gmail API."""

    def __init__(self, gmail_client: Optional[GmailClient] = None):
        """
        Initialize the email sender.

        Args:
            gmail_client: Optional GmailClient instance. Creates new one if not provided.
        """
        self.config = get_config()
        self.gmail = gmail_client or GmailClient()

    def send_briefing(
        self,
        briefing: Dict[str, str],
        recipient: Optional[str] = None,
        audio_path: Optional[Union[str, Path]] = None,
    ) -> Dict:
        """
        Send the briefing email.

        Args:
            briefing: Dictionary with 'html', 'text', and 'subject' keys
            recipient: Optional override for recipient email
            audio_path: Optional path to MP3 audio file to attach

        Returns:
            Sent message metadata from Gmail API
        """
        # Ensure authenticated
        if not self.gmail.service:
            self.gmail.authenticate()

        to_email = recipient or self.config.recipient_email
        if not to_email:
            raise ValueError("No recipient email configured")

        print(f"\nSending briefing to {to_email}...")
        if audio_path:
            print(f"  Attaching audio: {audio_path}")

        result = self.gmail.send_email(
            to=to_email,
            subject=briefing["subject"],
            html_body=briefing["html"],
            text_body=briefing.get("text"),
            attachment_path=audio_path,
        )

        return result

    def send_error_notification(
        self,
        error_message: str,
        recipient: Optional[str] = None,
    ) -> Dict:
        """
        Send an error notification email.

        Args:
            error_message: Description of the error
            recipient: Optional override for recipient email

        Returns:
            Sent message metadata from Gmail API
        """
        # Ensure authenticated
        if not self.gmail.service:
            self.gmail.authenticate()

        to_email = recipient or self.config.recipient_email
        if not to_email:
            raise ValueError("No recipient email configured")

        subject = f"{self.config.subject_prefix} ERROR - Briefing Failed"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, sans-serif; padding: 20px; }}
                .error-box {{
                    background-color: #fef2f2;
                    border: 1px solid #fecaca;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .error-title {{
                    color: #dc2626;
                    font-size: 18px;
                    font-weight: 600;
                    margin: 0 0 12px 0;
                }}
                .error-message {{
                    color: #7f1d1d;
                    font-family: monospace;
                    white-space: pre-wrap;
                }}
            </style>
        </head>
        <body>
            <h2>AI Briefing Generation Failed</h2>
            <div class="error-box">
                <p class="error-title">Error Details</p>
                <p class="error-message">{error_message}</p>
            </div>
            <p>Please check the GitHub Actions logs for more details.</p>
        </body>
        </html>
        """

        text_body = f"""
AI Briefing Generation Failed
=============================

Error Details:
{error_message}

Please check the GitHub Actions logs for more details.
        """

        print(f"Sending error notification to {to_email}...")

        result = self.gmail.send_email(
            to=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

        return result
