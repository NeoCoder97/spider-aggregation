"""Abstract base dialect for database backends."""

from abc import ABC, abstractmethod

from sqlalchemy import Engine, event
from sqlalchemy.pool import Pool


class BaseDialect(ABC):
    """Abstract base class for database dialects.

    Each dialect implements database-specific configuration and behavior,
    allowing MindWeaver to work seamlessly with SQLite, PostgreSQL, MySQL,
    and other database backends.

    Subclasses must implement all abstract methods to provide dialect-specific
    behavior for URL construction, engine configuration, connection pooling,
    and event handling.
    """

    @abstractmethod
    def build_url(self, config: "DatabaseConfig") -> str:  # noqa: F821
        """Build database URL from configuration.

        Args:
            config: Database configuration object

        Returns:
            SQLAlchemy database URL string

        Examples:
            >>> # SQLite
            >>> "sqlite:///data/spider_aggregation.db"
            >>> # PostgreSQL
            >>> "postgresql://user:pass@localhost:5432/dbname"
            >>> # MySQL
            >>> "mysql+pymysql://user:pass@localhost:3306/dbname"
        """
        ...

    @abstractmethod
    def get_engine_kwargs(self, config: "DatabaseConfig") -> dict:  # noqa: F821
        """Get engine-specific keyword arguments.

        Args:
            config: Database configuration object

        Returns:
            Dictionary of keyword arguments for create_engine()

        Examples:
            >>> {
            ...     "echo": False,
            ...     "connect_args": {"check_same_thread": False},
            ...     "poolclass": QueuePool,
            ...     "pool_size": 5,
            ...     "max_overflow": 10,
            ... }
        """
        ...

    @abstractmethod
    def get_pool_class(self) -> type[Pool] | None:
        """Get the connection pool class for this dialect.

        Returns:
            Pool class or None for default pooling

        Note:
            SQLite typically uses StaticPool or QueuePool,
            PostgreSQL/MySQL use QueuePool.
        """
        ...

    def setup_engine_events(self, engine: Engine) -> None:
        """Set up dialect-specific engine event listeners.

        Args:
            engine: SQLAlchemy engine instance

        Note:
            Base implementation does nothing. Subclasses can override
            to set up PRAGMA statements (SQLite) or other event handlers.
        """
        pass

    def get_migration_kwargs(self) -> dict:
        """Get dialect-specific migration kwargs for Alembic.

        Returns:
            Dictionary of kwargs for context.configure()

        Examples:
            >>> {"render_as_batch": True}  # SQLite
            >>> {}  # PostgreSQL/MySQL
        """
        return {}

    def validate_config(self, config: "DatabaseConfig") -> list[str]:  # noqa: F821
        """Validate dialect-specific configuration.

        Args:
            config: Database configuration object

        Returns:
            List of validation error messages (empty if valid)

        Note:
            Base implementation performs no validation.
            Subclasses can override to check required fields.
        """
        return []

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the dialect name.

        Returns:
            Dialect name (e.g., "sqlite", "postgresql", "mysql")
        """
        ...

    @property
    def supports_json(self) -> bool:
        """Check if dialect supports JSON column types.

        Returns:
            True if JSON is natively supported
        """
        return False

    @property
    def supports_array(self) -> bool:
        """Check if dialect supports ARRAY column types.

        Returns:
            True if ARRAY is natively supported
        """
        return False

    @property
    def requires_cascade_type(self) -> bool:
        """Check if CASCADE requires type specification.

        Returns:
            True if CASCADE needs explicit type (e.g., PostgreSQL)
        """
        return False
