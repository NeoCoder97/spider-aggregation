"""
Configuration management for MindWeaver.

Uses Pydantic for validation and pydantic-settings for environment variable support.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration.

    Supports SQLite, PostgreSQL, and MySQL backends.
    Configuration priority: type field > auto-detection > default (SQLite).

    For SQLite:
        - Only `path` is required
        - Environment variable: DB_PATH

    For PostgreSQL/MySQL:
        - Set `type` to "postgresql" or "mysql"
        - Set `host`, `database`, `user`, `password`
        - Optional: `port`, `ssl_mode`
        - Environment variables: DB_TYPE, DB_HOST, DB_DATABASE, DB_USER, DB_PASSWORD, etc.
    """

    model_config = SettingsConfigDict(env_prefix="DB_")

    # Database type selection
    type: str = Field(default="sqlite", description="Database type: sqlite, postgresql, mysql")

    # SQLite configuration
    path: str = Field(default="data/spider_aggregation.db", description="Database file path (SQLite)")

    # PostgreSQL/MySQL configuration
    host: str | None = Field(default=None, description="Database host (PostgreSQL/MySQL)")
    port: int | None = Field(default=None, description="Database port (default: 5432 for PostgreSQL, 3306 for MySQL)")
    database: str | None = Field(default=None, description="Database name (PostgreSQL/MySQL)")
    user: str | None = Field(default=None, description="Database user (PostgreSQL/MySQL)")
    password: str | None = Field(default=None, description="Database password (PostgreSQL/MySQL)")
    ssl_mode: str | None = Field(default=None, description="SSL mode: prefer/require (PostgreSQL), preferred/required (MySQL)")

    # Common settings
    echo: bool = Field(default=False, description="Echo SQL statements")
    pool_size: int = Field(default=5, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Max overflow connections")

    @field_validator("type")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Normalize database type name."""
        v = v.lower().strip()
        if v == "postgres":
            return "postgresql"
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate database type."""
        valid_types = ["sqlite", "postgresql", "mysql"]
        if v not in valid_types:
            raise ValueError(f"Invalid database type: {v!r}. Must be one of {valid_types}")
        return v

    @field_validator("path")
    @classmethod
    def ensure_directory_exists(cls, v: str) -> str:
        """Ensure the database directory exists."""
        Path(v).parent.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int | None) -> int | None:
        """Validate port number."""
        if v is not None and not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("ssl_mode")
    @classmethod
    def validate_ssl_mode(cls, v: str | None) -> str | None:
        """Validate SSL mode."""
        if v is None:
            return None

        v = v.lower()
        valid_pg_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        valid_mysql_modes = ["disabled", "preferred", "required", "verify_ca", "verify_identity"]

        if v not in valid_pg_modes and v not in valid_mysql_modes:
            raise ValueError(
                f"Invalid ssl_mode: {v!r}. "
                f"PostgreSQL: {valid_pg_modes}, MySQL: {valid_mysql_modes}"
            )
        return v


class SchedulerConfig(BaseSettings):
    """Task scheduler configuration."""

    model_config = SettingsConfigDict(env_prefix="SCHEDULER_")

    enabled: bool = Field(default=True, description="Enable scheduler")
    timezone: str = Field(default="Asia/Shanghai", description="Scheduler timezone")

    # Fetch intervals (in minutes)
    default_interval_minutes: int = Field(default=60, ge=1, description="Default fetch interval")
    min_interval_minutes: int = Field(default=10, ge=1, description="Minimum fetch interval")

    # Job execution settings
    max_workers: int = Field(default=3, ge=1, le=20, description="Maximum concurrent workers")
    misfire_grace_time: int = Field(default=300, ge=0, description="Misfire grace time in seconds")
    coalesce: bool = Field(default=True, description="Coalesce misfired jobs")

    # Retry settings
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_backoff_seconds: int = Field(default=60, ge=1, description="Retry backoff in seconds")


