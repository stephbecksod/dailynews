"""Generate HTML briefing from processed stories."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from .config import get_config


class BriefingGenerator:
    """Generate HTML email briefing from deduplicated stories."""

    def __init__(self):
        """Initialize the generator with Jinja2 environment."""
        self.config = get_config()

        # Setup Jinja2 template loader
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
        )

    def generate(
        self,
        processed_data: Dict[str, Any],
        newsletters_processed: List[str],
    ) -> Dict[str, str]:
        """
        Generate HTML and text briefing.

        Args:
            processed_data: Output from deduplicator with ranked stories
            newsletters_processed: List of newsletter names that were processed

        Returns:
            Dictionary with 'html', 'text', and 'subject' keys
        """
        today = datetime.now()
        date_str = today.strftime("%B %d, %Y")
        weekday = today.strftime("%A")

        # Extract data
        top_stories = processed_data.get("top_stories", [])
        secondary_stories = processed_data.get("secondary_stories", [])
        other_stories = processed_data.get("other_stories", [])
        summary = processed_data.get("deduplication_summary", {})

        # Build subject line
        subject = self._build_subject(date_str, top_stories)

        # Build executive summary
        exec_summary = self._build_executive_summary(top_stories)

        # Render HTML
        template = self.env.get_template("briefing_template.html")
        html = template.render(
            date=date_str,
            weekday=weekday,
            executive_summary=exec_summary,
            top_stories=top_stories,
            secondary_stories=secondary_stories,
            other_stories=other_stories,
            newsletters_processed=newsletters_processed,
            total_stories=summary.get("deduplicated_story_count", len(top_stories) + len(secondary_stories) + len(other_stories)),
            original_count=summary.get("original_story_count", 0),
        )

        # Build plain text version
        text = self._build_plain_text(
            date_str,
            exec_summary,
            top_stories,
            secondary_stories,
            newsletters_processed,
        )

        return {
            "html": html,
            "text": text,
            "subject": subject,
        }

    def _build_subject(self, date_str: str, top_stories: List[Dict]) -> str:
        """Build email subject line."""
        prefix = self.config.subject_prefix

        if top_stories:
            # Use top story headline (truncated)
            top_headline = top_stories[0].get("headline", "")[:60]
            if len(top_stories[0].get("headline", "")) > 60:
                top_headline += "..."
            return f"{prefix} {date_str}: {top_headline}"

        return f"{prefix} {date_str}"

    def _build_executive_summary(self, top_stories: List[Dict]) -> List[str]:
        """Build executive summary bullets from top stories."""
        summary = []
        for story in top_stories[:5]:
            headline = story.get("headline", "")
            why = story.get("why_it_matters", "")
            if headline and why:
                summary.append(f"{headline}: {why}")
            elif headline:
                summary.append(headline)
        return summary

    def _build_plain_text(
        self,
        date_str: str,
        exec_summary: List[str],
        top_stories: List[Dict],
        secondary_stories: List[Dict],
        newsletters: List[str],
    ) -> str:
        """Build plain text version of briefing."""
        lines = [
            f"AI NEWS BRIEFING - {date_str}",
            "=" * 50,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 30,
        ]

        for bullet in exec_summary:
            lines.append(f"• {bullet}")

        lines.extend(["", "TOP STORIES", "-" * 30])

        for i, story in enumerate(top_stories, 1):
            lines.append(f"\n{i}. {story.get('headline', '')}")
            lines.append(f"   {story.get('summary', '')}")
            if story.get("why_it_matters"):
                lines.append(f"   Why it matters: {story['why_it_matters']}")
            sources = ", ".join(story.get("sources", []))
            if sources:
                lines.append(f"   Sources: {sources}")

        if secondary_stories:
            lines.extend(["", "MORE STORIES", "-" * 30])
            for story in secondary_stories:
                lines.append(f"• {story.get('headline', '')}")
                lines.append(f"  {story.get('summary', '')}")

        lines.extend([
            "",
            "-" * 50,
            f"Sources: {', '.join(newsletters)}",
        ])

        return "\n".join(lines)
