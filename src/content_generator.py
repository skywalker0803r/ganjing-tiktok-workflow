"""OpenAI-backed TikTok title and hashtag generation."""

import logging
import re
from typing import Optional

from openai import OpenAI

from config import CONTENT_GENERATION_PROMPT, OPENAI_API_KEY, OPENAI_MODEL
from database import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates and stores TikTok-ready copy for processed videos."""

    def __init__(
        self,
        database: Optional[DatabaseManager] = None,
        api_key: str = OPENAI_API_KEY,
        model: str = OPENAI_MODEL,
        client=None,
    ):
        self.database = database or get_db_manager()
        self.model = model
        self.client = client or (OpenAI(api_key=api_key) if api_key else None)

    def generate_content(
        self,
        video_id: int,
        original_title: str,
        content_summary: str = "",
    ) -> Optional[dict]:
        """Generate and persist a title and hashtags for one video."""
        if not self.client:
            self._record_failure(video_id, "OpenAI API key is not configured")
            return None

        try:
            prompt = CONTENT_GENERATION_PROMPT.format(
                original_title=original_title,
                content_summary=content_summary or "未提供",
            )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
            )
            content = response.choices[0].message.content or ""
            generated = self.parse_response(content)
            if not self.database.update_generated_content(video_id, generated["title"], generated["hashtags"]):
                raise RuntimeError("Video record was not found")
            self.database.log_processing_step(video_id, "generate_content", "TikTok copy generated")
            return generated
        except Exception as error:
            self._record_failure(video_id, f"Content generation failed: {error}")
            return None

    @staticmethod
    def parse_response(content: str) -> dict:
        """Extract labelled title and hashtags from the configured prompt format."""
        title_match = re.search(r"(?:標題|title)\s*[:：]\s*(.+)", content, re.IGNORECASE)
        hashtags_match = re.search(r"(?:hashtags|標籤)\s*[:：]\s*(.+)", content, re.IGNORECASE)
        if not title_match or not hashtags_match:
            raise ValueError("Response must include labelled title and hashtags")

        title = title_match.group(1).strip()
        hashtags = " ".join(re.findall(r"#[\w]+", hashtags_match.group(1)))
        if not title or not hashtags:
            raise ValueError("Response did not contain a title and at least one hashtag")
        return {"title": title, "hashtags": hashtags}

    def _record_failure(self, video_id: int, message: str) -> None:
        self.database.update_video_status(video_id, "failed", message)
        self.database.log_processing_step(video_id, "generate_content", message, "failure")
        logger.error("Video %s: %s", video_id, message)