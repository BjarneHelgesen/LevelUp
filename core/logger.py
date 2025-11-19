"""
LevelUp logging module - debug logging to disk for troubleshooting
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    RELEASE = "RELEASE"


# Hardcoded log level - change to RELEASE for production
CURRENT_LOG_LEVEL = LogLevel.DEBUG

# Log file configuration
LOG_FILENAME = "LevelUp.log"
_logger_initialized = False
_logger = None


def _get_log_path() -> Path:
    """Get the log file path in the project root"""
    # Find project root by looking for known markers
    current = Path(__file__).parent.parent  # core -> LevelUp
    return current / LOG_FILENAME


def _rotate_existing_log():
    """Rename existing log file with timestamp"""
    log_path = _get_log_path()
    if log_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = log_path.parent / f"LevelUp_{timestamp}.log"
        try:
            log_path.rename(new_name)
        except Exception:
            # If rename fails, just overwrite
            pass


def _initialize_logger():
    """Initialize the logger with file handler"""
    global _logger_initialized, _logger

    if _logger_initialized:
        return _logger

    # Rotate existing log
    _rotate_existing_log()

    # Create logger
    _logger = logging.getLogger("LevelUp")
    _logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    _logger.handlers.clear()

    # Create file handler
    log_path = _get_log_path()
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')

    # Set format for easy reading
    # Format: [TIMESTAMP] [LEVEL] [MODULE:FUNCTION:LINE] MESSAGE
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)-8s] [%(module)s:%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # Set handler level based on log level
    if CURRENT_LOG_LEVEL == LogLevel.DEBUG:
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.WARNING)

    _logger.addHandler(file_handler)
    _logger_initialized = True

    # Log startup
    _logger.info("=" * 60)
    _logger.info("LevelUp Logger Started")
    _logger.info(f"Log Level: {CURRENT_LOG_LEVEL.value}")
    _logger.info(f"Log File: {log_path}")
    _logger.info("=" * 60)

    return _logger


def get_logger():
    """Get the LevelUp logger instance"""
    global _logger
    if not _logger_initialized:
        _initialize_logger()
    return _logger


# Convenience functions for logging
def debug(msg: str, *args, **kwargs):
    """Log debug message"""
    get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log info message"""
    get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log warning message"""
    get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log error message"""
    get_logger().error(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs):
    """Log exception with traceback"""
    get_logger().exception(msg, *args, **kwargs)


def assert_true(condition, msg: str):
    """Log error and raise RuntimeError if condition is false"""
    if not condition:
        get_logger().error(msg)
        raise RuntimeError(msg)
