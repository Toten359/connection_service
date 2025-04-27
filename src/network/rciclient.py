import requests
import hashlib
from ..config import Config


from ..pkg.logger import get_logger
from ..pkg.logger import LogType


logger_text = get_logger(__name__, logType=LogType.SYSLOG)


class KeeneticRCIClient:
    def __init__(self, config: Config):
        self.session = requests.session()
        self.ip = config.ip
        self.login = config.login
        self.password = config.password
        self.timeout = config.timeout
        self.degradation_steps = config.degradation_steps
        logger_text.info("[Keenetic] Конфигурация загружена успешно.")
        logger_text.info("[Keenetic] Инициализация сессии...")

    def _request(self, path, post=None):
        url = f"http://{self.ip}/{path}"
        return self.session.post(url, json=post) if post else self.session.get(url)

    def authenticate(self) -> bool:
        r = self._request("auth")
        if r.status_code == 401:
            realm = r.headers.get("X-NDM-Realm", "")
            challenge = r.headers.get("X-NDM-Challenge", "")
            md5 = hashlib.md5(f"{self.login}:{realm}:{self.password}".encode()).hexdigest()
            sha256 = hashlib.sha256((challenge + md5).encode()).hexdigest()
            r = self._request("auth", {"login": self.login, "password": sha256})
            if r.status_code == 200:
                logger_text.info("[Keenetic] Аутентификация успешна")
                return True
            else:
                logger_text.error(f"[Keenetic] Ошибка аутентификации: {r.status_code}")
                return False
        elif r.status_code == 200:
            logger_text.info("[Keenetic] Уже авторизован")
            return True
        else:
            logger_text.error(f"[Keenetic] Ошибка аутентификации: {r.status_code}")
        return False

    @staticmethod
    def find_used_connection(data) -> str:
        active = ""
        priority = 0

        def recurse(node):
            nonlocal active, priority
            if isinstance(node, dict):
                if node.get("connected", "") == "yes" or node.get("status", "") == "connected":
                    if node.get("priority", 0) > priority:
                        active = node.get("id")
                        priority = node.get("priority", 0)
                for v in node.values():
                    recurse(v)
            elif isinstance(node, list):
                for item in node:
                    recurse(item)

        recurse(data)
        return active

    def get_connection_info(self):
        data: dict = self._request("rci/show/interface").json()
        connection = self.find_used_connection(data)
        if "WifiStation" == data.get(connection).get("type"):
            return self._calculate_wifi_quality(data.get(connection))
        return self._calculate_4g_signal_quality(data.get(connection))

    @staticmethod
    def _level_from_score(score, max_score=100, levels=5):
        step = max_score // levels
        level = min(levels, max(0, (max_score - score) // step))
        return level

    def _calculate_4g_signal_quality(self, connection: dict):
        rssi = float(connection["rssi"])
        rsrp = float(connection["rsrp"])
        cinr = float(connection["cinr"])

        def normalize(value, min_val, max_val):
            return max(0, min(1, (value - min_val) / (max_val - min_val)))

        rssi_norm = normalize(rssi, -80, -50)
        rsrp_norm = normalize(rsrp, -120, -85)
        cinr_norm = normalize(cinr, 0, 20)
        score = round(rssi_norm * 30 + rsrp_norm * 40 + cinr_norm * 30)
        return {"score": score, "level": self._level_from_score(score, 100, self.degradation_steps)}

    def _calculate_wifi_quality(self, connection: dict = None):
        rssi = float(connection["rssi"])
        noise = float(connection["noise"])
        mcs = float(connection["mcs"])
        nss = float(connection["nss"])

        def normalize(value, min_val, max_val):
            return max(0, min(1, (value - min_val) / (max_val - min_val)))

        snr = rssi - noise
        snr_norm = normalize(snr, 0, 50)
        mcs_norm = normalize(mcs, 0, 11)
        nss_norm = normalize(nss, 1, 4)
        score = round(snr_norm * 50 + mcs_norm * 30 + nss_norm * 20)
        return {"score": score, "level": self._level_from_score(score, 100, self.degradation_steps)}
