"""Deduplication and ranking of news stories using Claude API."""

import json
import re
from typing import Any, Dict, List

from anthropic import Anthropic

from .config import get_config


class Deduplicator:
    """Deduplicate and rank news stories using Claude API."""

    def __init__(self):
        """Initialize with Claude client."""
        self.config = get_config()
        self.client = Anthropic(
            api_key=self.config.anthropic_api_key,
            timeout=300.0,
        )

    def process(self, raw_stories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deduplicate and rank stories.

        Args:
            raw_stories: List of raw extracted stories

        Returns:
            Dictionary with categorized and ranked stories
        """
        if not raw_stories:
            return self._empty_result()

        print(f"\nProcessing {len(raw_stories)} raw stories...")

        system_prompt = self._build_system_prompt(len(raw_stories))
        user_prompt = self._build_user_prompt(raw_stories)

        try:
            # Use streaming for large responses
            response_text = ""
            with self.client.messages.stream(
                model=self.config.claude_model,
                max_tokens=self.config.claude_max_tokens,
                temperature=self.config.claude_temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    response_text += text

            result = self._parse_response(response_text)

            # Log summary
            print(f"\n[OK] Deduplication complete:")
            print(f"  Original: {len(raw_stories)} stories")
            print(f"  Top stories: {len(result.get('top_stories', []))}")
            print(f"  Secondary stories: {len(result.get('secondary_stories', []))}")
            print(f"  Other stories: {len(result.get('other_stories', []))}")

            return result

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON: {e}")
            return self._empty_result()
        except Exception as e:
            print(f"[ERROR] Failed to deduplicate: {e}")
            return self._empty_result()

    def _build_system_prompt(self, story_count: int) -> str:
        """Build the system prompt for deduplication and ranking."""
        major_companies = ", ".join(self.config.major_ai_companies)
        top_count = self.config.top_stories_count

        return f"""You are an AI assistant helping to deduplicate and rank news stories for a daily AI briefing.

You will receive {story_count} raw news stories extracted from newsletters. You must:

1. DEDUPLICATE:
   - Group overlapping stories that report on the same underlying event
   - When merging duplicates, keep:
     * Combined list of sources
     * Count of how many newsletters mentioned it
     * A clean final headline
     * A unified summary (combining best information from all sources)
     * All URLs from different sources
     * The earliest date

2. RANK STORIES by strategic significance:
   PRIMARY RANKING CRITERIA (in priority order):
   a) Strategic significance - Does this signal something bigger about AI's future?
   b) Multiple newsletter mentions - Stories covered by 2+ sources rank higher
   c) Major AI company involvement: {major_companies}
   d) Is it a launch vs general news

   HIGH-PRIORITY stories:
   - Platform/ecosystem changes
   - Controversy & safety issues
   - Strategic announcements from major players
   - Market structure changes

   MEDIUM-PRIORITY:
   - Major product launches
   - Significant funding rounds ($100M+)
   - Enterprise adoption news

3. CATEGORIZE:
   - top_stories: Top {top_count} most significant stories with why_it_matters
   - secondary_stories: Next 5-10 important stories with why_it_matters
   - other_stories: Everything else (include headline only)

4. For each top/secondary story, include "why_it_matters" - one sentence explaining strategic significance

OUTPUT FORMAT (JSON only):
{{
  "top_stories": [
    {{
      "headline": "Clean, compelling headline",
      "summary": "2-3 sentence summary of what happened",
      "why_it_matters": "One sentence explaining strategic significance",
      "sources": ["Newsletter 1", "Newsletter 2"],
      "mention_count": 2,
      "date": "YYYY-MM-DD",
      "urls": ["url1", "url2"],
      "is_launch": false,
      "companies_mentioned": ["OpenAI", "Google"]
    }}
  ],
  "secondary_stories": [ /* same format */ ],
  "other_stories": [
    {{ "headline": "Headline for lower-priority story" }}
  ],
  "deduplication_summary": {{
    "original_story_count": {story_count},
    "deduplicated_story_count": 0,
    "stories_merged": 0
  }}
}}

IMPORTANT:
- Be aggressive with deduplication - merge stories about the same event
- Include why_it_matters for top and secondary stories
- Output ONLY valid JSON, no other text"""

    def _build_user_prompt(self, stories: List[Dict[str, Any]]) -> str:
        """Build the user prompt with all stories."""
        stories_json = json.dumps(stories, indent=2, ensure_ascii=False)

        return f"""Here are the raw news stories to deduplicate and rank:

{stories_json}

Please deduplicate, rank, and categorize these stories. Return your response as valid JSON only."""

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's response and extract result."""
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

        return json.loads(json_text)

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "top_stories": [],
            "secondary_stories": [],
            "other_stories": [],
            "deduplication_summary": {
                "original_story_count": 0,
                "deduplicated_story_count": 0,
                "stories_merged": 0,
            },
        }
