import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(service_name: str) -> logging.Logger:
    log_dir = os.getenv("LOG_DIR", "/logs")
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{service_name}.log")

    logger = logging.getLogger(service_name)
    logger.setLevel(level)

    # чтобы не плодить хендлеры при перезагрузке
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    # в файл (ротация)
    file_handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)

    # в консоль (docker logs)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
