"""Offline tests for the public-video downloader module."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from database import DatabaseManager
from downloader import VideoDownloader


class FakeResponse:
    def __init__(self, chunks=None, error=None):
        self.chunks = chunks or [b"video-data"]
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def raise_for_status(self):
        if self.error:
            raise self.error

    def iter_content(self, chunk_size):
        return iter(self.chunks)


class VideoDownloaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = DatabaseManager(os.path.join(self.temp_dir.name, "pipeline.db"))
        self.raw_dir = os.path.join(self.temp_dir.name, "raw")
        self.videos = []
        self.responses = []
        self.downloader = VideoDownloader(
            database=self.database,
            channel_url="https://www.ganjingworld.com/tag/example",
            raw_video_dir=self.raw_dir,
            min_duration=10,
            max_duration=600,
            video_fetcher=lambda: self.videos,
            http_get=lambda *args, **kwargs: self.responses.pop(0),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_downloads_only_new_eligible_videos(self):
        self.database.add_video("existing", "https://example.com/existing", "Existing")
        self.videos = [self._video("new"), self._video("existing"), self._video("short", 9), self._video("long", 601)]
        self.responses = [FakeResponse()]

        self.assertEqual(self.downloader.scan_and_download(), ["new"])
        self.assertTrue(os.path.isfile(os.path.join(self.raw_dir, "new.mp4")))
        self.assertEqual(self.database.get_video_by_ganjing_id("new")["status"], "downloaded")

    def test_download_failure_is_recorded_and_partial_file_removed(self):
        self.responses = [FakeResponse(error=RuntimeError("network unavailable"))]

        self.assertFalse(self.downloader.download_video(self._video("broken")))
        record = self.database.get_video_by_ganjing_id("broken")
        self.assertEqual(record["status"], "failed")
        self.assertIn("network unavailable", record["error_message"])
        self.assertFalse(os.path.exists(os.path.join(self.raw_dir, "broken.mp4")))

    def test_missing_media_url_is_rejected(self):
        self.videos = [{"id": "missing", "webpage_url": "https://example.com/video", "duration": 60}]

        self.assertEqual(self.downloader.scan_and_download(), [])

    def test_placeholder_video_url_is_rejected(self):
        self.assertFalse(VideoDownloader._is_video_page_url("https://example.com/video/undefined"))
        self.assertFalse(VideoDownloader._is_video_page_url("https://example.com/video/null"))
        self.assertTrue(VideoDownloader._is_video_page_url("https://example.com/video/abc123"))

    @staticmethod
    def _video(video_id, duration=60):
        return {
            "id": video_id,
            "webpage_url": f"https://www.ganjingworld.com/video/{video_id}",
            "media_url": f"https://media.example.com/{video_id}.mp4",
            "title": video_id,
            "duration": duration,
        }


if __name__ == "__main__":
    unittest.main()