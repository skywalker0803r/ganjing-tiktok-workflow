"""Offline tests for the video processor module."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from database import DatabaseManager
from video_processor import VideoProcessor


class VideoProcessorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = DatabaseManager(os.path.join(self.temp_dir.name, "pipeline.db"))
        self.raw_dir = os.path.join(self.temp_dir.name, "raw")
        self.processed_dir = os.path.join(self.temp_dir.name, "processed")
        os.makedirs(self.raw_dir)
        self.processor = VideoProcessor(
            database=self.database,
            raw_video_dir=self.raw_dir,
            processed_video_dir=self.processed_dir,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _add_downloaded_video(self, ganjing_id):
        video_id = self.database.add_video(ganjing_id, f"https://example.com/{ganjing_id}", ganjing_id)
        self.database.update_video_status(video_id, "downloaded")
        input_path = os.path.join(self.raw_dir, f"{ganjing_id}.mp4")
        with open(input_path, "wb") as source_file:
            source_file.write(b"placeholder")
        return video_id, input_path

    @patch("video_processor.ffmpeg.run")
    @patch("video_processor.ffmpeg.probe", return_value={"streams": [{"codec_type": "audio"}]})
    def test_process_video_marks_record_processed_and_builds_portrait_filter(self, mock_probe, mock_run):
        video_id, input_path = self._add_downloaded_video("ready")

        output_path = self.processor.process_video(video_id, input_path)

        self.assertEqual(output_path, os.path.join(self.processed_dir, "ready.mp4"))
        self.assertEqual(self.database.get_video_by_ganjing_id("ready")["status"], "processed")
        command = " ".join(mock_run.call_args.args[0].compile())
        self.assertIn("boxblur", command)
        self.assertIn("1080", command)
        self.assertIn("1920", command)

    @patch("video_processor.ffmpeg.run", side_effect=RuntimeError("encoder unavailable"))
    @patch("video_processor.ffmpeg.probe", return_value={"streams": []})
    def test_processing_failure_is_recorded(self, mock_probe, mock_run):
        video_id, input_path = self._add_downloaded_video("broken")

        self.assertIsNone(self.processor.process_video(video_id, input_path))
        record = self.database.get_video_by_ganjing_id("broken")
        self.assertEqual(record["status"], "failed")
        self.assertIn("encoder unavailable", record["error_message"])


if __name__ == "__main__":
    unittest.main()