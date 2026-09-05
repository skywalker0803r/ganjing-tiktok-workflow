"""Video conversion support for the Ganjing to TikTok pipeline."""

import glob
import logging
import os
from typing import Optional

import ffmpeg

from config import (
    PROCESSED_VIDEO_DIR,
    RAW_VIDEO_DIR,
    TIKTOK_TARGET_BITRATE,
    TIKTOK_TARGET_FPS,
    TIKTOK_TARGET_RESOLUTION,
    VIDEO_PROCESSING,
)
from database import DatabaseManager, get_db_manager

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Converts downloaded videos into TikTok-compatible portrait MP4 files."""

    def __init__(
        self,
        database: Optional[DatabaseManager] = None,
        raw_video_dir: str = RAW_VIDEO_DIR,
        processed_video_dir: str = PROCESSED_VIDEO_DIR,
        processing_config: Optional[dict] = None,
    ):
        self.database = database or get_db_manager()
        self.raw_video_dir = raw_video_dir
        self.processed_video_dir = processed_video_dir
        self.processing_config = processing_config or VIDEO_PROCESSING["format_conversion"]
        os.makedirs(self.processed_video_dir, exist_ok=True)

    def process_video(self, video_id: int, input_path: str) -> Optional[str]:
        """Convert one source file and record its processing outcome."""
        if not os.path.isfile(input_path):
            self._record_failure(video_id, f"Source video not found: {input_path}")
            return None

        output_path = os.path.join(
            self.processed_video_dir,
            f"{os.path.splitext(os.path.basename(input_path))[0]}.mp4",
        )
        try:
            self._render(input_path, output_path)
            self.database.update_video_status(video_id, "processed")
            self.database.log_processing_step(video_id, "process", "Video converted to 9:16 MP4")
            logger.info("Processed video %s to %s", video_id, output_path)
            return output_path
        except ffmpeg.Error as error:
            stderr = getattr(error, "stderr", b"") or b""
            detail = stderr.decode("utf-8", errors="replace").strip() or str(error)
            self._record_failure(video_id, f"Video processing failed: {detail}")
            return None
        except Exception as error:
            self._record_failure(video_id, f"Video processing failed: {error}")
            return None

    def process_downloaded_videos(self) -> list[str]:
        """Process every downloaded video whose source file is present."""
        processed_paths = []
        for video in self.database.get_videos_by_status("downloaded"):
            source_paths = sorted(glob.glob(os.path.join(self.raw_video_dir, f"{video['ganjing_id']}.*")))
            if not source_paths:
                self._record_failure(video["id"], f"Source video not found for {video['ganjing_id']}")
                continue
            output_path = self.process_video(video["id"], source_paths[0])
            if output_path:
                processed_paths.append(output_path)
        return processed_paths

    def _render(self, input_path: str, output_path: str) -> None:
        source = ffmpeg.input(input_path)
        video_stream = self._build_video_stream(source.video)
        streams = [video_stream]
        output_options = {
            "vcodec": "libx264",
            "pix_fmt": "yuv420p",
            "r": TIKTOK_TARGET_FPS,
            "video_bitrate": TIKTOK_TARGET_BITRATE,
            "movflags": "+faststart",
        }
        if self._has_audio(input_path):
            streams.append(source.audio)
            output_options["acodec"] = "aac"

        output = ffmpeg.output(*streams, output_path, **output_options)
        ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)

    def _build_video_stream(self, stream):
        width, height = TIKTOK_TARGET_RESOLUTION
        mode = self.processing_config.get("mode", "blur_background")
        if mode == "center_crop":
            return (
                stream.filter("scale", width, height, force_original_aspect_ratio="increase")
                .filter("crop", width, height)
            )

        blur_strength = self.processing_config.get("background_blur_strength", 15)
        background = (
            stream.filter("scale", width, height, force_original_aspect_ratio="increase")
            .filter("crop", width, height)
            .filter("boxblur", luma_radius=blur_strength, luma_power=1)
        )
        foreground = stream.filter("scale", width, height, force_original_aspect_ratio="decrease")
        return ffmpeg.overlay(background, foreground, x="(W-w)/2", y="(H-h)/2")

    @staticmethod
    def _has_audio(input_path: str) -> bool:
        metadata = ffmpeg.probe(input_path)
        return any(stream.get("codec_type") == "audio" for stream in metadata.get("streams", []))

    def _record_failure(self, video_id: int, message: str) -> None:
        self.database.update_video_status(video_id, "failed", message)
        self.database.log_processing_step(video_id, "process", message, "failure")
        logger.error("Video %s: %s", video_id, message)