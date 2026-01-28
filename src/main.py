#!/usr/bin/env python3
"""
Daily AI News Briefing - Main Orchestrator

Fetches newsletters from Gmail, extracts stories using Claude,
deduplicates and ranks, then sends a formatted briefing email.
"""

import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import get_config
from .gmail_client import GmailClient
from .newsletter_parser import NewsletterParser
from .deduplicator import Deduplicator
from .briefing_generator import BriefingGenerator
from .email_sender import EmailSender


def retry_with_backoff(func, max_attempts: int = 3, base_delay: int = 5):
    """
    Retry a function with exponential backoff.

    Args:
        func: Function to call
        max_attempts: Maximum number of attempts
        base_delay: Base delay in seconds

    Returns:
        Function result

    Raises:
        Last exception if all attempts fail
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                print(f"[RETRY] Attempt {attempt + 1} failed: {e}")
                print(f"[RETRY] Waiting {delay} seconds before retry...")
                time.sleep(delay)

    raise last_exception


def run_pipeline() -> Dict[str, Any]:
    """
    Run the full briefing generation pipeline.

    Returns:
        Dictionary with pipeline results and metadata
    """
    config = get_config()
    start_time = datetime.now()

    print("=" * 60)
    print("DAILY AI NEWS BRIEFING")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Initialize components
    gmail_client = GmailClient()
    parser = NewsletterParser()
    deduplicator = Deduplicator()
    generator = BriefingGenerator()
    sender = EmailSender(gmail_client)

    # Step 1: Authenticate with Gmail
    print("\n[1/5] Authenticating with Gmail...")
    gmail_client.authenticate()

    # Step 2: Fetch newsletters
    print("\n[2/5] Fetching newsletters from the past day...")
    newsletter_emails = config.newsletter_emails

    def fetch_newsletters():
        emails = gmail_client.search_newsletters(
            sender_emails=newsletter_emails,
            days_back=1,
            max_results=20,
        )
        return emails

    email_list = retry_with_backoff(
        fetch_newsletters,
        max_attempts=config.max_retry_attempts,
        base_delay=config.retry_base_delay,
    )

    if not email_list:
        print("[WARNING] No newsletters found in the past day")
        return {
            "success": True,
            "newsletters_found": 0,
            "stories_extracted": 0,
            "briefing_sent": False,
            "message": "No newsletters found",
        }

    # Fetch full text for each newsletter
    print(f"\n[2/5] Fetching text from {len(email_list)} newsletters...")
    newsletters = []
    newsletters_processed = []

    for i, email in enumerate(email_list, 1):
        try:
            # Safely encode subject for Windows console (replace emojis with ?)
            subject_preview = email["subject"][:40].encode("ascii", "replace").decode("ascii")
            print(f"  [{i}/{len(email_list)}] Fetching: {subject_preview}...")
            email_data = gmail_client.get_email_text(email["id"])
            newsletters.append(email_data)
            source_name = config.get_source_name(email["from"])
            if source_name not in newsletters_processed:
                newsletters_processed.append(source_name)
        except Exception as e:
            print(f"  [ERROR] Failed to fetch email: {e}")

    print(f"[OK] Fetched {len(newsletters)} newsletters")

    if not newsletters:
        return {
            "success": True,
            "newsletters_found": len(email_list),
            "stories_extracted": 0,
            "briefing_sent": False,
            "message": "Failed to fetch newsletter content",
        }

    # Step 3: Extract stories
    print("\n[3/5] Extracting stories with Claude API...")

    def extract_stories():
        return parser.extract_stories(newsletters)

    raw_stories = retry_with_backoff(
        extract_stories,
        max_attempts=config.max_retry_attempts,
        base_delay=config.retry_base_delay,
    )

    print(f"[OK] Extracted {len(raw_stories)} raw stories")

    if not raw_stories:
        return {
            "success": True,
            "newsletters_found": len(email_list),
            "newsletters_processed": len(newsletters),
            "stories_extracted": 0,
            "briefing_sent": False,
            "message": "No stories extracted from newsletters",
        }

    # Step 4: Deduplicate and rank
    print("\n[4/5] Deduplicating and ranking stories...")

    def deduplicate():
        return deduplicator.process(raw_stories)

    processed_data = retry_with_backoff(
        deduplicate,
        max_attempts=config.max_retry_attempts,
        base_delay=config.retry_base_delay,
    )

    # Step 5: Generate and send briefing
    print("\n[5/5] Generating and sending briefing...")

    briefing = generator.generate(
        processed_data=processed_data,
        newsletters_processed=newsletters_processed,
    )

    # Send the briefing
    def send_email():
        return sender.send_briefing(briefing)

    sent_result = retry_with_backoff(
        send_email,
        max_attempts=config.max_retry_attempts,
        base_delay=config.retry_base_delay,
    )

    # Calculate stats
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    top_count = len(processed_data.get("top_stories", []))
    secondary_count = len(processed_data.get("secondary_stories", []))
    total_stories = top_count + secondary_count

    print("\n" + "=" * 60)
    print("BRIEFING COMPLETE")
    print("=" * 60)
    print(f"Newsletters processed: {len(newsletters)}")
    print(f"Raw stories extracted: {len(raw_stories)}")
    print(f"Unique stories after dedup: {total_stories}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Email sent to: {config.recipient_email}")
    print("=" * 60)

    return {
        "success": True,
        "newsletters_found": len(email_list),
        "newsletters_processed": len(newsletters),
        "stories_extracted": len(raw_stories),
        "stories_after_dedup": total_stories,
        "briefing_sent": True,
        "duration_seconds": duration,
        "message_id": sent_result.get("id"),
    }


def main():
    """Main entry point with error handling."""
    config = get_config()

    try:
        result = run_pipeline()

        if result["success"]:
            print("\n[SUCCESS] Daily briefing completed successfully")
            sys.exit(0)
        else:
            print(f"\n[WARNING] Pipeline completed with issues: {result.get('message')}")
            sys.exit(0)

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}"
        print(f"\n[ERROR] Pipeline failed: {error_msg}")

        # Try to send error notification
        try:
            gmail_client = GmailClient()
            gmail_client.authenticate()
            sender = EmailSender(gmail_client)
            sender.send_error_notification(error_msg)
            print("[OK] Error notification sent")
        except Exception as notify_error:
            print(f"[ERROR] Failed to send error notification: {notify_error}")

        sys.exit(1)


if __name__ == "__main__":
    main()
