from datetime import datetime
from enum import Enum
import logging
import json
import syslog


class LogType(Enum):
    CONSOLE = "console"
    BOTH = "both"
    SYSLOG = "syslog"


class JsonSyslogLogHandler(logging.Handler):
    def __init__(self, ident="connection_monitor") -> None:
        super().__init__()
        syslog.openlog(ident=ident, logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL0)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = record.getMessage()

            data = {
                "timestamp": ts,
                "message": message,
                "level": record.levelname,
                "module": record.module,
                "lineno": record.lineno,
                "name": record.name,
            }
            if isinstance(record.msg, dict):
                data.update(record.msg)
            elif not isinstance(message, str):
                data["extra_message"] = str(record.msg)

            json_str = json.dumps(data, ensure_ascii=False)
            syslog.syslog(syslog.LOG_INFO, json_str)
        except Exception:
            self.handleError(record)


def get_logger(name, level=logging.INFO, logType: LogType = None) -> logging.Logger:
    """
    Get a logger with the specified name and configuration.
    Args:
        name (str): Name of the logger.
        level (int): Logging level (default: logging.INFO).
        logType (LogType): Type of logging (CONSOLE, BOTH, SYSLOG).
    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(level)
        if logType == LogType.CONSOLE:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            logger.addHandler(console_handler)
        elif logType == LogType.SYSLOG:
            syslog_handler = JsonSyslogLogHandler()
            logger.addHandler(syslog_handler)
        elif logType == LogType.BOTH:
            console_handler = logging.StreamHandler()
            logger.addHandler(console_handler)
            console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            syslog_handler = JsonSyslogLogHandler()
            logger.addHandler(syslog_handler)
    return logger
