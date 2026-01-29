"""Gmail API client for fetching newsletters and sending emails."""

import base64
import json
import os
import pickle
import re
from datetime import datetime, timedelta
from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

try:
    from bs4 import BeautifulSoup
    HTML_PARSING_AVAILABLE = True
except ImportError:
    HTML_PARSING_AVAILABLE = False

from .config import get_config


# Gmail API scopes - read and send
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailClient:
    """Gmail API client for reading newsletters and sending briefings."""

    def __init__(self):
        """Initialize the Gmail client."""
        self.config = get_config()
        self.service = None
        self._credentials_dir = Path(".gmail_credentials")
        self._credentials_dir.mkdir(exist_ok=True)

    def authenticate(self) -> None:
        """
        Authenticate with Gmail API.

        Supports two modes:
        1. Local development: Uses credentials.json and OAuth flow
        2. GitHub Actions: Uses GMAIL_TOKEN_JSON environment variable
        """
        creds = None

        if self.config.is_github_actions:
            # GitHub Actions: Load from environment variable
            token_json = self.config.gmail_token_json
            if token_json:
                try:
                    token_data = json.loads(base64.b64decode(token_json))
                    creds = Credentials(
                        token=token_data.get("token"),
                        refresh_token=token_data.get("refresh_token"),
                        token_uri=token_data.get("token_uri"),
                        client_id=token_data.get("client_id"),
                        client_secret=token_data.get("client_secret"),
                        scopes=token_data.get("scopes"),
                    )
                    print("[OK] Loaded credentials from GMAIL_TOKEN_JSON")
                except Exception as e:
                    raise RuntimeError(f"Failed to load Gmail credentials: {e}")
        else:
            # Local development: Try MCP token first, then standard OAuth
            creds = self._load_local_credentials()

        # Refresh if needed
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
            self._save_credentials(creds)

        if not creds or not creds.valid:
            if self.config.is_github_actions:
                raise RuntimeError("Invalid Gmail credentials in GitHub Actions")
            # Local: Run OAuth flow
            creds = self._run_oauth_flow()

        # Build Gmail API service
        self.service = build("gmail", "v1", credentials=creds)
        print("[OK] Authenticated with Gmail API")

    def _load_local_credentials(self) -> Optional[Credentials]:
        """Load credentials for local development."""
        creds = None

        # Try MCP server token first
        mcp_token_path = Path.home() / ".gmail-mcp" / "gmail-token.json"
        if mcp_token_path.exists():
            try:
                with open(mcp_token_path, "r") as f:
                    token_data = json.load(f)
                creds = Credentials(
                    token=token_data.get("token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    scopes=token_data.get("scopes"),
                )
                print("[OK] Loaded credentials from MCP server token")
                return creds
            except Exception as e:
                print(f"[WARNING] Could not load MCP token: {e}")

        # Try standard token pickle
        token_path = self._credentials_dir / "token.pickle"
        if token_path.exists():
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
                print("[OK] Loaded credentials from token.pickle")

        return creds

    def _run_oauth_flow(self) -> Credentials:
        """Run OAuth flow for local development."""
        credentials_path = self.config.gmail_credentials_path
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Credentials file not found: {credentials_path}\n"
                "Please download OAuth credentials from Google Cloud Console."
            )

        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)
        self._save_credentials(creds)
        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to pickle file."""
        token_path = self._credentials_dir / "token.pickle"
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    def search_newsletters(
        self,
        sender_emails: List[str],
        days_back: int = 1,
        max_results: int = 20,
    ) -> List[Dict]:
        """
        Search for newsletters from specified senders.

        Args:
            sender_emails: List of sender email addresses
            days_back: How many days back to search
            max_results: Maximum number of results

        Returns:
            List of email metadata dictionaries
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        # Build query for multiple senders
        sender_queries = [f"from:{email}" for email in sender_emails]
        sender_query = " OR ".join(sender_queries)

        # Date range
        after_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
        query = f"({sender_query}) after:{after_date}"

        print(f"Searching Gmail: {query}")

        results = []
        page_token = None

        while len(results) < max_results:
            response = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=min(100, max_results - len(results)),
                    pageToken=page_token,
                )
                .execute()
            )

            messages = response.get("messages", [])
            if not messages:
                break

            for msg in messages:
                metadata = (
                    self.service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=msg["id"],
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"],
                    )
                    .execute()
                )

                headers = {
                    h["name"]: h["value"]
                    for h in metadata.get("payload", {}).get("headers", [])
                }

                results.append({
                    "id": msg["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                })

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        print(f"[OK] Found {len(results)} newsletters")
        return results

    def get_email_text(self, message_id: str) -> Dict:
        """
        Get email metadata and plain text content.

        Args:
            message_id: Gmail message ID

        Returns:
            Dictionary with email metadata and text content
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        # Get full message
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        # Extract headers
        headers = {
            h["name"]: h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }

        # Extract plain text
        plain_text = self._extract_text_from_payload(message.get("payload", {}))

        return {
            "id": message_id,
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "text": plain_text,
        }

    def _extract_text_from_payload(self, payload: Dict) -> str:
        """Extract plain text from email payload."""
        text_parts = []
        html_parts = []

        def extract_recursive(p: Dict) -> None:
            mime_type = p.get("mimeType", "")

            if mime_type == "text/plain":
                body_data = p.get("body", {}).get("data", "")
                if body_data:
                    decoded = base64.urlsafe_b64decode(body_data).decode(
                        "utf-8", errors="ignore"
                    )
                    text_parts.append(decoded)

            elif mime_type == "text/html":
                body_data = p.get("body", {}).get("data", "")
                if body_data:
                    decoded = base64.urlsafe_b64decode(body_data).decode(
                        "utf-8", errors="ignore"
                    )
                    html_parts.append(decoded)

            elif mime_type.startswith("multipart/"):
                for part in p.get("parts", []):
                    extract_recursive(part)

        extract_recursive(payload)

        # Prefer plain text
        if text_parts:
            return "\n\n".join(text_parts)

        # Fall back to HTML conversion
        if html_parts and HTML_PARSING_AVAILABLE:
            converted = []
            for html in html_parts:
                text = self._html_to_text(html)
                if text:
                    converted.append(text)
            return "\n\n".join(converted)

        return ""

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        if not HTML_PARSING_AVAILABLE:
            # Fallback: regex-based stripping
            text = re.sub(
                r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
            )
            text = re.sub(
                r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE
            )
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()

        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "head", "meta", "link"]):
            element.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines)

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        attachment_path: Optional[Path] = None,
    ) -> Dict:
        """
        Send an email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML content of the email
            text_body: Optional plain text alternative
            attachment_path: Optional path to file to attach (e.g., MP3)

        Returns:
            Sent message metadata
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        # Use mixed multipart if we have an attachment, otherwise alternative
        if attachment_path:
            message = MIMEMultipart("mixed")
            # Create the body as an alternative part
            body_part = MIMEMultipart("alternative")
            if text_body:
                body_part.attach(MIMEText(text_body, "plain"))
            body_part.attach(MIMEText(html_body, "html"))
            message.attach(body_part)

            # Add the attachment
            attachment_path = Path(attachment_path)
            if attachment_path.suffix.lower() == ".mp3":
                with open(attachment_path, "rb") as f:
                    audio_part = MIMEAudio(f.read(), _subtype="mpeg")
                audio_part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment_path.name,
                )
                message.attach(audio_part)
            else:
                # Generic attachment
                with open(attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment_path.name,
                )
                message.attach(part)
        else:
            # Simple alternative message without attachment
            message = MIMEMultipart("alternative")
            if text_body:
                message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

        message["to"] = to
        message["subject"] = subject

        # Encode and send
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {"raw": raw}

        sent_message = (
            self.service.users().messages().send(userId="me", body=body).execute()
        )

        print(f"[OK] Email sent to {to}")
        return sent_message
