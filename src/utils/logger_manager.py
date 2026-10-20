import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Enable ANSI escape sequences on Windows console
if sys.platform == "win32":
    os.system("")


class MaxLevelFilter(logging.Filter):
    """
    Filter that only allows log records up to a specified maximum level.
    """

    def __init__(self, max_level):
        super().__init__()
        self.max_level = max_level

    def filter(self, record):
        return record.levelno <= self.max_level


class ColoredConsoleFormatter(logging.Formatter):
    """
    Console formatter with clean ANSI colors and level-specific prefixes.
    """

    RESET = "\033[0m"
    DIM = "\033[90m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    BOLD_RED = "\033[1;31m"

    LEVEL_CONFIG = {
        logging.DEBUG: (DIM, "[d]"),
        logging.INFO: (CYAN, "[*]"),
        logging.WARNING: (YELLOW, "[!]"),
        logging.ERROR: (RED, "[!]"),
        logging.CRITICAL: (BOLD_RED, "[!]"),
    }

    def __init__(self, datefmt: str, stream=None):
        super().__init__(datefmt=datefmt)
        is_tty = hasattr(stream, "isatty") and stream.isatty()
        self.use_color = is_tty and not os.getenv("NO_COLOR")

    def format(self, record):
        asctime = self.formatTime(record, self.datefmt)
        color, prefix = self.LEVEL_CONFIG.get(record.levelno, (self.CYAN, "[*]"))

        if self.use_color:
            if record.levelno >= logging.ERROR:
                msg = f"{color}{prefix}{self.RESET} {self.DIM}{asctime}{self.RESET} - {color}{record.getMessage()}{self.RESET}"
            elif record.levelno == logging.WARNING:
                msg = f"{color}{prefix}{self.RESET} {self.DIM}{asctime}{self.RESET} - {color}{record.getMessage()}{self.RESET}"
            else:
                msg = f"{color}{prefix}{self.RESET} {self.DIM}{asctime}{self.RESET} - {record.getMessage()}"
        else:
            msg = f"{prefix} {asctime} - {record.getMessage()}"

        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


class LoggerManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance.logger = None
            cls._instance.setup_logger()
        return cls._instance

    def setup_logger(self):
        if self.logger is None:
            self.logger = logging.getLogger("logger")
            self.logger.setLevel(logging.DEBUG)

            fmt_datefmt = "%Y-%m-%d %H:%M:%S"

            # 1) Console INFO & WARNING handler (stdout)
            info_handler = logging.StreamHandler(sys.stdout)
            info_handler.setLevel(logging.INFO)
            info_handler.setFormatter(
                ColoredConsoleFormatter(fmt_datefmt, stream=sys.stdout)
            )
            info_handler.addFilter(MaxLevelFilter(logging.WARNING))
            self.logger.addHandler(info_handler)

            # 2) Console ERROR handler (stderr)
            error_handler = logging.StreamHandler(sys.stderr)
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(
                ColoredConsoleFormatter(fmt_datefmt, stream=sys.stderr)
            )
            self.logger.addHandler(error_handler)

            # 3) File handler — DEBUG level, includes full stack traces
            #    Rotates at 5 MB, keeps 3 backups
            file_handler = RotatingFileHandler(
                "tiktok-recorder.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s", fmt_datefmt
                )
            )
            self.logger.addHandler(file_handler)


logger = LoggerManager().logger
