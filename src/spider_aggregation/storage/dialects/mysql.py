"""MySQL dialect implementation."""

from typing import TYPE_CHECKING

from sqlalchemy.pool import QueuePool

from spider_aggregation.storage.dialects.base import BaseDialect

if TYPE_CHECKING:
    from spider_aggregation.config import DatabaseConfig


class MySQLDialect(BaseDialect):
    """MySQL database dialect.

    MySQL is a popular choice for web applications and offers good performance
    for read-heavy workloads. Requires pymysql driver.

    Features:
    - JSON column type (MySQL 5.7.8+)
    - Good read performance
    - Wide deployment and tooling support
    """

    @property
    def name(self) -> str:
        """Get dialect name."""
        return "mysql"

    def build_url(self, config: "DatabaseConfig") -> str:
        """Build MySQL database URL.

        Args:
            config: Database configuration

        Returns:
            SQLAlchemy URL string

        Examples:
            >>> mysql+pymysql://user:pass@localhost:3306/dbname
            >>> mysql+pymysql://user:pass@localhost:3306/dbname?charset=utf8mb4
        """
        # Build URL components
        user_part = f"{config.user}:{config.password}" if config.password else config.user
        host_part = config.host or "localhost"
        port_part = f":{config.port}" if config.port and config.port != 3306 else ""

        url = f"mysql+pymysql://{user_part}@{host_part}{port_part}/{config.database}"

        # Always use utf8mb4 for proper Unicode support
        url += "?charset=utf8mb4"

        return url

    def get_engine_kwargs(self, config: "DatabaseConfig") -> dict:
        """Get MySQL-specific engine kwargs.

        Args:
            config: Database configuration

        Returns:
            Dictionary of engine kwargs

        Note:
            MySQL connections are recycled to avoid stale connections.
        """
        return {
            "echo": config.echo,
            "poolclass": QueuePool,
            "pool_size": config.pool_size,
            "max_overflow": config.max_overflow,
            "pool_pre_ping": True,  # Verify connections before use
            "pool_recycle": 3600,  # Recycle connections after 1 hour
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
            Empty dict (MySQL doesn't need batch mode)
        """
        return {}

    def validate_config(self, config: "DatabaseConfig") -> list[str]:
        """Validate MySQL configuration.

        Args:
            config: Database configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not config.database:
            errors.append("MySQL requires 'database' name")

        if not config.host and not config.user:
            errors.append("MySQL requires either 'host' or 'user'")

        # Validate SSL mode
        if config.ssl_mode:
            valid_modes = ["disabled", "preferred", "required", "verify_ca", "verify_identity"]
            if config.ssl_mode not in valid_modes:
                errors.append(
                    f"Invalid ssl_mode: {config.ssl_mode}. Must be one of {valid_modes}"
                )

        return errors

    @property
    def supports_json(self) -> bool:
        """MySQL 5.7.8+ supports JSON."""
        return True

    @property
    def supports_array(self) -> bool:
        """MySQL does not have native ARRAY support."""
        return False

    @property
    def requires_cascade_type(self) -> bool:
        """MySQL CASCADE does not require type specification."""
        return False
