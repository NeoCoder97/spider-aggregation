"""PostgreSQL dialect implementation."""

from typing import TYPE_CHECKING

from sqlalchemy.pool import QueuePool

from spider_aggregation.storage.dialects.base import BaseDialect

if TYPE_CHECKING:
    from spider_aggregation.config import DatabaseConfig


class PostgreSQLDialect(BaseDialect):
    """PostgreSQL database dialect.

    PostgreSQL is recommended for production deployments with multiple users.
    It offers excellent concurrency, robust data integrity, and advanced features.

    Features:
    - Native JSON/JSONB support
    - ARRAY column types
    - Full-text search
    - Excellent concurrency with MVCC
    - ACID compliance
    """

    @property
    def name(self) -> str:
        """Get dialect name."""
        return "postgresql"

    def build_url(self, config: "DatabaseConfig") -> str:
        """Build PostgreSQL database URL.

        Args:
            config: Database configuration

        Returns:
            SQLAlchemy URL string

        Examples:
            >>> postgresql://user:pass@localhost:5432/dbname
            >>> postgresql://user:pass@localhost:5432/dbname?sslmode=require
        """
        # Build URL components
        user_part = f"{config.user}:{config.password}" if config.password else config.user
        host_part = config.host or "localhost"
        port_part = f":{config.port}" if config.port and config.port != 5432 else ""

        url = f"postgresql://{user_part}@{host_part}{port_part}/{config.database}"

        # Add SSL mode if specified
        if config.ssl_mode:
            url += f"?sslmode={config.ssl_mode}"

        return url

    def get_engine_kwargs(self, config: "DatabaseConfig") -> dict:
        """Get PostgreSQL-specific engine kwargs.

        Args:
            config: Database configuration

        Returns:
            Dictionary of engine kwargs
        """
        return {
            "echo": config.echo,
            "poolclass": QueuePool,
            "pool_size": config.pool_size,
            "max_overflow": config.max_overflow,
            "pool_pre_ping": True,  # Verify connections before use
        }

    def get_pool_class(self) -> type[QueuePool]:
        """Get connection pool class.

        Returns:
            QueuePool for connection pooling
        """
        return QueuePool

    def get_migration_kwargs(self) -> dict:
        """Get Alembic migration kwargs.

        Returns:
            Empty dict (PostgreSQL doesn't need batch mode)
        """
        return {}

    def validate_config(self, config: "DatabaseConfig") -> list[str]:
        """Validate PostgreSQL configuration.

        Args:
            config: Database configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not config.database:
            errors.append("PostgreSQL requires 'database' name")

        if not config.host and not config.user:
            errors.append("PostgreSQL requires either 'host' or 'user'")

        # Validate SSL mode
        if config.ssl_mode:
            valid_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
            if config.ssl_mode not in valid_modes:
                errors.append(f"Invalid ssl_mode: {config.ssl_mode}. Must be one of {valid_modes}")

        return errors

    @property
    def supports_json(self) -> bool:
        """PostgreSQL has native JSON/JSONB support."""
        return True

    @property
    def supports_array(self) -> bool:
        """PostgreSQL has native ARRAY support."""
        return True

    @property
    def requires_cascade_type(self) -> bool:
        """PostgreSQL CASCADE requires explicit type specification."""
        return True
