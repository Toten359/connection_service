from src.restreamer import Restreamer
from src.config import Config
from src.pkg.logger import get_logger, LogType
import time
import signal
import sys

logger = get_logger(__name__, logType=LogType.SYSLOG)

config = Config('main.conf')
restreamer = None

def signal_handler(sig, frame):
    logger.info("Завершение работы...")
    if restreamer:
        restreamer.stop()
    sys.exit(0)

def main():
    global restreamer
    
    restreamer = Restreamer(config)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Проверка подключения к роутеру
    if restreamer.signal_checker.authenticate():
        logger.info("[CONNECTION CHECKER] Подключение к роутеру успешно")
        restreamer.signal_checker.get_connection_info()
        if restreamer.connection_validator.check_connection():
            logger.info("[CONNECTION CHECKER] Проверка подключения к роутеру прошла успешно")
        else:
            logger.error("[CONNECTION CHECKER] Ошибка проверки подключения к роутеру")
            sys.exit(1)
    else:
        logger.error("[CONNECTION CHECKER] Ошибка подключения к роутеру")
        sys.exit(1)
    

    
    if config.adaptive_mode:
        logger.info("Запуск в адаптивном режиме")
        restreamer.start_adaptive_mode()
    else:
        logger.info("Запуск в режиме стандартного качества")
        restreamer.start_all_quality_mode()
    
    # Основной цикл с выводом статуса
    try:
        while True:
            status = restreamer.get_status()
            logger.info(f"Текущий уровень сигнала: {status['signal_level']}")
            logger.info(f"Активные источники: {[k for k, v in status['sources'].items() if v.get('active', False)]}")
            time.sleep(60)
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        logger.error(f"Ошибка в основном цикле: {e}")
        restreamer.stop()

if __name__ == "__main__":
    main()