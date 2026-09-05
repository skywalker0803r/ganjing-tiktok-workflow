"""Video discovery and download support for the pipeline."""

import logging
import os
from typing import Any, Dict, List, Optional

import yt_dlp

from config import GANJING_CHANNEL_URL, GANJING_VIDEO_MAX_LENGTH, GANJING_VIDEO_MIN_LENGTH, RAW_VIDEO_DIR
from database import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Discovers eligible channel videos and saves new ones locally."""

    def __init__(
        self,
        database: Optional[DatabaseManager] = None,
        channel_url: str = GANJING_CHANNEL_URL,
        raw_video_dir: str = RAW_VIDEO_DIR,
        min_duration: int = GANJING_VIDEO_MIN_LENGTH,
        max_duration: int = GANJING_VIDEO_MAX_LENGTH,
    ):
        self.database = database or get_db_manager()
        self.channel_url = channel_url
        self.raw_video_dir = raw_video_dir
        self.min_duration = min_duration
        self.max_duration = max_duration
        os.makedirs(self.raw_video_dir, exist_ok=True)

    def fetch_channel_videos(self) -> List[Dict[str, Any]]:
        """Return metadata for videos listed in the configured channel."""
        options = {
            "extract_flat": "discard_in_playlist",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(options) as downloader:
            result = downloader.extract_info(self.channel_url, download=False)

        return [entry for entry in (result.get("entries") or []) if entry]

    def is_eligible(self, video: Dict[str, Any]) -> bool:
        """Check whether a video includes required metadata and duration."""
        duration = video.get("duration")
        return (
            bool(video.get("id"))
            and bool(video.get("url") or video.get("webpage_url"))
            and isinstance(duration, (int, float))
            and self.min_duration <= duration <= self.max_duration
        )

    def download_video(self, video: Dict[str, Any]) -> bool:
        """Download one video and persist its resulting pipeline status."""
        ganjing_id = video["id"]
        if self.database.get_video_by_ganjing_id(ganjing_id):
            logger.info("Skipping existing video: %s", ganjing_id)
            return False

        video_url = video.get("webpage_url") or video["url"]
        title = video.get("title") or ganjing_id
        video_id = self.database.add_video(ganjing_id, video_url, title)
        if video_id == -1:
            return False

        options = {
            "format": "best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(self.raw_video_dir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.extract_info(video_url, download=True)
            self.database.update_video_status(video_id, "downloaded")
            self.database.log_processing_step(video_id, "download", "Video downloaded successfully")
            logger.info("Downloaded video: %s", ganjing_id)
            return True
        except Exception as error:
            message = f"Download failed: {error}"
            self.database.update_video_status(video_id, "failed", message)
            self.database.log_processing_step(video_id, "download", message, "failure")
            logger.exception("Failed to download video: %s", ganjing_id)
            return False

    def scan_and_download(self) -> List[str]:
        """Download each new, eligible video from the configured channel."""
        downloaded_ids = []
        for video in self.fetch_channel_videos():
            if not self.is_eligible(video):
                logger.info("Skipping ineligible video: %s", video.get("id", "unknown"))
                continue
            if self.download_video(video):
                downloaded_ids.append(video["id"])
        return downloaded_ids