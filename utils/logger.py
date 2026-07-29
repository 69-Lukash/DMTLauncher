import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger() -> logging.Logger:
    if sys.platform == "win32":
        app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
        log_dir = os.path.join(app_data, "DMTL", "logs")
    else:
        log_dir = os.path.join(str(Path.home()), ".config", "DMTL", "logs")
    
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("DMTLauncher")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    info_file = os.path.join(log_dir, "dmtl_info.log")
    info_handler = RotatingFileHandler(info_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    error_file = os.path.join(log_dir, "dmtl_error.log")
    error_handler = RotatingFileHandler(error_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(info_handler)
        logger.addHandler(error_handler)
        logger.addHandler(console_handler)

    return logger

logger = setup_logger()