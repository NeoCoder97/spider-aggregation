"""Alembic migration environment configuration for MindWeaver.

This file is configured to work with MindWeaver's:
- Pydantic-based configuration system
- SQLAlchemy models in src/spider_aggregation/models/
- Multi-database dialect support (SQLite, PostgreSQL, MySQL)
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, event

from alembic import context

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import MindWeaver configuration and models
from spider_aggregation.config import get_config
from spider_aggregation.models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get MindWeaver configuration
mind_config = get_config()
db_config = mind_config.database

# Import dialect system for database URL construction
from spider_aggregation.storage.dialects import get_dialect

# Get appropriate dialect and build URL
dialect = get_dialect(db_config.type)
db_url = dialect.build_url(db_config)

# Set database URL from MindWeaver config
# This ensures migrations use the same database as the application
config.set_main_option("sqlalchemy.url", db_url)

# Target metadata for autogenerate support
# This includes all SQLAlchemy models: feeds, entries, categories, filter_rules
target_metadata = Base.metadata

# Get dialect-specific migration kwargs
migration_kwargs = dialect.get_migration_kwargs()

# Additional values from the config
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **migration_kwargs,  # Dialect-specific settings (e.g., render_as_batch for SQLite)
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create engine configuration
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = db_url

    # Get engine kwargs from dialect
    engine_kwargs = dialect.get_engine_kwargs(db_config)

    # Remove echo from engine kwargs (Alembic has its own logging)
    engine_kwargs.pop("echo", None)

    # Create engine
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", **engine_kwargs)

    # Set up dialect-specific events (e.g., SQLite PRAGMA)
    dialect.setup_engine_events(connectable)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            **migration_kwargs,  # Dialect-specific settings
            # Compare type defaults (e.g., server_default values)
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
