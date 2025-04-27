import threading
import time
import depthai as dai
from .framedistributor import FrameDistributor
from ..abstract.interfacedef import AbstractInputSource
import subprocess
import cv2
from typing import Optional

from dataclasses import dataclass
from ..config import DeviceConfig
from ..pkg.logger import get_logger
from ..pkg.logger import LogType

logger = get_logger(__name__, logType=LogType.SYSLOG)


class DAICameraInput(AbstractInputSource):
    def __init__(
        self,
        frame_width: int = 1920,
        frame_height: int = 1080,
        fps: int = 30,
        device_name: str = None,
        camera_socket: dai.CameraBoardSocket = dai.CameraBoardSocket.CAM_A,
        color_order: dai.ColorCameraProperties.ColorOrder = dai.ColorCameraProperties.ColorOrder.BGR,
        usb_speed: dai.UsbSpeed = dai.UsbSpeed.SUPER,
    ):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps = fps
        self.device_name = device_name
        self.camera_socket = camera_socket
        self.color_order = color_order
        self.usb_speed = usb_speed

        self._setup_pipeline()

        self.distributor = FrameDistributor()

    def _setup_pipeline(self):
        """Set up the DepthAI pipeline for the camera."""
        pipeline = dai.Pipeline()
        cam_rgb = pipeline.create(dai.node.ColorCamera)
        cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_A)
        cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        cam_rgb.setInterleaved(False)
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        cam_rgb.setPreviewSize(self.frame_width, self.frame_height)
        cam_rgb.setFps(self.fps)

        xout = pipeline.create(dai.node.XLinkOut)
        xout.setStreamName("video")
        cam_rgb.preview.link(xout.input)

        return pipeline

    def start(self):
        pipeline = self._setup_pipeline()
        self.device = dai.Device(pipeline)
        self.queue = self.device.getOutputQueue("video", maxSize=4, blocking=False)

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _worker_loop(self):
        while self.running:
            frame = self.queue.tryGet()
            if frame:
                cv_frame = frame.getCvFrame()
                self.distributor.distribute(cv_frame.tobytes())
            else:
                time.sleep(0.001)

    def stop(self):
        self.running = False
        if self.worker_thread:
            self.worker_thread.join()
        if self.device:
            self.device.close()
            self.device = None

    def release(self):
        self.stop()
        self.queue = None
        self.device = None

    def add_consumer(self, consumer_fn):
        self.distributor.add_consumer(consumer_fn)

    def remove_consumer(self, consumer_fn):
        self.distributor.remove_consumer(consumer_fn)


class RTSPInputSource(AbstractInputSource):
    def __init__(self, device_config: DeviceConfig):

        self.rtsp_url = device_config.ip_address
        self.cap = None
        self.running = False
        self.thread = None

        self.distributor = FrameDistributor()

    def start(self):
        if self.running:
            logger.warning("[RTSP Streamer] Stream already running")
            return
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if not self.cap.isOpened():
            logger.error("[RTSP Streamer] Cannot open RTSP stream")
            raise Exception("Cannot open RTSP stream")
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("[RTSP Streamer] RTSP stream started")

    def _run(self):
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("[RTSP Streamer] Failed to read frame")
                    break
                for consumer in list(self.consumers):
                    try:
                        consumer(frame)
                    except Exception as e:
                        logger.exception(f"[RTSP Streamer] Consumer function raised an exception: {e}")
        except Exception as e:
            logger.exception(f"[RTSP Streamer] Unhandled exception in _run: {e}")
        finally:
            self.stop()

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        if self.cap:
            self.cap.release()
        logger.info("[RTSP Streamer] RTSP stream stopped")

    def add_consumer(self, consumer_fn):
        if not callable(consumer_fn):
            raise ValueError("Consumer must be callable")
        self.distributor.add_consumer(consumer_fn)
        logger.info(f"[RTSP Streamer] Подключен {consumer_fn} added")

    def remove_consumer(self, consumer_fn):
        self.consumers.discard(consumer_fn)
        logger.info(f"[RTSP Streamer] Consumer {consumer_fn} removed")

    def release(self):
        self.stop()
