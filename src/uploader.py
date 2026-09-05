"""TikTok upload workflow with persistent browser sessions and safety limits."""

import logging
import os
import random
import time
from typing import Optional

from playwright.sync_api import sync_playwright

from config import PROCESSED_VIDEO_DIR, TIKTOK_UPLOAD
from database import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"


class CaptchaDetectedError(RuntimeError):
    """Raised when TikTok requires human verification."""


class TikTokUploader:
    """Uploads generated videos while enforcing the configured daily limit."""

    def __init__(
        self,
        database: Optional[DatabaseManager] = None,
        processed_video_dir: str = PROCESSED_VIDEO_DIR,
        upload_config: Optional[dict] = None,
        playwright_factory=sync_playwright,
        sleeper=time.sleep,
    ):
        self.database = database or get_db_manager()
        self.processed_video_dir = processed_video_dir
        self.config = upload_config or TIKTOK_UPLOAD
        self.playwright_factory = playwright_factory
        self.sleeper = sleeper

    def upload_ready_videos(self) -> list[int]:
        """Upload eligible videos until the daily limit is reached."""
        slots = self.config["max_daily_posts"] - self.database.get_stats().get("uploaded_today", 0)
        if slots <= 0:
            logger.info("Daily TikTok upload limit reached")
            return []

        uploaded_ids = []
        for video in self.database.get_videos_by_status("content_generated", limit=slots):
            if len(uploaded_ids) > 0:
                self.sleeper(random.uniform(self.config["post_delay_min"], self.config["post_delay_max"]))
            try:
                if self.upload_video(video):
                    uploaded_ids.append(video["id"])
            except CaptchaDetectedError:
                logger.warning("Upload paused because TikTok requires human verification")
                break
        return uploaded_ids

    def upload_video(self, video: dict) -> bool:
        """Upload one database video using the persistent TikTok browser session."""
        video_path = os.path.join(self.processed_video_dir, f"{video['ganjing_id']}.mp4")
        if not os.path.isfile(video_path):
            self._record_failure(video["id"], f"Processed video not found: {video_path}")
            return False

        description = self._build_description(video)
        try:
            with self.playwright_factory() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    self.config["session_data_dir"],
                    headless=self.config["headless"],
                )
                try:
                    page = context.pages[0] if context.pages else context.new_page()
                    page.goto(TIKTOK_UPLOAD_URL, wait_until="domcontentloaded")
                    self._raise_if_captcha(page)
                    selectors = self.config["selectors"]
                    page.locator(selectors["file_input"]).set_input_files(video_path)
                    page.locator(selectors["description"]).fill(description)
                    self._raise_if_captcha(page)
                    page.locator(selectors["post_button"]).click()
                    page.wait_for_load_state("networkidle")
                    self._raise_if_captcha(page)
                    self.database.update_video_status(video["id"], "uploaded")
                    self.database.log_processing_step(video["id"], "upload", "Video uploaded to TikTok")
                    return True
                finally:
                    context.close()
        except CaptchaDetectedError:
            self.database.log_processing_step(video["id"], "upload", "CAPTCHA detected; upload paused", "warning")
            raise
        except Exception as error:
            self._record_failure(video["id"], f"TikTok upload failed: {error}")
            return False

    def _raise_if_captcha(self, page) -> None:
        if page.locator(self.config["selectors"]["captcha"]).count() > 0:
            raise CaptchaDetectedError("TikTok CAPTCHA detected")

    @staticmethod
    def _build_description(video: dict) -> str:
        return "\n".join(part for part in [video.get("tiktok_title", ""), video.get("tiktok_hashtags", "")] if part).strip()

    def _record_failure(self, video_id: int, message: str) -> None:
        self.database.update_video_status(video_id, "failed", message)
        self.database.log_processing_step(video_id, "upload", message, "failure")
        logger.error("Video %s: %s", video_id, message)