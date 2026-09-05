"""Offline tests for the TikTok uploader safety and state handling."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from database import DatabaseManager
from uploader import TikTokUploader


class FakeLocator:
    def __init__(self, count=0):
        self._count = count
        self.uploaded_file = None
        self.text = None
        self.clicked = False

    def count(self):
        return self._count

    def set_input_files(self, path):
        self.uploaded_file = path

    def fill(self, text):
        self.text = text

    def click(self):
        self.clicked = True


class FakePage:
    def __init__(self, captcha=False):
        self.captcha = captcha
        self.locators = {}

    def goto(self, url, wait_until):
        self.url = url

    def locator(self, selector):
        if selector not in self.locators:
            self.locators[selector] = FakeLocator(1 if self.captcha and "captcha" in selector else 0)
        return self.locators[selector]

    def wait_for_load_state(self, state):
        self.load_state = state


class FakeContext:
    def __init__(self, page):
        self.pages = [page]
        self.closed = False

    def close(self):
        self.closed = True


class FakePlaywrightFactory:
    def __init__(self, page):
        self.page = page
        self.context = FakeContext(page)
        self.started = False
        self.playwright = type("Playwright", (), {"chromium": self})()

    def __call__(self):
        return self

    def __enter__(self):
        self.started = True
        return self.playwright

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def launch_persistent_context(self, session_dir, headless):
        self.session_dir = session_dir
        self.headless = headless
        return self.context


class TikTokUploaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = DatabaseManager(os.path.join(self.temp_dir.name, "pipeline.db"))
        self.processed_dir = os.path.join(self.temp_dir.name, "processed")
        os.makedirs(self.processed_dir)
        self.config = {
            "max_daily_posts": 2,
            "post_delay_min": 0,
            "post_delay_max": 0,
            "session_data_dir": os.path.join(self.temp_dir.name, "session"),
            "headless": True,
            "selectors": {
                "file_input": "file",
                "description": "description",
                "post_button": "post",
                "captcha": "captcha",
            },
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def _add_ready_video(self, ganjing_id):
        video_id = self.database.add_video(ganjing_id, f"https://example.com/{ganjing_id}", ganjing_id)
        self.database.update_generated_content(video_id, "生成標題", "#標籤 #FYP")
        with open(os.path.join(self.processed_dir, f"{ganjing_id}.mp4"), "wb") as video_file:
            video_file.write(b"placeholder")
        return self.database.get_video_by_ganjing_id(ganjing_id)

    def test_upload_marks_video_uploaded(self):
        video = self._add_ready_video("ready")
        factory = FakePlaywrightFactory(FakePage())
        uploader = TikTokUploader(self.database, self.processed_dir, self.config, factory, lambda _: None)

        self.assertTrue(uploader.upload_video(video))
        self.assertEqual(self.database.get_video_by_ganjing_id("ready")["status"], "uploaded")
        self.assertIn("#標籤", factory.page.locators["description"].text)
        self.assertTrue(factory.page.locators["post"].clicked)

    def test_captcha_stops_batch_without_marking_video_failed(self):
        self._add_ready_video("blocked")
        factory = FakePlaywrightFactory(FakePage(captcha=True))
        uploader = TikTokUploader(self.database, self.processed_dir, self.config, factory, lambda _: None)

        self.assertEqual(uploader.upload_ready_videos(), [])
        self.assertEqual(self.database.get_video_by_ganjing_id("blocked")["status"], "content_generated")

    def test_daily_limit_prevents_browser_launch(self):
        uploaded_id = self.database.add_video("already", "https://example.com/already", "Already")
        self.database.update_video_status(uploaded_id, "uploaded")
        self.config["max_daily_posts"] = 1
        factory = FakePlaywrightFactory(FakePage())
        uploader = TikTokUploader(self.database, self.processed_dir, self.config, factory, lambda _: None)

        self.assertEqual(uploader.upload_ready_videos(), [])
        self.assertFalse(factory.started)


if __name__ == "__main__":
    unittest.main()