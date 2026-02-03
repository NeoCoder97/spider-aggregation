"""Database dialect system for MindWeaver.

This module provides a dialect abstraction layer that allows MindWeaver
to work with different database backends (SQLite, PostgreSQL, MySQL).
"""

from spider_aggregation.storage.dialects.base import BaseDialect
from spider_aggregation.storage.dialects.mysql import MySQLDialect
from spider_aggregation.storage.dialects.postgresql import PostgreSQLDialect
from spider_aggregation.storage.dialects.sqlite import SQLiteDialect

# Dialect registry
_DIALECT_REGISTRY: dict[str, type[BaseDialect]] = {
    "sqlite": SQLiteDialect,
    "postgresql": PostgreSQLDialect,
    "postgres": PostgreSQLDialect,  # Alias
    "mysql": MySQLDialect,
}


def get_dialect(name: str) -> BaseDialect:
    """Get a dialect instance by name.

    Args:
        name: Dialect name (sqlite, postgresql, mysql).
               "postgres" is accepted as an alias for "postgresql".

    Returns:
        Dialect instance

    Raises:
        ValueError: If dialect name is not supported

    Examples:
        >>> dialect = get_dialect("sqlite")
        >>> url = dialect.build_url(config)
    """
    name_lower = name.lower()
    if name_lower not in _DIALECT_REGISTRY:
        supported = ", ".join(sorted(set(_DIALECT_REGISTRY.keys())))
        raise ValueError(
            f"Unsupported database dialect: {name!r}. "
            f"Supported dialects: {supported}"
        )

    dialect_class = _DIALECT_REGISTRY[name_lower]
    return dialect_class()


def register_dialect(name: str, dialect_class: type[BaseDialect]) -> None:
    """Register a custom dialect.

    Args:
        name: Dialect name
        dialect_class: Dialect class to register

    Note:
        This allows extending MindWeaver with custom database backends.
    """
    _DIALECT_REGISTRY[name.lower()] = dialect_class


def get_supported_dialects() -> list[str]:
    """Get list of supported dialect names.

    Returns:
        List of dialect names
    """
    return sorted(set(_DIALECT_REGISTRY.keys()))


__all__ = [
    "BaseDialect",
    "SQLiteDialect",
    "PostgreSQLDialect",
    "MySQLDialect",
    "get_dialect",
    "register_dialect",
    "get_supported_dialects",
]