class FetcherConfig(BaseSettings):
    """RSS/Atom fetcher configuration."""

    model_config = SettingsConfigDict(env_prefix="FETCHER_")

    # HTTP settings
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")
    user_agent: str = Field(
        default="Mind-Aggregation/0.1.0 (+https://github.com/mind-weaver)",
        description="User-Agent header"
    )

    # Retry settings
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=5, ge=1)

    # Content settings
    max_content_length: int = Field(
        default=100_000,
        ge=1_000,
        le=1_000_000,
        description="Maximum content length in bytes"
    )

    # Follow redirects
    follow_redirects: bool = Field(default=True)
    max_redirects: int = Field(default=5, ge=0, le=20)

    # Feed entry limits
    max_entries_per_feed: int = Field(
        default=0, ge=0, le=1000,
        description="Max entries to fetch per feed (0=unlimited)"
    )
    fetch_recent_days: int = Field(
        default=30, ge=0, le=365,
        description="Only fetch entries from last N days (0=unlimited)"
    )


class DeduplicatorConfig(BaseSettings):
    """Deduplication configuration."""

    model_config = SettingsConfigDict(env_prefix="DEDUP_")

    enabled: bool = Field(default=True, description="Enable deduplication")

    # Hash methods: md5, sha256
    link_hash_method: str = Field(default="sha256", description="Hash method for links")
    title_hash_method: str = Field(default="md5", description="Hash method for titles")
    content_hash_method: str = Field(default="sha256", description="Hash method for content")

    # Similarity threshold (0.0 - 1.0)
    title_similarity_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Title similarity threshold"
    )

    # Check options
    check_by_link: bool = Field(default=True, description="Deduplicate by link")
    check_by_title: bool = Field(default=True, description="Deduplicate by title similarity")
    check_by_content: bool = Field(default=False, description="Deduplicate by content hash")


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Log format"
    )

    # File logging
    file_enabled: bool = Field(default=True, description="Enable file logging")
    file_path: str = Field(default="logs/spider_aggregation.log", description="Log file path")
    rotation: str = Field(default="100 MB", description="Log rotation size")
    retention: str = Field(default="30 days", description="Log retention period")

    # Console logging
    console_enabled: bool = Field(default=True, description="Enable console logging")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v

    @field_validator("file_path")
    @classmethod
    def ensure_directory_exists(cls, v: str) -> str:
        """Ensure the log directory exists."""
        Path(v).parent.mkdir(parents=True, exist_ok=True)
        return v


class FeedConfig(BaseSettings):
    """Feed-specific configuration."""

    model_config = SettingsConfigDict(env_prefix="FEED_")

    # Feed validation
    validate_url: bool = Field(default=True, description="Validate feed URLs")
    check_interval_hours: int = Field(default=24, ge=1, description="Interval to check feed health")

    # Error handling
    max_consecutive_errors: int = Field(
        default=10,
        ge=1,
        description="Max consecutive errors before disabling feed"
    )
    error_backoff_hours: int = Field(default=1, ge=0, description="Backoff hours after error")


class WebConfig(BaseSettings):
    """Web API configuration (for future use)."""

    model_config = SettingsConfigDict(env_prefix="WEB_")

    enabled: bool = Field(default=False, description="Enable web API")
    host: str = Field(default="127.0.0.1", description="Web server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Web server port")
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(default="dev-secret-key", description="Secret key for sessions")


class ContentFetcherConfig(BaseSettings):
    """Content fetcher configuration for Phase 2."""

    model_config = SettingsConfigDict(env_prefix="CONTENT_FETCHER_")

    enabled: bool = Field(default=True, description="Enable full content fetching")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Request timeout")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=5, ge=1, description="Retry delay")
    max_content_length: int = Field(
        default=500_000,
        ge=10_000,
        le=5_000_000,
        description="Maximum content length in bytes"
    )
    user_agent: str = Field(
        default="Mind-Aggregation/0.2.0 (+https://github.com/mind-weaver)",
        description="User-Agent header"
    )


class KeywordExtractorConfig(BaseSettings):
    """Keyword extractor configuration for Phase 2."""

    model_config = SettingsConfigDict(env_prefix="KEYWORD_EXTRACTOR_")

    enabled: bool = Field(default=True, description="Enable keyword extraction")
    max_keywords: int = Field(default=10, ge=1, le=50, description="Maximum keywords to extract")
    min_keyword_length: int = Field(default=2, ge=1, description="Minimum keyword length")
    language: str = Field(default="auto", description="Language: auto, en, zh")


