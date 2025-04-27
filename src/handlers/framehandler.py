import threading
from typing import List, Callable
from ..abstract.interfacedef import AbstractFrameDistributor


class FrameDistributor(AbstractFrameDistributor):
    """Concrete implementation that manages multiple consumers of frame data."""

    def __init__(self):
        self._consumers: List[Callable[[bytes], None]] = []
        self._lock = threading.Lock()

    def add_consumer(self, consumer_fn):
        with self._lock:
            if consumer_fn not in self._consumers:
                self._consumers.append(consumer_fn)

    def remove_consumer(self, consumer_fn):
        with self._lock:
            if consumer_fn in self._consumers:
                self._consumers.remove(consumer_fn)

    def distribute(self, frame_bytes):
        with self._lock:
            for consumer in self._consumers:
                try:
                    consumer(frame_bytes)
                except Exception as e:
                    print(f"Error in frame consumer: {e}")
