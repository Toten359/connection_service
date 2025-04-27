from ..config import Config
from ..pkg.logger import LogType
from ..pkg.logger import get_logger


logger = get_logger(__name__, logType=LogType.SYSLOG)


class SignalPolicyEngine:
    def __init__(self, config: Config = None):
        if config is None:
            raise ValueError("config не может быть None")
        self.config = config
        self.create_degradation_profiles(config)

    def create_degradation_profiles(self, config: Config):
        base_profile = {
            "base Profile": None,
            "resolution": config.standard_resolution,
            "bitrate": config.standard_bitrate,
            "fps": config.standard_fps,
        }
        logger.info(base_profile)
        degradation_steps = config.degradation_steps
        if degradation_steps < 1:
            raise ValueError("Количество шагов деградации должно быть больше 0")
        if degradation_steps > 10:
            raise ValueError("Количество шагов деградации должно быть меньше 10")
        self.profiles = []
        for step in range(degradation_steps + 1):
            width, height = base_profile["resolution"].split("x")
            width = int(width) - step * (int(width) // degradation_steps)
            height = int(height) - step * (int(height) // degradation_steps)
            if width <= 1:
                width = 320
            if height <= 1:
                height = 240
            resolution = f"{width}x{height}"
            bitrate = f"{int(int(base_profile['bitrate'].split('k')[0]) * ((degradation_steps - step) / degradation_steps))}k"
            if int(bitrate.split("k")[0]) < 300:
                bitrate = "300k"
            fps = str(int(base_profile["fps"]) - step * 3 if int(base_profile["fps"]) - step * 3 > 0 else 1)
            if int(fps) < 10:
                fps = "12"
            self.profiles.append({"resolution": resolution, "bitrate": bitrate, "fps": fps})
        logger.info(f"[POLICY] Инициализация завершена с профилями: {self.profiles}")
        self.profiles = {i: profile for i, profile in enumerate(self.profiles)}
