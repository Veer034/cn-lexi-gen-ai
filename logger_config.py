import logging
import sys
import threading
from pathlib import Path
from logging.handlers import RotatingFileHandler
import contextvars

# Context variable to hold tracking_id per request
tracking_id_var = contextvars.ContextVar("tracking_id", default="NA")

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.tracking_id = tracking_id_var.get()
        record.threadName = threading.current_thread().name
        return True

def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        log_dir / "service.log",
        maxBytes=50*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    console_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(threadName)s] [%(tracking_id)s] %(levelname)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        root_logger.addFilter(ContextFilter())

        logging.getLogger('elasticsearch').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('sentence_transformers').setLevel(logging.WARNING)

def get_logger(name):
    setup_logging()
    return logging.getLogger(name)
