import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import settings
from logfire import LogfireLoggingHandler

LOG_PATH = Path("logs")
LOG_PATH.mkdir(parents=True, exist_ok=True)


def init_logger(
    logger_name: str,
    log_path: Path = LOG_PATH,
    filename: str | None = None,
    log_level: int = logging.INFO,
    add_logfire_handler: bool = True,
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    formatter = logging.Formatter(
        "%(levelname)s: %(asctime)s: %(pathname)s: %(lineno)s: %(name)s | %(message)s"
    )
    streamhandler = logging.StreamHandler(sys.stdout)
    streamhandler.setFormatter(formatter)
    logger.addHandler(streamhandler)
    if filename is not None:
        filehandler = RotatingFileHandler(
            filename=log_path / filename, maxBytes=10 * 1024 * 1024, backupCount=10
        )
        filehandler.setFormatter(formatter)
        logger.addHandler(filehandler)

    if settings.logfire_token and add_logfire_handler:
        logger.addHandler(LogfireLoggingHandler())

    return logger


app_logger = init_logger(logger_name="APP-LOGS", filename="app.log")
app_logger.info("Logger initialized for %s", "APP-LOGS")
