"""Pipeline orchestration and scheduled execution entry point."""

import argparse
import logging
import time
from datetime import datetime
from typing import Callable, Optional

from config import FEATURES, TIKTOK_UPLOAD, setup_logging
from content_generator import ContentGenerator
from downloader import VideoDownloader
from uploader import TikTokUploader
from video_processor import VideoProcessor

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Runs the pipeline stages in status-driven order."""

    def __init__(
        self,
        downloader: Optional[VideoDownloader] = None,
        processor: Optional[VideoProcessor] = None,
        content_generator: Optional[ContentGenerator] = None,
        uploader: Optional[TikTokUploader] = None,
        features: Optional[dict] = None,
    ):
        self.downloader = downloader or VideoDownloader()
        self.processor = processor or VideoProcessor()
        self.content_generator = content_generator or ContentGenerator()
        self.uploader = uploader or TikTokUploader()
        self.features = {**FEATURES, **(features or {})}

    def run_once(self) -> dict:
        """Execute all enabled stages once and return their summary."""
        summary = {"downloaded": [], "processed": [], "content_generated": [], "uploaded": [], "errors": {}}

        if self.features["enable_download"]:
            summary["downloaded"] = self._run_stage("download", self.downloader.scan_and_download, summary)
        if self.features["enable_processing"]:
            summary["processed"] = self._run_stage("process", self.processor.process_downloaded_videos, summary)
        if self.features["enable_content_generation"]:
            summary["content_generated"] = self._generate_content(summary)
        if self.features["enable_upload"] and not self.features["dry_run_mode"]:
            summary["uploaded"] = self._run_stage("upload", self.uploader.upload_ready_videos, summary)

        logger.info("Pipeline completed: %s", self._summary_counts(summary))
        return summary

    def _generate_content(self, summary: dict) -> list[int]:
        generated_ids = []
        try:
            for video in self.content_generator.database.get_videos_by_status("processed"):
                if self.content_generator.generate_content(video["id"], video["title"]):
                    generated_ids.append(video["id"])
        except Exception as error:
            summary["errors"]["content_generation"] = str(error)
            logger.exception("Content generation stage failed")
        return generated_ids

    @staticmethod
    def _run_stage(stage: str, operation: Callable, summary: dict) -> list:
        try:
            return operation()
        except Exception as error:
            summary["errors"][stage] = str(error)
            logger.exception("%s stage failed", stage.capitalize())
            return []

    @staticmethod
    def _summary_counts(summary: dict) -> dict:
        return {key: len(value) for key, value in summary.items() if isinstance(value, list)}


class PipelineScheduler:
    """Runs the pipeline once per configured clock time each day."""

    def __init__(
        self,
        runner: PipelineRunner,
        scheduled_times: Optional[list[str]] = None,
        now_provider: Callable[[], datetime] = datetime.now,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.runner = runner
        self.scheduled_times = scheduled_times or TIKTOK_UPLOAD["scheduled_times"]
        self.now_provider = now_provider
        self.sleeper = sleeper
        self.last_run_dates = {}

    def run_pending(self) -> Optional[dict]:
        """Run once when the current minute matches an unhandled schedule time."""
        now = self.now_provider()
        current_time = now.strftime("%H:%M")
        current_date = now.date()
        if current_time not in self.scheduled_times or self.last_run_dates.get(current_time) == current_date:
            return None

        self.last_run_dates[current_time] = current_date
        logger.info("Starting scheduled pipeline run for %s", current_time)
        return self.runner.run_once()

    def run_forever(self, poll_interval: int = 30) -> None:
        """Poll configured times until the process is stopped."""
        while True:
            self.run_pending()
            self.sleeper(poll_interval)


def main() -> None:
    """Run the pipeline once or keep the scheduler alive."""
    parser = argparse.ArgumentParser(description="Ganjing to TikTok pipeline")
    parser.add_argument("--once", action="store_true", help="Run all enabled stages once")
    parser.add_argument("--dry-run", action="store_true", help="Run without publishing to TikTok")
    args = parser.parse_args()

    setup_logging()
    features = {"dry_run_mode": args.dry_run} if args.dry_run else None
    runner = PipelineRunner(features=features)
    if args.once:
        runner.run_once()
    else:
        PipelineScheduler(runner).run_forever()


if __name__ == "__main__":
    main()