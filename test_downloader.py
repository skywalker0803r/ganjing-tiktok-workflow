"""Offline tests for the video downloader module."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from database import DatabaseManager
from downloader import VideoDownloader


class FakeYoutubeDL:
    """Minimal yt-dlp replacement that records requested downloads."""

    channel_entries = []
    download_error = None
    downloaded_urls = []

    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def extract_info(self, url, download):
        if not download:
            return {"entries": self.channel_entries}
        self.downloaded_urls.append(url)
        if self.download_error:
            raise self.download_error
        return {"id": "downloaded"}


class VideoDownloaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = DatabaseManager(os.path.join(self.temp_dir.name, "pipeline.db"))
        self.raw_dir = os.path.join(self.temp_dir.name, "raw")
        FakeYoutubeDL.channel_entries = []
        FakeYoutubeDL.download_error = None
        FakeYoutubeDL.downloaded_urls = []
        self.downloader = VideoDownloader(
            database=self.database,
            channel_url="https://example.com/channel",
            raw_video_dir=self.raw_dir,
            min_duration=10,
            max_duration=600,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    def test_scan_downloads_only_new_eligible_videos(self):
        self.database.add_video("existing", "https://example.com/existing", "Existing")
        FakeYoutubeDL.channel_entries = [
            {"id": "new", "webpage_url": "https://example.com/new", "title": "New", "duration": 60},
            {"id": "existing", "webpage_url": "https://example.com/existing", "title": "Existing", "duration": 60},
            {"id": "short", "webpage_url": "https://example.com/short", "title": "Short", "duration": 9},
            {"id": "long", "webpage_url": "https://example.com/long", "title": "Long", "duration": 601},
        ]

        self.assertEqual(self.downloader.scan_and_download(), ["new"])
        self.assertEqual(FakeYoutubeDL.downloaded_urls, ["https://example.com/new"])
        self.assertEqual(self.database.get_video_by_ganjing_id("new")["status"], "downloaded")
        self.assertEqual(self.database.get_processing_logs(2)[0]["status"], "success")

    @patch("downloader.yt_dlp.YoutubeDL", FakeYoutubeDL)
    def test_download_failure_is_recorded(self):
        FakeYoutubeDL.download_error = RuntimeError("network unavailable")
        video = {"id": "broken", "webpage_url": "https://example.com/broken", "title": "Broken", "duration": 60}

        self.assertFalse(self.downloader.download_video(video))
        record = self.database.get_video_by_ganjing_id("broken")
        self.assertEqual(record["status"], "failed")
        self.assertIn("network unavailable", record["error_message"])


if __name__ == "__main__":
    unittest.main()