class SummarizerConfig(BaseSettings):
    """Summarizer configuration for Phase 2."""

    model_config = SettingsConfigDict(env_prefix="SUMMARIZER_")

    enabled: bool = Field(default=True, description="Enable summarization")
    method: str = Field(default="extractive", description="Method: extractive or ai")
    max_sentences: int = Field(default=3, ge=1, le=10, description="Maximum sentences in summary")
    min_sentence_length: int = Field(default=10, ge=5, description="Minimum sentence length")

    # AI summarization (optional)
    ai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI model for summarization")
    ai_max_tokens: int = Field(default=150, ge=50, le=500, description="Max tokens for AI summary")


class FilterConfig(BaseSettings):
    """Filter engine configuration for Phase 2."""

    model_config = SettingsConfigDict(env_prefix="FILTER_")

    enabled: bool = Field(default=True, description="Enable filtering")
    auto_apply: bool = Field(default=False, description="Auto-apply filters on fetch")
    cache_size: int = Field(default=100, ge=0, description="Rule cache size")


class Config(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MIND_",
        case_sensitive=False,
    )

    # Application
    version: str = Field(default="0.3.0", description="Application version")
    app_name: str = Field(default="MindWeaver", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    verbose: bool = Field(default=False, description="Verbose output")

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    fetcher: FetcherConfig = Field(default_factory=FetcherConfig)
    deduplicator: DeduplicatorConfig = Field(default_factory=DeduplicatorConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    feed: FeedConfig = Field(default_factory=FeedConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    content_fetcher: ContentFetcherConfig = Field(default_factory=ContentFetcherConfig)
    keyword_extractor: KeywordExtractorConfig = Field(default_factory=KeywordExtractorConfig)
    summarizer: SummarizerConfig = Field(default_factory=SummarizerConfig)
    filter: FilterConfig = Field(default_factory=FilterConfig)

    # Paths
    config_dir: str = Field(default="config", description="Configuration directory")
    data_dir: str = Field(default="data", description="Data directory")

    def get_config_path(self, name: str) -> Path:
        """Get path to a configuration file."""
        return Path(self.config_dir) / name

    def get_data_path(self, name: str) -> Path:
        """Get path to a data file."""
        path = Path(self.data_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def load_config_from_yaml(yaml_path: str) -> Config:
    """Load configuration from a YAML file.

    Note: Values loaded from YAML take precedence over environment variables.
    For environment variable overrides, use .env file or set them directly.

    Args:
        yaml_path: Path to the YAML configuration file.

    Returns:
        Config instance loaded from the file.
    """
    import yaml

    yaml_file = Path(yaml_path)
    if not yaml_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

    with yaml_file.open("r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f) or {}

    # Build config from YAML, then allow env vars to override specific nested configs
    # We need to rebuild nested configs to allow env var override
    main_config = {}
    nested_configs = {}

    for key, value in config_dict.items():
        if key in ["database", "scheduler", "fetcher", "deduplicator", "logging", "feed", "web",
                   "content_fetcher", "keyword_extractor", "summarizer", "filter"]:
            nested_configs[key] = value
        else:
            main_config[key] = value

    # Create nested config instances (which will read from env vars)
    config_classes = {
        "database": DatabaseConfig,
        "scheduler": SchedulerConfig,
        "fetcher": FetcherConfig,
        "deduplicator": DeduplicatorConfig,
        "logging": LoggingConfig,
        "feed": FeedConfig,
        "web": WebConfig,
        "content_fetcher": ContentFetcherConfig,
        "keyword_extractor": KeywordExtractorConfig,
        "summarizer": SummarizerConfig,
        "filter": FilterConfig,
    }

    for key, config_class in config_classes.items():
        if key in nested_configs:
            # Create from dict, env vars can still override
            nested_configs[key] = config_class(**nested_configs[key])
        else:
            nested_configs[key] = config_class()

    # Merge and create main config
    main_config.update(nested_configs)
    return Config(**main_config)


def reload_config() -> Config:
    """Reload configuration from environment and YAML files."""
    global _config
    _config = None

    # Try to load from YAML if exists
    config_yaml = Path("config/config.yaml")
    if config_yaml.exists():
        _config = load_config_from_yaml(str(config_yaml))
    else:
        _config = Config()

    return _config
