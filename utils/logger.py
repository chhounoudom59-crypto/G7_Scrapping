# =============================================================
# utils/logger.py — Coloured Console + Rotating File Logger
# =============================================================

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

try:
    import colorlog
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


def get_logger(name: str = "g7_scraper") -> logging.Logger:
    """Return a configured logger. Safe to call multiple times."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt      = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # Console handler (coloured if colorlog is available)
    if HAS_COLOR:
        console_fmt = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s%(reset)s | %(name)s | %(message)s",
            datefmt=date_fmt,
            log_colors={"DEBUG": "cyan", "INFO": "green",
                        "WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red"},
        )
    else:
        console_fmt = logging.Formatter(fmt, datefmt=date_fmt)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(console_fmt)
    logger.addHandler(ch)

    # Rotating file handler
    from config import LOG_DIR
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"g7_{datetime.now().strftime('%Y%m%d')}.log")
    fh = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt=date_fmt))
    logger.addHandler(fh)

    return logger
