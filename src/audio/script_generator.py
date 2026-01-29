"""Generate podcast script from briefing data."""

from datetime import datetime
from typing import Any, Dict, List


class ScriptGenerator:
    """Convert briefing data into a natural spoken script."""

    def generate(
        self,
        processed_data: Dict[str, Any],
        newsletters_processed: List[str],
    ) -> str:
        """
        Generate a podcast script from processed briefing data.

        Args:
            processed_data: Output from deduplicator with ranked stories
            newsletters_processed: List of newsletter names that were processed

        Returns:
            Script text ready for TTS
        """
        today = datetime.now()
        date_spoken = today.strftime("%A, %B %d")  # "Wednesday, January 28"

        top_stories = processed_data.get("top_stories", [])
        secondary_stories = processed_data.get("secondary_stories", [])

        sections = []

        # Intro
        sections.append(self._generate_intro(date_spoken, len(top_stories)))

        # Executive summary (quick headlines)
        sections.append(self._generate_executive_summary(top_stories))

        # Top stories in detail
        sections.append(self._generate_top_stories(top_stories))

        # Secondary stories (brief mentions)
        if secondary_stories:
            sections.append(self._generate_secondary_stories(secondary_stories))

        # Outro
        sections.append(self._generate_outro(newsletters_processed))

        return "\n\n".join(sections)

    def _generate_intro(self, date_spoken: str, story_count: int) -> str:
        """Generate the intro section."""
        return (
            f"Good morning. Here's your AI news briefing for {date_spoken}. "
            f"Today I have {story_count} top stories for you, plus a roundup of other notable developments."
        )

    def _generate_executive_summary(self, top_stories: List[Dict]) -> str:
        """Generate quick headline summary."""
        if not top_stories:
            return ""

        lines = ["First, a quick overview of today's top headlines."]

        for story in top_stories[:5]:
            headline = story.get("headline", "")
            if headline:
                lines.append(headline + ".")

        return " ".join(lines)

    def _generate_top_stories(self, top_stories: List[Dict]) -> str:
        """Generate detailed coverage of top stories."""
        if not top_stories:
            return ""

        sections = ["Now, let's dive into the details."]

        for i, story in enumerate(top_stories, 1):
            headline = story.get("headline", "")
            summary = story.get("summary", "")
            why_it_matters = story.get("why_it_matters", "")
            sources = story.get("sources", [])
            mention_count = story.get("mention_count", 1)

            # Story intro
            if i == 1:
                story_text = f"Our top story today: {headline}. "
            elif i == len(top_stories):
                story_text = f"And finally in our top stories: {headline}. "
            else:
                story_text = f"Next up: {headline}. "

            # Summary
            if summary:
                story_text += summary + " "

            # Why it matters
            if why_it_matters:
                story_text += f"Why this matters: {why_it_matters} "

            # Source attribution for multi-source stories
            if mention_count > 1 and sources:
                story_text += f"This story was covered by {mention_count} newsletters including {sources[0]}."

            sections.append(story_text.strip())

        return "\n\n".join(sections)

    def _generate_secondary_stories(self, secondary_stories: List[Dict]) -> str:
        """Generate brief coverage of secondary stories."""
        if not secondary_stories:
            return ""

        lines = [
            "Now for a quick roundup of other stories worth knowing about."
        ]

        for story in secondary_stories:
            headline = story.get("headline", "")
            summary = story.get("summary", "")

            if headline and summary:
                # Use first sentence of summary only for brevity
                first_sentence = summary.split(". ")[0]
                if not first_sentence.endswith("."):
                    first_sentence += "."
                lines.append(f"{headline}. {first_sentence}")
            elif headline:
                lines.append(f"{headline}.")

        return " ".join(lines)

    def _generate_outro(self, newsletters: List[str]) -> str:
        """Generate the outro section."""
        source_text = ", ".join(newsletters[:-1])
        if len(newsletters) > 1:
            source_text += f", and {newsletters[-1]}"
        else:
            source_text = newsletters[0] if newsletters else "various sources"

        return (
            f"That's your AI briefing for today. "
            f"This summary was compiled from {source_text}. "
            f"Have a great day, and I'll see you tomorrow."
        )
