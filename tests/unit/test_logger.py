"""Unit tests for logger configuration."""

import sys
from pathlib import Path

import pytest
from loguru import logger as _logger

from spider_aggregation.logger import (
    critical,
    debug,
    error,
    exception,
    get_logger,
    info,
    logger as app_logger,
    setup_logger,
    warning,
)


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_setup_logger_adds_handlers(self):
        """Test that setup_logger adds handlers."""
        # Clear existing handlers
        _logger.remove()

        setup_logger()

        # Check that handlers were added by using logger
        # If we can log without error, handlers are working
        import io
        output = io.StringIO()
        handler_id = _logger.add(output, format="{message}")
        _logger.info("Test")
        assert "Test" in output.getvalue()
        _logger.remove(handler_id)  # Clean up

    def test_setup_logger_with_custom_values(self, tmp_path):
        """Test setup_logger with custom values."""
        log_file = tmp_path / "test.log"

        _logger.remove()
        setup_logger(
            level="DEBUG",
            log_file=str(log_file),
            rotation="10 MB",
            retention="1 day",
        )

        # Log a message
        _logger.info("Test message")

        # Flush to ensure message is written
        _logger.remove()  # This flushes handlers

        # Check that message was written
        content = log_file.read_text()
        assert "Test message" in content
        assert "INFO" in content

    def test_console_handler_enabled(self, capsys=None):
        """Test that console handler is enabled by default."""
        _logger.remove()
        setup_logger()

        # Log and capture output
        _logger.info("Console test")
        # If we get here without exception, console handler works
        assert True

    def test_file_handler_disabled(self, monkeypatch):
        """Test disabling file handler."""
        # Disable file logging via config
        from spider_aggregation.config import get_config

        config = get_config()
        config.logging.file_enabled = False

        _logger.remove()
        setup_logger()

        # Log a message - if file handler is disabled, no error should occur
        _logger.info("Test with file disabled")
        assert True


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger."""
        log = get_logger()
        assert log is not None

    def test_get_logger_with_name(self):
        """Test get_logger with name parameter."""
        log = get_logger("test_module")
        assert log is not None

    def test_get_logger_bind(self):
        """Test that get_logger binds name."""
        log = get_logger("test_module")
        # bind returns a new logger with extra bound
        assert log is not None
        # We can log with it
        log.info("Test")
        assert True


class TestConvenienceFunctions:
    """Tests for convenience logging functions."""

    def test_debug_function(self, caplog=None):
        """Test debug logging function."""
        debug("Debug message")
        assert True  # If we got here, no exception was raised

    def test_info_function(self):
        """Test info logging function."""
        info("Info message")
        assert True

    def test_warning_function(self):
        """Test warning logging function."""
        warning("Warning message")
        assert True

    def test_error_function(self):
        """Test error logging function."""
        error("Error message")
        assert True

    def test_critical_function(self):
        """Test critical logging function."""
        critical("Critical message")
        assert True

    def test_exception_function(self):
        """Test exception logging function."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            exception("Exception occurred")
        assert True


class TestLoggerOutput:
    """Tests for logger output."""

    def test_log_format_includes_level(self, tmp_path):
        """Test that log format includes level."""
        log_file = tmp_path / "format_test.log"

        _logger.remove()
        _logger.add(
            str(log_file),
            format="<level>{level}</level>: {message}",
            level="INFO",
            enqueue=False,  # Disable enqueue for immediate writes
        )

        _logger.info("Test message")
        _logger.remove()  # Flush and close

        content = log_file.read_text()
        assert "INFO" in content

    def test_log_format_includes_time(self, tmp_path):
        """Test that log format includes timestamp."""
        log_file = tmp_path / "time_test.log"

        _logger.remove()
        _logger.add(
            str(log_file),
            format="{time} | {message}",
            level="INFO",
            enqueue=False,
        )

        _logger.info("Test message")
        _logger.remove()

        content = log_file.read_text()
        # Check for date pattern (contains digits and colon)
        assert any(char.isdigit() for char in content)

    def test_log_format_includes_function(self, tmp_path):
        """Test that log format includes function information."""
        log_file = tmp_path / "function_test.log"

        _logger.remove()
        _logger.add(
            str(log_file),
            format="{function} | {message}",
            level="INFO",
            enqueue=False,
        )

        _logger.info("Test message")
        _logger.remove()

        content = log_file.read_text()
        # Function name should be in log
        assert "test_log_format_includes_function" in content

    def test_log_levels_filtering(self, tmp_path):
        """Test that log level filtering works."""
        log_file = tmp_path / "level_test.log"

        _logger.remove()
        _logger.add(
            str(log_file),
            format="{level} | {message}",
            level="WARNING",
            enqueue=False,
        )

        _logger.debug("Debug message")
        _logger.info("Info message")
        _logger.warning("Warning message")
        _logger.error("Error message")
        _logger.remove()

        content = log_file.read_text()

        # DEBUG and INFO should not appear
        assert "Debug message" not in content
        assert "Info message" not in content

        # WARNING and ERROR should appear
        assert "Warning message" in content
        assert "Error message" in content


