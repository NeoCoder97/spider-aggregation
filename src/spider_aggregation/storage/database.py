"""
Database connection and session management.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from spider_aggregation.config import get_config
from spider_aggregation.models import Base

if TYPE_CHECKING:
    from spider_aggregation.config import DatabaseConfig

# Global engine and session factory
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """Get or create the database engine.

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine

    if _engine is None:
        config = get_config()
        db_config: DatabaseConfig = config.database

        # Import dialect system
        from spider_aggregation.storage.dialects import get_dialect

        # Get appropriate dialect
        dialect = get_dialect(db_config.type)

        # Build database URL using dialect
        url = dialect.build_url(db_config)

        # Get engine kwargs from dialect
        engine_kwargs = dialect.get_engine_kwargs(db_config)

        # Create engine
        _engine = create_engine(url, **engine_kwargs)

        # Set up dialect-specific events (e.g., SQLite PRAGMA)
        dialect.setup_engine_events(_engine)

    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory.

    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )

    return _session_factory


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get a database session.

    Yields:
        SQLAlchemy Session instance

    Example:
        >>> with get_db() as session:
        ...     feeds = session.query(FeedModel).all()
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Session:
    """Get a database session without context manager.

    The caller is responsible for closing the session.

    Returns:
        SQLAlchemy Session instance

    Example:
        >>> session = get_session()
        >>> try:
        ...     feeds = session.query(FeedModel).all()
        ... finally:
        ...     session.close()
    """
    session_factory = get_session_factory()
    return session_factory()


def init_db(drop_all: bool = False, use_migrations: bool = True) -> None:
    """Initialize the database.

    Args:
        drop_all: If True, drop all tables before creating them (DANGEROUS!)
        use_migrations: If True, use Alembic migrations instead of create_all()
                       Recommended for production. Set to False for testing only.

    Note:
        For production use, always use Alembic migrations:
        - Fresh install: alembic upgrade head
        - Existing DB: alembic stamp head
    """
    from spider_aggregation.logger import get_logger
    logger = get_logger(__name__)

    engine = get_engine()

    # For testing or development, allow drop_all + create_all
    if drop_all:
        logger.warning("Dropping all tables - data will be lost!")
        Base.metadata.drop_all(bind=engine)
        # After dropping, we need to run migrations to recreate
        use_migrations = True

    if use_migrations:
        # Check if alembic_version table exists
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        has_alembic = 'alembic_version' in inspector.get_table_names()

        if not has_alembic and not drop_all:
            # Fresh database with existing tables (created by old init_db)
            # Stamp it as current migration
            logger.info("Stamping database with current migration version")
            from alembic.config import Config
            from alembic import command

            alembic_cfg = Config("alembic.ini")
            try:
                command.stamp(alembic_cfg, "head")
                logger.info("Database stamped successfully")
            except Exception as e:
                logger.warning(f"Could not stamp database: {e}")
        elif not has_alembic:
            # Completely fresh database (no tables at all)
            logger.info("Running database migrations")
            from alembic.config import Config
            from alembic import command

            alembic_cfg = Config("alembic.ini")
            try:
                command.upgrade(alembic_cfg, "head")
                logger.info("Database migrations completed")
            except Exception as e:
                logger.warning(f"Could not run migrations: {e}, falling back to create_all")
                Base.metadata.create_all(bind=engine)
        # else: alembic_version table exists, migrations are being managed by alembic CLI
    else:
        # Legacy behavior - directly create tables (not recommended for production)
        logger.warning("Using direct table creation (not recommended for production)")
        Base.metadata.create_all(bind=engine)


def close_db() -> None:
    """Close the database connection and dispose of the engine."""
    global _engine, _session_factory

    if _engine is not None:
        _engine.dispose()
        _engine = None

    _session_factory = None


class DatabaseManager:
    """Database manager for context-managed database operations."""

    def __init__(self, db_path: Optional[str] = None, db_config: Optional["DatabaseConfig"] = None):
        """Initialize database manager.

        Args:
            db_path: Optional custom database path for SQLite (deprecated, use db_config).
            db_config: Optional custom database configuration.

        Note:
            If neither db_path nor db_config is provided, uses the global config.
            For custom database backends, provide db_config.
        """
        self._custom_db_path = db_path
        self._custom_db_config = db_config
        self._engine: Optional[Engine] = None

    @property
    def engine(self) -> Engine:
        """Get the database engine."""
        if self._engine is None:
            if self._custom_db_path:
                # Legacy support: create SQLite engine from path
                from spider_aggregation.storage.dialects import get_dialect

                db_path = Path(self._custom_db_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)

                # Create a minimal config for SQLite
                from spider_aggregation.config import DatabaseConfig

                db_config = DatabaseConfig(path=str(db_path), echo=False)
                dialect = get_dialect("sqlite")

                url = dialect.build_url(db_config)
                engine_kwargs = dialect.get_engine_kwargs(db_config)
                self._engine = create_engine(url, **engine_kwargs)
                dialect.setup_engine_events(self._engine)
            elif self._custom_db_config:
                # Use custom config
                from spider_aggregation.storage.dialects import get_dialect

                dialect = get_dialect(self._custom_db_config.type)
                url = dialect.build_url(self._custom_db_config)
                engine_kwargs = dialect.get_engine_kwargs(self._custom_db_config)
                self._engine = create_engine(url, **engine_kwargs)
                dialect.setup_engine_events(self._engine)
            else:
                # Use global config
                self._engine = get_engine()

        return self._engine

    def init_db(self, drop_all: bool = False) -> None:
        """Initialize database tables.

        Args:
            drop_all: If True, drop existing tables first
        """
        if drop_all:
            Base.metadata.drop_all(bind=self.engine)

        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session.

        Yields:
            SQLAlchemy Session instance
        """
        session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        session = session_factory()

        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close database connections."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
