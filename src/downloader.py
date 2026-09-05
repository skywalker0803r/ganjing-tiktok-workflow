"""Authorized public-video discovery and download support for the pipeline."""

import hashlib
import logging
import os
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import requests
from playwright.sync_api import sync_playwright

from config import GANJING_CHANNEL_URL, GANJING_DOWNLOAD, GANJING_VIDEO_MAX_LENGTH, GANJING_VIDEO_MIN_LENGTH, RAW_VIDEO_DIR
from database import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Discovers and downloads authorized, publicly playable MP4 videos."""

    def __init__(self, database: Optional[DatabaseManager] = None, channel_url: str = GANJING_CHANNEL_URL,
                 raw_video_dir: str = RAW_VIDEO_DIR, min_duration: int = GANJING_VIDEO_MIN_LENGTH,
                 max_duration: int = GANJING_VIDEO_MAX_LENGTH, source_config: Optional[dict] = None,
                 playwright_factory=sync_playwright, http_get: Callable = requests.get,
                 video_fetcher: Optional[Callable[[], List[Dict[str, Any]]]] = None):
        self.database = database or get_db_manager()
        self.channel_url = channel_url
        self.raw_video_dir = raw_video_dir
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.source_config = source_config or GANJING_DOWNLOAD
        self.playwright_factory = playwright_factory
        self.http_get = http_get
        self.video_fetcher = video_fetcher
        os.makedirs(self.raw_video_dir, exist_ok=True)

    def fetch_channel_videos(self) -> List[Dict[str, Any]]:
        """Return metadata for public videos linked by the configured source page."""
        if not self.channel_url:
            raise ValueError("GANJING_CHANNEL_URL is not configured")
        if self.video_fetcher:
            return self.video_fetcher()

        with self.playwright_factory() as playwright:
            browser = playwright.chromium.launch(headless=self.source_config["headless"])
            try:
                page = browser.new_page()
                page.goto(self.channel_url, wait_until="domcontentloaded")
                video_urls = page.locator(self.source_config["video_link_selector"]).evaluate_all(
                    "links => [...new Set(links.map(link => link.href))]"
                )
                valid_video_urls = [video_url for video_url in video_urls if self._is_video_page_url(video_url)]
                return [self._read_video_page(page, video_url) for video_url in valid_video_urls]
            finally:
                browser.close()

    def _read_video_page(self, page, video_url: str) -> Dict[str, Any]:
        """Read public player metadata without bypassing access controls."""
        page.goto(video_url, wait_until="domcontentloaded")
        player = page.locator(self.source_config["video_selector"]).first
        if player.count() == 0:
            raise ValueError(f"No public video player found: {video_url}")
        media_url = player.evaluate("player => player.currentSrc || player.src || ''")
        if not media_url or urlparse(media_url).scheme not in {"http", "https"}:
            raise ValueError(f"No downloadable public MP4 URL found: {video_url}")
        duration = player.evaluate("player => player.duration")
        title = page.locator('meta[property="og:title"]').get_attribute("content") or page.title()
        return {"id": self._video_id(video_url), "webpage_url": video_url, "media_url": media_url,
                "title": title, "duration": duration}

    @staticmethod
    def _video_id(video_url: str) -> str:
        path_part = urlparse(video_url).path.rstrip("/").split("/")[-1]
        return path_part or hashlib.sha256(video_url.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def _is_video_page_url(cls, video_url: str) -> bool:
        """Reject placeholder links emitted while the source page is rendering."""
        parsed_url = urlparse(video_url)
        return parsed_url.scheme in {"http", "https"} and cls._video_id(video_url).lower() not in {
            "undefined", "null"
        }

    def is_eligible(self, video: Dict[str, Any]) -> bool:
        """Check whether a video includes required metadata and duration."""
        duration = video.get("duration")
        return (bool(video.get("id")) and bool(video.get("webpage_url")) and bool(video.get("media_url"))
                and isinstance(duration, (int, float)) and self.min_duration <= duration <= self.max_duration)

    def download_video(self, video: Dict[str, Any]) -> bool:
        """Download one public MP4 video and persist its pipeline status."""
        ganjing_id = video["id"]
        if self.database.get_video_by_ganjing_id(ganjing_id):
            logger.info("Skipping existing video: %s", ganjing_id)
            return False
        video_id = self.database.add_video(ganjing_id, video["webpage_url"], video.get("title") or ganjing_id)
        if video_id == -1:
            return False
        output_path = os.path.join(self.raw_video_dir, f"{ganjing_id}.mp4")
        try:
            with self.http_get(video["media_url"], stream=True, timeout=60,
                               headers={"Referer": video["webpage_url"]}) as response:
                response.raise_for_status()
                with open(output_path, "wb") as output_file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output_file.write(chunk)
            self.database.update_video_status(video_id, "downloaded")
            self.database.log_processing_step(video_id, "download", "Video downloaded successfully")
            logger.info("Downloaded video: %s", ganjing_id)
            return True
        except Exception as error:
            if os.path.exists(output_path):
                os.remove(output_path)
            message = f"Download failed: {error}"
            self.database.update_video_status(video_id, "failed", message)
            self.database.log_processing_step(video_id, "download", message, "failure")
            logger.exception("Failed to download video: %s", ganjing_id)
            return False

    def scan_and_download(self) -> List[str]:
        """Download each new, eligible video from the configured source page."""
        downloaded_ids = []
        for video in self.fetch_channel_videos():
            if not self.is_eligible(video):
                logger.info("Skipping ineligible video: %s", video.get("id", "unknown"))
                continue
            if self.download_video(video):
                downloaded_ids.append(video["id"])
        return downloaded_ids