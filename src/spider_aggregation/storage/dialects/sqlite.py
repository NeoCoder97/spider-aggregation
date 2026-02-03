"""SQLite dialect implementation."""

from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Engine, event
from sqlalchemy.pool import QueuePool, StaticPool

from spider_aggregation.storage.dialects.base import BaseDialect

if TYPE_CHECKING:
    from spider_aggregation.config import DatabaseConfig


class SQLiteDialect(BaseDialect):
    """SQLite database dialect.

    SQLite is the default database for MindWeaver. It requires no external
    database server and is suitable for single-user deployments and development.

    Features:
    - Embedded database (no server required)
    - WAL mode for better concurrent read access
    - Foreign key constraints enabled
    - StaticPool for single-threaded, QueuePool for multi-threaded
    """

    @property
    def name(self) -> str:
        """Get dialect name."""
        return "sqlite"

    def build_url(self, config: "DatabaseConfig") -> str:
        """Build SQLite database URL.

        Args:
            config: Database configuration

        Returns:
            SQLAlchemy URL string

        Note:
            Supports both path-based and URL-based configuration.
            - path: "data/spider_aggregation.db" -> "sqlite:///data/spider_aggregation.db"
            - path: "sqlite:///data/spider_aggregation.db" -> unchanged
        """
        db_path = config.path

        # Already a URL, return as-is
        if db_path.startswith("sqlite://"):
            return db_path

        # Ensure directory exists
        path_obj = Path(db_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        return f"sqlite:///{db_path}"

    def get_engine_kwargs(self, config: "DatabaseConfig") -> dict:
        """Get SQLite-specific engine kwargs.

        Args:
            config: Database configuration

        Returns:
            Dictionary of engine kwargs

        Note:
            Uses QueuePool for better concurrency with ThreadPoolExecutor.
            StaticPool causes issues with multiple threads.
        """
        return {
            "echo": config.echo,
            "connect_args": {
                "check_same_thread": False,  # Needed for SQLite
                "timeout": 30,  # 30 second timeout for locks
            },
            "poolclass": QueuePool,
            "pool_size": config.pool_size,
            "max_overflow": config.max_overflow,
        }

    def get_pool_class(self) -> type[QueuePool]:
        """Get connection pool class.

        Returns:
            QueuePool for concurrent access
        """
        return QueuePool

    def setup_engine_events(self, engine: Engine) -> None:
        """Set up SQLite PRAGMA statements.

        Args:
            engine: SQLAlchemy engine

        Note:
            Enables foreign keys and WAL mode for better concurrency.
        """
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            # Set WAL mode for better concurrent read access
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    def get_migration_kwargs(self) -> dict:
        """Get Alembic migration kwargs.

        Returns:
            Dictionary with render_as_batch=True for SQLite
        """
        return {
            "render_as_batch": True,  # Required for SQLite ALTER TABLE
        }

    def validate_config(self, config: "DatabaseConfig") -> list[str]:
        """Validate SQLite configuration.

        Args:
            config: Database configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check if path is accessible
        try:
            db_path = Path(config.path)
            if db_path.exists() and not db_path.is_file():
                errors.append(f"Database path exists but is not a file: {config.path}")
        except Exception as e:
            errors.append(f"Invalid database path: {e}")

        return errors

    @property
    def supports_json(self) -> bool:
        """SQLite has limited JSON support (via JSON1 extension)."""
        return True  # JSON1 extension is commonly available

    @property
    def supports_array(self) -> bool:
        """SQLite does not support ARRAY types."""
        return False
