"""
Database connection and session management.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from spider_aggregation.config import get_config
from spider_aggregation.models import Base

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
        db_path = Path(config.database.path)

        # Ensure database directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        if config.database.path.startswith("sqlite://"):
            url = config.database.path
        else:
            url = f"sqlite:///{db_path}"

        # Use QueuePool for better concurrency with ThreadPoolExecutor
        # StaticPool causes issues with multiple threads
        _engine = create_engine(
            url,
            echo=config.database.echo,
            connect_args={
                "check_same_thread": False,  # Needed for SQLite
                "timeout": 30,  # 30 second timeout for locks
            },
            poolclass=QueuePool,
            pool_size=5,  # Allow up to 5 connections in the pool
            max_overflow=10,  # Allow up to 10 additional connections
        )

        # Enable foreign key constraints for SQLite
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            # Set WAL mode for better concurrent read access
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

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


def init_db(drop_all: bool = False) -> None:
    """Initialize the database.

    Creates all tables if they don't exist.

    Args:
        drop_all: If True, drop all tables before creating them
    """
    engine = get_engine()

    if drop_all:
        Base.metadata.drop_all(bind=engine)

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

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager.

        Args:
            db_path: Optional custom database path. If not provided, uses config.
        """
        self._custom_db_path = db_path
        self._engine: Optional[Engine] = None

    @property
    def engine(self) -> Engine:
        """Get the database engine."""
        if self._engine is None:
            if self._custom_db_path:
                db_path = Path(self._custom_db_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)
                url = f"sqlite:///{db_path}"
                self._engine = create_engine(
                    url,
                    echo=False,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 30,
                    },
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                )

                @event.listens_for(self._engine, "connect")
                def set_sqlite_pragma(dbapi_conn, connection_record):
                    cursor = dbapi_conn.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.close()
            else:
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