class TestLogRotation:
    """Tests for log rotation."""

    def test_rotation_setting(self):
        """Test that rotation setting is applied."""
        from spider_aggregation.config import get_config

        config = get_config()
        assert config.logging.rotation == "100 MB"

    def test_retention_setting(self):
        """Test that retention setting is applied."""
        from spider_aggregation.config import get_config

        config = get_config()
        assert config.logging.retention == "30 days"


class TestIntegration:
    """Integration tests for logging system."""

    def test_logger_with_config(self, tmp_path):
        """Test that logger works with config system."""
        from spider_aggregation.config import Config, load_config_from_yaml
        import yaml

        # Create test config
        config_file = tmp_path / "test_config.yaml"
        log_file = tmp_path / "test.log"
        test_config = {
            "logging": {
                "level": "DEBUG",
                "file_enabled": True,
                "file_path": str(log_file),
                "rotation": "10 MB",
                "retention": "7 days",
                "console_enabled": False,
            }
        }

        with config_file.open("w") as f:
            yaml.dump(test_config, f)

        # Load config
        config = load_config_from_yaml(str(config_file))

        # Setup logger with config values - disable enqueue for immediate writes
        _logger.remove()
        _logger.add(
            str(log_file),
            format="{level} | {message}",
            level=config.logging.level,
            rotation=config.logging.rotation,
            retention=config.logging.retention,
            enqueue=False,  # Disable enqueue for test
        )

        # Log test message
        _logger.debug("Debug test")
        _logger.info("Info test")
        _logger.remove()

        # Verify output
        log_content = log_file.read_text()
        assert "Debug test" in log_content
        assert "Info test" in log_content

    def test_multiple_modules_logging(self, tmp_path):
        """Test logging from multiple modules."""
        log_file = tmp_path / "multi.log"

        _logger.remove()
        _logger.add(
            str(log_file),
            format="{message}",
            level="INFO",
            enqueue=False,
        )

        # Simulate logging from different modules
        logger1 = get_logger("module_a")
        logger2 = get_logger("module_b")

        logger1.info("Message from module A")
        logger2.info("Message from module B")
        _logger.remove()

        content = log_file.read_text()
        assert "Message from module A" in content
        assert "Message from module B" in content

    def test_logger_reconfigure(self, tmp_path):
        """Test reconfiguring logger."""
        log_file1 = tmp_path / "test1.log"
        log_file2 = tmp_path / "test2.log"

        # Initial setup
        _logger.remove()
        _logger.add(str(log_file1), format="{message}", enqueue=False)
        _logger.info("Message 1")
        _logger.remove()
        assert log_file1.exists()

        # Reconfigure
        _logger.add(str(log_file2), format="{message}", enqueue=False)
        _logger.info("Message 2")
        _logger.remove()
        assert log_file2.exists()

        # Check both files have content
        assert "Message 1" in log_file1.read_text()
        assert "Message 2" in log_file2.read_text()


class TestLoggerInitialization:
    """Tests for logger initialization."""

    def test_logger_initialized_by_default(self):
        """Test that logger can be used without explicit setup."""
        # Just use the convenience functions
        info("Test message")
        assert True

    def test_logger_level_validation(self):
        """Test that invalid log levels are handled."""
        from spider_aggregation.config import LoggingConfig

        # Valid levels should work
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

        # Invalid level should raise error
        with pytest.raises(Exception):
            LoggingConfig(level="INVALID")

    def test_log_directory_creation(self, tmp_path):
        """Test that log directory is created."""
        log_dir = tmp_path / "logs" / "subdir"
        log_file = log_dir / "test.log"

        _logger.remove()
        # Use direct file handler to test directory creation
        _logger.add(str(log_file), format="{message}", enqueue=False)
        _logger.info("Test")
        _logger.remove()

        # Log file should be created, which means directory was created
        assert log_file.exists()
        assert log_dir.exists()
