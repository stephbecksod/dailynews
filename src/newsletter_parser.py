"""Newsletter parser using Claude API to extract news stories."""

import json
import re
from datetime import datetime
from typing import Any, Dict, List

from anthropic import Anthropic

from .config import get_config


class NewsletterParser:
    """Extract news stories from newsletter text using Claude API."""

    def __init__(self):
        """Initialize the parser with Claude client."""
        self.config = get_config()
        self.client = Anthropic(
            api_key=self.config.anthropic_api_key,
            timeout=300.0,
        )

    def extract_stories(self, newsletters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract news stories from multiple newsletters.

        Args:
            newsletters: List of newsletter data with text content

        Returns:
            List of extracted story dictionaries
        """
        all_stories = []

        for i, newsletter in enumerate(newsletters, 1):
            subject_preview = newsletter["subject"][:50]
            print(f"\n[{i}/{len(newsletters)}] Extracting stories from: {subject_preview}...")
            print(f"  From: {newsletter['from']}")
            print(f"  Text length: {len(newsletter.get('text', ''))} characters")

            # Skip if no meaningful content
            text = newsletter.get("text", "")
            if not text or len(text) < 100:
                print("  [SKIP] No meaningful text content")
                continue

            stories = self._extract_from_single(newsletter)
            print(f"  [OK] Extracted {len(stories)} stories")
            all_stories.extend(stories)

        return all_stories

    def _extract_from_single(self, newsletter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract stories from a single newsletter."""
        # Determine source name
        source_name = self.config.get_source_name(newsletter["from"])

        # Parse date
        newsletter_date = self._parse_date(newsletter.get("date", ""))

        # Build prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            source_name, newsletter_date, newsletter["subject"], newsletter["text"]
        )

        try:
            response = self.client.messages.create(
                model=self.config.claude_model,
                max_tokens=self.config.claude_max_tokens,
                temperature=self.config.claude_temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            response_text = response.content[0].text
            stories = self._parse_response(response_text)

            # Add source metadata to each story
            for story in stories:
                if "source" not in story or not story["source"]:
                    story["source"] = source_name
                if "date" not in story or not story["date"]:
                    story["date"] = newsletter_date

            return stories

        except json.JSONDecodeError as e:
            print(f"  [ERROR] Failed to parse JSON: {e}")
            return []
        except Exception as e:
            print(f"  [ERROR] Failed to extract stories: {e}")
            return []

    def _build_system_prompt(self) -> str:
        """Build the system prompt for story extraction."""
        return """You are an AI assistant helping to extract news stories from AI newsletters.

Your task:
1. Read through the newsletter content carefully
2. Identify and extract ONLY actual news stories
3. News includes: new partnerships, products, features, fundraising, valuations, company announcements, research breakthroughs
4. SKIP: tips, tools, tutorials, prompts, how-to guides, opinion pieces, commentary, ads, sponsored content

For each news story you find, extract:
- headline: Clear, descriptive headline (use newsletter's or write your own)
- source: Newsletter name
- date: Newsletter date (YYYY-MM-DD format)
- summary: 1-3 sentence summary of what happened
- url: Link to the full story if provided (null if not available)
- is_launch: true if this is a launch (new model, company, product, feature)

Output ONLY valid JSON in this exact format:
{
  "stories": [
    {
      "headline": "Story headline here",
      "source": "Newsletter name",
      "date": "YYYY-MM-DD",
      "summary": "Brief summary here",
      "url": "https://example.com or null",
      "is_launch": false
    }
  ]
}

Extract everything that qualifies as news. Do NOT deduplicate - that happens in a later step."""

    def _build_user_prompt(
        self, source_name: str, date: str, subject: str, text: str
    ) -> str:
        """Build the user prompt with newsletter content."""
        # Truncate very long newsletters to avoid token limits
        max_chars = 50000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated...]"

        return f"""Extract all news stories from this newsletter:

Newsletter: {source_name}
Date: {date}
Subject: {subject}

Content:
{text}

Extract all news stories and return them as JSON."""

    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse Claude's response and extract stories."""
        # Try to extract JSON from markdown code block
        json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                json_text = response_text

        result = json.loads(json_text)
        return result.get("stories", [])

    def _parse_date(self, date_str: str) -> str:
        """Parse email date string to YYYY-MM-DD format."""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")

        try:
            # Common email date format: "Mon, 27 Jan 2025 08:00:00 +0000"
            parsed = datetime.strptime(date_str[:16], "%a, %d %b %Y")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

        try:
            # Try alternative format
            parsed = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

        return datetime.now().strftime("%Y-%m-%d")
