"""Offline tests for pipeline orchestration and scheduling."""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from main import PipelineRunner, PipelineScheduler


class FakeDownloader:
    def __init__(self):
        self.calls = 0

    def scan_and_download(self):
        self.calls += 1
        return ["new-video"]


class FakeProcessor:
    def __init__(self):
        self.calls = 0

    def process_downloaded_videos(self):
        self.calls += 1
        return ["/tmp/new-video.mp4"]


class FakeDatabase:
    def get_videos_by_status(self, status):
        return [{"id": 7, "title": "Original title"}] if status == "processed" else []


class FakeContentGenerator:
    def __init__(self):
        self.database = FakeDatabase()
        self.calls = []

    def generate_content(self, video_id, title):
        self.calls.append((video_id, title))
        return {"title": "Generated", "hashtags": "#FYP"}


class FakeUploader:
    def __init__(self):
        self.calls = 0

    def upload_ready_videos(self):
        self.calls += 1
        return [7]


class PipelineRunnerTests(unittest.TestCase):
    def setUp(self):
        self.downloader = FakeDownloader()
        self.processor = FakeProcessor()
        self.generator = FakeContentGenerator()
        self.uploader = FakeUploader()

    def test_run_once_executes_all_enabled_stages(self):
        runner = PipelineRunner(self.downloader, self.processor, self.generator, self.uploader)

        summary = runner.run_once()

        self.assertEqual(summary["downloaded"], ["new-video"])
        self.assertEqual(summary["processed"], ["/tmp/new-video.mp4"])
        self.assertEqual(summary["content_generated"], [7])
        self.assertEqual(summary["uploaded"], [7])
        self.assertEqual(self.generator.calls, [(7, "Original title")])

    def test_dry_run_skips_upload_only(self):
        runner = PipelineRunner(
            self.downloader,
            self.processor,
            self.generator,
            self.uploader,
            features={"dry_run_mode": True},
        )

        summary = runner.run_once()

        self.assertEqual(summary["uploaded"], [])
        self.assertEqual(self.uploader.calls, 0)
        self.assertEqual(self.generator.calls, [(7, "Original title")])


class PipelineSchedulerTests(unittest.TestCase):
    def test_schedule_runs_once_per_time_per_day(self):
        runner = type("Runner", (), {"calls": 0, "run_once": lambda self: setattr(self, "calls", self.calls + 1) or {"ok": True}})()
        now = datetime(2026, 9, 5, 12, 0)
        scheduler = PipelineScheduler(runner, ["12:00"], lambda: now, lambda _: None)

        self.assertEqual(scheduler.run_pending(), {"ok": True})
        self.assertIsNone(scheduler.run_pending())
        self.assertEqual(runner.calls, 1)


if __name__ == "__main__":
    unittest.main()