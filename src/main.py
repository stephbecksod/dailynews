#!/usr/bin/env python3
"""
Daily AI News Briefing - Main Orchestrator

Fetches newsletters from Gmail, extracts stories using Claude,
deduplicates and ranks, generates audio podcast, then sends a formatted briefing email.
"""

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
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

    # Determine total steps (6 if audio enabled, 5 otherwise)
    total_steps = 6 if config.audio_enabled else 5

    # Step 1: Authenticate with Gmail
    print(f"\n[1/{total_steps}] Authenticating with Gmail...")
    gmail_client.authenticate()

    # Step 2: Fetch newsletters
    print(f"\n[2/{total_steps}] Fetching newsletters from the past day...")
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
    print(f"\n[2/{total_steps}] Fetching text from {len(email_list)} newsletters...")
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
    print(f"\n[3/{total_steps}] Extracting stories with Claude API...")

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
    print(f"\n[4/{total_steps}] Deduplicating and ranking stories...")

    def deduplicate():
        return deduplicator.process(raw_stories)

    processed_data = retry_with_backoff(
        deduplicate,
        max_attempts=config.max_retry_attempts,
        base_delay=config.retry_base_delay,
    )

    # Step 5: Generate audio (if enabled)
    audio_path = None
    if config.audio_enabled:
        print(f"\n[5/{total_steps}] Generating audio podcast...")
        try:
            from .audio import ScriptGenerator, TTSClient

            script_gen = ScriptGenerator()
            tts_client = TTSClient()

            # Generate script
            script = script_gen.generate(
                processed_data=processed_data,
                newsletters_processed=newsletters_processed,
            )

            # Estimate duration
            duration_mins = tts_client.estimate_duration(script)
            char_count = tts_client.get_character_count(script)
            print(f"  Script: {char_count} characters, ~{duration_mins:.1f} min")

            # Generate audio
            audio_path = Path("briefing_audio.mp3")

            def generate_audio():
                return tts_client.generate_audio(script, audio_path)

            audio_path = retry_with_backoff(
                generate_audio,
                max_attempts=config.max_retry_attempts,
                base_delay=config.retry_base_delay,
            )
        except Exception as e:
            print(f"  [WARNING] Audio generation failed: {e}")
            print("  [WARNING] Continuing without audio...")
            audio_path = None

    # Step 6: Generate and send briefing
    final_step = total_steps
    print(f"\n[{final_step}/{total_steps}] Generating and sending briefing...")

    briefing = generator.generate(
        processed_data=processed_data,
        newsletters_processed=newsletters_processed,
    )

    # Send the briefing (with audio if available)
    def send_email():
        return sender.send_briefing(briefing, audio_path=audio_path)

    sent_result = retry_with_backoff(
        send_email,
        max_attempts=config.max_retry_attempts,
        base_delay=config.retry_base_delay,
    )

    # Clean up audio file
    if audio_path and audio_path.exists():
        audio_path.unlink()

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
    print(f"Audio included: {'Yes' if audio_path else 'No'}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Email sent to: {config.recipient_email}")
    print("=" * 60)

    return {
        "success": True,
        "newsletters_found": len(email_list),
        "newsletters_processed": len(newsletters),
        "stories_extracted": len(raw_stories),
        "stories_after_dedup": total_stories,
        "audio_included": bool(audio_path),
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
