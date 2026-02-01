"""
Logging configuration for spider aggregation.

Uses loguru for advanced logging capabilities with rotation and retention.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger as _logger

from spider_aggregation.config import get_config


def setup_logger(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    rotation: Optional[str] = None,
    retention: Optional[str] = None,
    format: Optional[str] = None,
) -> None:
    """Configure the logger with file and console handlers.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, etc.)
        log_file: Path to log file
        rotation: Log rotation setting (e.g., "100 MB", "1 day")
        retention: Log retention setting (e.g., "30 days", "1 week")
        format: Log format string
    """
    config = get_config()
    log_config = config.logging

    # Use provided values or fall back to config
    level = level or log_config.level
    log_file = log_file or log_config.file_path
    rotation = rotation or log_config.rotation
    retention = retention or log_config.retention
    format = format or log_config.format

    # Remove default handler
    _logger.remove()

    # Add console handler if enabled
    if log_config.console_enabled:
        _logger.add(
            sys.stderr,
            format=format,
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # Add file handler if enabled
    if log_config.file_enabled:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        _logger.add(
            log_file,
            format=format,
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8",
            enqueue=True,  # Thread-safe logging
            backtrace=True,
            diagnose=True,
        )


def get_logger(name: Optional[str] = None):
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Logger instance
    """
    if name:
        return _logger.bind(name=name)
    return _logger


# Convenience functions that match standard logging interface
def debug(msg: str, *args, **kwargs):
    """Log a debug message."""
    _logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log an info message."""
    _logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log a warning message."""
    _logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log an error message."""
    _logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Log a critical message."""
    _logger.critical(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs):
    """Log an exception with traceback."""
    _logger.exception(msg, *args, **kwargs)


# Re-export logger for direct use
logger = _logger

__all__ = [
    "setup_logger",
    "get_logger",
    "logger",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "exception",
]
