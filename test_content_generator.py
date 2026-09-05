"""Offline tests for the OpenAI content generator."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from content_generator import ContentGenerator
from database import DatabaseManager


class FakeCompletions:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error:
            raise self.error
        message = type("Message", (), {"content": self.content})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


class FakeClient:
    def __init__(self, content=None, error=None):
        completions = FakeCompletions(content, error)
        self.chat = type("Chat", (), {"completions": completions})()
        self.completions = completions


class ContentGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = DatabaseManager(os.path.join(self.temp_dir.name, "pipeline.db"))
        self.video_id = self.database.add_video("content-video", "https://example.com/video", "原始標題")
        self.database.update_video_status(self.video_id, "processed")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_content_saves_title_and_hashtags(self):
        client = FakeClient("標題: 你不能錯過的市場變化\nHashtags: #財經 #市場 #FYP")
        generator = ContentGenerator(database=self.database, client=client)

        content = generator.generate_content(self.video_id, "原始標題", "市場趨勢分析")

        self.assertEqual(content, {"title": "你不能錯過的市場變化", "hashtags": "#財經 #市場 #FYP"})
        record = self.database.get_video_by_ganjing_id("content-video")
        self.assertEqual(record["status"], "content_generated")
        self.assertEqual(record["tiktok_title"], content["title"])
        self.assertEqual(record["tiktok_hashtags"], content["hashtags"])
        self.assertEqual(client.completions.requests[0]["model"], "gpt-4o-mini")

    def test_generation_failure_is_recorded(self):
        generator = ContentGenerator(database=self.database, client=FakeClient(error=RuntimeError("service unavailable")))

        self.assertIsNone(generator.generate_content(self.video_id, "原始標題"))
        record = self.database.get_video_by_ganjing_id("content-video")
        self.assertEqual(record["status"], "failed")
        self.assertIn("service unavailable", record["error_message"])


if __name__ == "__main__":
    unittest.main()