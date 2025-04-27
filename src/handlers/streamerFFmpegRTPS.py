import subprocess
import threading
from ..abstract.interfacedef import AbstractRTPStreamer
from ..pkg.logger import LogType
from ..pkg.logger import get_logger

logger = get_logger(__name__, logType=LogType.BOTH)


class FFmpegRTPStreamer(AbstractRTPStreamer):
    """Handles sending raw frames to FFmpeg process for RTP streaming, supports dynamic profile switching."""

    def __init__(self, streamer_config: dict):

        self.width = streamer_config.get("resolution", {}).split("x")[0]
        self.height = streamer_config.get("resolution", {}).split("x")[1]
        self.fps = streamer_config.get("fps")
        self.output_url = streamer_config.get("output_url")
        self.profile = {
            "resolution": f"{self.width}x{self.height}",
            "bitrate": "4500k",  # Default bitrate
            "fps": str(self.fps),
        }
        self.proc = self._start_ffmpeg_process(self.profile)

    def _start_ffmpeg_process(self, profile):
        resolution = profile["resolution"]
        bitrate = profile["bitrate"]
        fps = profile["fps"]
        logger.info(f"[FFMPEG] Starting process with {resolution} {bitrate} {fps}")

        return subprocess.Popen(
            [
                "ffmpeg",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "bgr24",
                "-s",
                resolution,
                "-r",
                fps,
                "-i",
                "-",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-tune",
                "zerolatency",
                "-b:v",
                bitrate,
                "-x264-params",
                "keyint=30:scenecut=0:insert-vui=1",
                "-bsf:v",
                "h264_mp4toannexb",
                "-f",
                "rtp",
                f"rtp://{self.output_url}",
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def start_streaming(self):
        """Start the FFmpeg process for streaming."""
        if not self.proc:
            logger.error("[FFMPEG] Process not started.")
            return

        logger.info(f"[FFMPEG] Streaming to {self.output_url} with profile: {self.profile}")

    def stop_streaming(self):
        """Stop the FFmpeg process."""
        if self.proc:
            logger.info("[FFMPEG] Stopping streaming.")
            self.close()
        else:
            logger.error("[FFMPEG] Process not started or already closed.")

    def process_frame(self, frame_bytes: bytes):
        """Process a single frame and send it to FFmpeg."""
        self.consume_frame(frame_bytes)

    def consume_frame(self, frame_bytes: bytes):
        try:
            if self.proc and self.proc.stdin:
                self.proc.stdin.write(frame_bytes)
        except (BrokenPipeError, IOError) as e:
            logger.error(f"[FFMPEG] Pipe closed while sending frame: {str(e)}")

    def apply_profile(self, profile: dict):
        """Dynamically apply a new encoding profile (resolution, bitrate, fps)."""
        if not profile:
            logger.error("[FFMPEG] No profile provided to apply.")
            return

        logger.info(f"[FFMPEG] Applying new profile: {profile}")

        # Save profile
        self.profile = profile

        # Restart FFmpeg process
        self.close()
        self.proc = self._start_ffmpeg_process(self.profile)

    def close(self):
        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
                self.proc.wait(timeout=0.5)
                if self.proc.poll() is None:
                    self.proc.terminate()
                    self.proc.wait(timeout=1)
                logger.info("[FFMPEG] Process closed successfully.")
            except Exception as e:
                logger.error(f"[FFMPEG] Error closing FFmpeg process: {str(e)}")
            self.proc = None
