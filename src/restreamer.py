import threading
import time
from typing import Dict, Any

from .abstract.interfacedef import AbstractInputSource, AbstractRTPStreamer
from .config import Config, DeviceConfig
from .controller.signalpolicy import SignalPolicyEngine
from .handlers.inputsources import RTSPInputSource, DAICameraInput
from .handlers.streamerFFmpegRTPS import FFmpegRTPStreamer
from .network.rciclient import KeeneticRCIClient
from .network.connection_checker import ConnectionChecker
from .pkg.logger import get_logger, LogType


logger = get_logger(__name__, logType=LogType.BOTH)


class Restreamer:
    """
    Управляет множественными источниками видео и их перенаправлением с учётом качества сигнала.

    Поддерживает различное поведение при падении качества соединения:
    - Приоритизация DAI камеры при низком качестве подключения
    - Динамическая настройка параметров стрима для всех исходных потоков
    - Поддержка двух режимов: адаптивного с изменением качества и стандартного с фиксированными параметрами
    """

    def __init__(self, config: Config):
        """
        Инициализирует систему перенаправления потоков.

        Args:
            config: Объект конфигурации с настройками источников и целевых профилей
        """
        self.config = config
        self.signal_checker = KeeneticRCIClient(config)
        self.connection_validator = ConnectionChecker(config)
        self.input_sources: Dict[str, AbstractInputSource] = {}
        self.output_streamers: Dict[str, AbstractRTPStreamer] = {}
        self.policy_engines: Dict[str, SignalPolicyEngine] = {}
        self.monitoring_thread = None
        self.running = False
        self.current_signal_level = 0  # 0 - высокое качество, увеличивается при деградации

        # Настройка входных источников и выходных стримеров
        self._setup_sources()
        self._setup_streamers()

    def _setup_sources(self):
        """Настраивает входные источники видео на основе конфигурации."""
        for device_name, device_config in self.config.device_configs.items():
            # Пропускаем DAI камеру, которая настраивается отдельно
            if device_name == "oakd":
                dai_config: DeviceConfig = self.config.device_configs["oakd"]
                wight, height = map(int, dai_config.resolution.split("x"))
                ip_address = dai_config.ip_address.split("@")[1]
                self.input_sources["oakd"] = DAICameraInput(
                    frame_height=height, frame_width=wight, device_name=ip_address
                )
                logger.info(f"[RESTREAMER] Настроена DAI камера: {dai_config.device_name}")

            # Создаем экземпляр RTSPInputSource для RTSP-камеры с аутентификацией.
            logger.info(f"[RESTREAMER] Настраиваем источник для {device_name}: {device_config.ip_address}{device_config.stream_path}")
            self.input_sources[device_name] = RTSPInputSource(device_config)

            logger.info(
                f"[RESTREAMER] Настроен источник для {device_name}: {device_config.ip_address}{device_config.stream_path}"
            )

    def _setup_streamers(self):
        """Настраивает выходные стримеры для всех источников."""
        # Создаем выходные стримеры для каждого источника
        for source_id, source in self.input_sources.items():
            # Создаем и настраиваем политику качества для стримера
            policy = SignalPolicyEngine(self.config)
            policy.create_degradation_profiles(self.config)
            self.policy_engines[source_id] = policy.profiles
            logger.info(f"[RESTREAMER] Настроена политика качества для {source_id}: {policy.profiles}")

            # Создаем стример - используем конфигурацию из Config
            streamer_config = {
                "source_id": source_id,
                "output_url": f"rtp://{self.config.camera_output}/{source_id}",
                "resolution": self.config.standard_resolution,
                "bitrate": self.config.standard_bitrate,
                "fps": self.config.standard_fps,
            }
            self.output_streamers[source_id] = FFmpegRTPStreamer(streamer_config)

            # Подключаем источник к стримеру
            source.add_consumer(self.output_streamers[source_id].process_frame)
            logger.info(f"[RESTREAMER] Настроен стример для {source_id} с выводом на {streamer_config['output_url']}")

    def start_all_quality_mode(self):
        """
        Запускает все источники с одинаковыми профилями высокого качества.
        В этом режиме __не__ проводится адаптивное управление качеством.
        """
        standard_profile = {
            "resolution": self.config.standard_resolution,
            "bitrate": self.config.standard_bitrate,
            "fps": self.config.standard_fps,
        }

        # Запускаем все источники с одинаковым профилем
        for source_id, source in self.input_sources.items():
            source.start()
            logger.info(f"[RESTREAMER] Запущен источник {source_id} в режиме стандартного качества")

        # Запускаем все выходные стримеры
        for streamer_id, streamer in self.output_streamers.items():
            streamer.apply_profile(standard_profile)
            streamer.start_streaming()
            logger.info(f"[RESTREAMER] Запущен стример {streamer_id} в режиме стандартного качества")

        logger.info("[RESTREAMER] Все источники и стримеры запущены в режиме фиксированного качества")

    def start_adaptive_mode(self):
        """
        Запускает систему в адаптивном режиме с контролем качества сигнала.
        Мониторит соединение и применяет стратегии деградации при необходимости.
        """
        # Запускаем мониторинг соединения
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self.monitoring_thread.start()

        # Получаем профиль высшего качества из первого доступного policy engine
        policy_engine_keys = list(self.policy_engines.keys())
        if not policy_engine_keys:
            logger.error("[RESTREAMER] Не найдены policy engines! Невозможно запустить адаптивный режим")
            return

        high_quality_profile = self.policy_engines[policy_engine_keys[0]][0]

        # Запускаем все источники с максимальным качеством
        for source_id, source in self.input_sources.items():
            source.start()
            logger.info(
                f"[RESTREAMER] Запущен источник {source_id} в адаптивном режиме с профилем: {high_quality_profile}"
            )

        # Запускаем выходные стримеры
        for streamer_id, streamer in self.output_streamers.items():
            streamer.apply_profile(high_quality_profile)
            streamer.start_streaming()
            logger.info(f"[RESTREAMER] Запущен стример {streamer_id} в адаптивном режиме")

        logger.info("[RESTREAMER] Все источники и стримеры запущены в адаптивном режиме")

    def _monitor_connection(self):
        """
        Фоновая задача, отслеживающая качество соединения и применяющая
        соответствующие политики управления качеством.
        """
        while self.running:
            try:
                # Проверяем качество сигнала
                try:
                    self.signal_checker.authenticate()
                except Exception as e:
                    logger.error(f"[RESTREAMER] Ошибка аутентификации: {e}")
                    time.sleep(self.config.timeout + 5)
                    continue
                # Получаем уровень сигнала
                self.signal_checker.get_connection_info()
                signal_level = self.signal_checker.get_connection_info()

                if signal_level != self.current_signal_level:
                    logger.info(
                        f"[RESTREAMER] Изменение уровня сигнала с {self.current_signal_level} на {signal_level}"
                    )
                    self._apply_quality_policy(signal_level)
                    self.current_signal_level = signal_level

                check_interval = int(self.config.timeout) or 5  # По умолчанию 5 секунд
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"[RESTREAMER] Ошибка при мониторинге соединения: {e}")
                time.sleep(self.config.timeout + 5)  # При ошибке увеличиваем интервал проверки

    def _apply_quality_policy(self, signal_level: int):
        """
        Применяет политику управления качеством на основе уровня сигнала.

        Args:
            signal_level: Уровень сигнала (0 - высокий, > 0 - деградация)
        """
        logger.info(f"[RESTREAMER] Обновление политики качества, уровень сигнала: {signal_level}")

        if not self.policy_engines:
            logger.error("[RESTREAMER] Нет доступных policy engines для применения!")
            return

        policy_engine_keys = list(self.policy_engines.keys())
        first_engine = self.policy_engines[policy_engine_keys[0]]

        # Проверяем, что уровень сигнала не выходит за пределы доступных профилей
        if signal_level >= len(first_engine.profiles):
            signal_level = len(first_engine.profiles) - 1
            logger.warning(f"[RESTREAMER] Уровень сигнала превышает количество профилей. Установлен на {signal_level}")

        # При очень низком качестве оставляем только DAI камеру ("oakd")
        if signal_level >= len(first_engine.profiles) - 1:
            # Отключаем все RTSP-камеры
            for source_id, source in self.input_sources.items():
                if source_id != "oakd":
                    source.stop()
                    logger.info(f"[RESTREAMER] Отключен источник {source_id} из-за низкого качества сигнала")

            # Применяем низкокачественный профиль для DAI
            dai_profile = first_engine.profiles[signal_level]
            if "oakd" in self.input_sources and "oakd" in self.output_streamers:
                # Проверяем, запущен ли источник
                if hasattr(self.input_sources["oakd"], "is_active") and not self.input_sources["oakd"].is_active():
                    self.input_sources["oakd"].start(dai_profile)

                # Если у источника есть метод restart_if_needed, используем его
                if hasattr(self.input_sources["oakd"], "restart_if_needed"):
                    self.input_sources["oakd"].restart_if_needed(dai_profile)

                # Обновляем профиль для выходного стримера
                self.output_streamers["oakd"].update_profile(dai_profile)
                logger.info(f"[RESTREAMER] DAI камера настроена на низкое качество: {dai_profile}")
            else:
                logger.error("[RESTREAMER] Источник или стример для DAI камеры не найден!")

        else:
            # Приоритизируем включение всех источников и настраиваем их согласно политикам
            for source_id, policy_engine in self.policy_engines.items():
                # Получаем соответствующий профиль для текущего уровня сигнала
                if signal_level in policy_engine.profiles:
                    profile = policy_engine.profiles[signal_level]
                else:
                    logger.error(f"[RESTREAMER] Недопустимый уровень сигнала {signal_level} для {source_id}")
                    continue

                # Применяем профиль к источнику
                if source_id in self.input_sources:
                    # Проверяем, есть ли метод is_active у источника
                    source_active = True
                    if hasattr(self.input_sources[source_id], "is_active"):
                        source_active = self.input_sources[source_id].is_active()

                    # Запускаем источник, если он был остановлен
                    if not source_active:
                        self.input_sources[source_id].start(profile)
                        logger.info(f"[RESTREAMER] Перезапущен источник {source_id} с профилем: {profile}")
                    else:
                        # Иначе обновляем профиль через policy engine
                        policy_engine.evaluate_and_apply({"level": signal_level})
                        logger.info(f"[RESTREAMER] Обновлен профиль для источника {source_id}: {profile}")

                # Обновляем настройки выходного стримера
                if source_id in self.output_streamers:
                    self.output_streamers[source_id].update_profile(profile)
                    logger.info(f"[RESTREAMER] Обновлен профиль для стримера {source_id}: {profile}")

    def stop(self):
        """Останавливает все источники, стримеры и мониторинг."""
        self.running = False

        # Ожидаем завершения потока мониторинга
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)

        # Останавливаем источники
        for source_id, source in self.input_sources.items():
            try:
                source.stop()
                logger.info(f"[RESTREAMER] Остановлен источник {source_id}")
            except Exception as e:
                logger.error(f"[RESTREAMER] Ошибка при остановке источника {source_id}: {e}")

        # Останавливаем стримеры
        for streamer_id, streamer in self.output_streamers.items():
            try:
                streamer.stop_streaming()
                streamer.close()
                logger.info(f"[RESTREAMER] Остановлен стример {streamer_id}")
            except Exception as e:
                logger.error(f"[RESTREAMER] Ошибка при остановке стримера {streamer_id}: {e}")

        logger.info("[RESTREAMER] Все источники и стримеры остановлены")

    def get_status(self) -> Dict[str, Any]:
        """
        Возвращает текущий статус всех источников и стримеров.

        Returns:
            Словарь с информацией о статусе всех компонентов
        """
        status = {"signal_level": self.current_signal_level, "running": self.running, "sources": {}, "streamers": {}}

        # Собираем информацию об источниках
        for source_id, source in self.input_sources.items():
            if hasattr(source, "get_current_settings"):
                status["sources"][source_id] = source.get_current_settings()
            elif hasattr(source, "is_active"):
                status["sources"][source_id] = {"active": source.is_active()}
            else:
                status["sources"][source_id] = {"active": "unknown"}

        # Собираем информацию о стримерах
        for streamer_id, streamer in self.output_streamers.items():
            if hasattr(streamer, "get_status"):
                status["streamers"][streamer_id] = streamer.get_status()
            else:
                status["streamers"][streamer_id] = {"active": "unknown"}

        return status
