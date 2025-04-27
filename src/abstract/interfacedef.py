from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any
import subprocess
import threading
from dataclasses import dataclass
from ..config import DeviceConfig


class AbstractFrameDistributor(ABC):
    """Abstract base class for frame distribution."""

    @abstractmethod
    def add_consumer(self, consumer_fn: Callable):
        """Add a consumer function to receive frames."""
        pass

    @abstractmethod
    def remove_consumer(self, consumer_fn: Callable):
        """Remove a consumer function."""
        pass

    @abstractmethod
    def distribute(self, frame_bytes: bytes):
        """Distribute frame bytes to all registered consumers."""
        pass


class AbstractInputSource(ABC):
    """Base class for input sources"""

    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError

    @abstractmethod
    def add_consumer(self, consumer_fn):
        raise NotImplementedError

    @abstractmethod
    def remove_consumer(self, consumer_fn):
        raise NotImplementedError

    @abstractmethod
    def release(self):
        """Alias for stop."""
        self.stop()


class AbstractRTPStreamer(ABC):
    """Abstract base class for RTP streaming."""

    @abstractmethod
    def __init__(self, width, height, fps, host, port):
        """Initialize the RTP streamer with configuration parameters."""
        self.width = width
        self.height = height
        self.fps = fps
        self.host = host
        self.port = port
        self.proc = None

    @abstractmethod
    def consume_frame(self, frame_bytes: bytes):
        """Process and send a frame to the RTP stream."""
        pass

    @abstractmethod
    def close(self):
        """Clean up resources and close the stream."""
        pass

    @abstractmethod
    def apply_profile(self, profile: dict):
        """Apply a new encoding profile (resolution, bitrate, fps) to the RTP stream."""
        pass

    @abstractmethod
    def start_streaming(self):
        """Start the RTP streaming process."""
        pass

    @abstractmethod
    def stop_streaming(self):
        """Stop the RTP streaming process."""
        pass
