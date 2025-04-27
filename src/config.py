from dataclasses import dataclass
import configparser
import os


@dataclass
class DeviceConfig:
    device_name: str
    output: str
    resolution: str
    bitrate: str
    fps: str
    ip_address: str = None
    stream_path: str = None


class Config:
    def __init__(self, config_path="main.conf"):
        self.config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file {config_path} not found")
        self.config.read(config_path)

        self.ip = self.config.get("Router", "ip_addr")
        self.login = self.config.get("Router", "login")
        self.password = self.config.get("Router", "password")

        self.timeout = self.config.get("settings", "timeout", fallback="5")
        self.connection_type = self.config.get("settings", "connection_type")
        self.stream_monitor_interval = int(self.config.get("settings", "stream_monitor_interval", fallback="60"))

        self.standard_resolution = self.config.get("Profile", "resolution")
        self.standard_bitrate = self.config.get("Profile", "bitrate")
        self.standard_fps = self.config.get("Profile", "fps")
        self.degradation_steps = int(self.config.get("Profile", "degradation_steps"))
        self.camera_login = self.config.get("Profile", "camera_login")
        self.camera_password = self.config.get("Profile", "camera_password")
        self.camera_port = self.config.get("Profile", "camera_port")
        self.camera_output = self.config.get("Profile", "camera_output")

        # Parse device configurations
        self.device_configs = {}
        self._parse_device_configs()

        # Connection check settings
        self.ping_ip = self.config.get("connection_check", "ping_ip")
        self.curl_url = self.config.get("connection_check", "curl_url")

        # Adaptive mode settings
        self.adaptive_mode = self.config.getboolean("adaptive_mode", "enabled", fallback=True)

    def _parse_device_configs(self):
        """Parse device configurations from the config file"""
        self.device_configs = {}
        input_devices_str = self.config.get("Profile", "input_devices", fallback="")

        if not input_devices_str:
            return

        devices = input_devices_str.split(",")
        for device in devices:
            parts = device.split(";")
            if len(parts) >= 3:
                device_name = parts[0].strip()
                ip_address = parts[1].strip()
                stream_path = parts[2].strip()

                full_stream_url = f"rtsp://{self.camera_login}:{self.camera_password}@{ip_address}:{self.camera_port}"

                device_config = DeviceConfig(
                    device_name=device_name,
                    output=self.camera_output,
                    resolution=self.standard_resolution,
                    bitrate=self.standard_bitrate,
                    fps=self.standard_fps,
                    ip_address=full_stream_url,
                    stream_path=stream_path,
                )

                self.device_configs[device_name] = device_config
            else:
                # Log warning for improperly formatted device entries
                print(f"Warning: Device entry '{device}' is not properly formatted. Expected format: 'name;ip;path'")

    def get_device_by_ip(self, ip_address):
        for device_name, device_config in self.device_configs.items():
            if device_config.ip_address == ip_address:
                return device_config
        return None
