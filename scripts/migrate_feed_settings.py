#!/usr/bin/env python
"""
Database migration script for feed personalization settings.

Adds the following columns to the feeds table:
- max_entries_per_fetch: Maximum number of entries to fetch per update (default: 100)
- fetch_only_recent: Only fetch entries from last 30 days (default: False)
"""

import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from spider_aggregation.config import get_config
from spider_aggregation.logger import get_logger
from spider_aggregation.storage.database import DatabaseManager

logger = get_logger(__name__)


def migrate():
    """Run the migration to add feed personalization settings columns."""
    config = get_config()
    db_manager = DatabaseManager(config.database.path)

    logger.info("Starting migration: Feed personalization settings")

    try:
        with db_manager.session() as session:
            # Check if columns already exist
            from sqlalchemy import inspect, text

            inspector = inspect(session.bind)
            columns = [col['name'] for col in inspector.get_columns('feeds')]

            # Add max_entries_per_fetch column if not exists
            if 'max_entries_per_fetch' not in columns:
                logger.info("Adding column: max_entries_per_fetch")
                session.execute(text(
                    "ALTER TABLE feeds ADD COLUMN max_entries_per_fetch INTEGER NOT NULL DEFAULT 100"
                ))
                session.commit()
                logger.info("Added column: max_entries_per_fetch (default: 100)")
            else:
                logger.info("Column 'max_entries_per_fetch' already exists, skipping")

            # Add fetch_only_recent column if not exists
            if 'fetch_only_recent' not in columns:
                logger.info("Adding column: fetch_only_recent")
                session.execute(text(
                    "ALTER TABLE feeds ADD COLUMN fetch_only_recent BOOLEAN NOT NULL DEFAULT 0"
                ))
                session.commit()
                logger.info("Added column: fetch_only_recent (default: False)")
            else:
                logger.info("Column 'fetch_only_recent' already exists, skipping")

        logger.info("Migration completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


def verify():
    """Verify the migration was successful."""
    config = get_config()
    db_manager = DatabaseManager(config.database.path)

    logger.info("Verifying migration...")

    try:
        with db_manager.session() as session:
            from sqlalchemy import inspect, text

            inspector = inspect(session.bind)
            columns = inspector.get_columns('feeds')
            column_names = [col['name'] for col in columns]

            # Check new columns exist
            if 'max_entries_per_fetch' in column_names:
                logger.info("Column 'max_entries_per_fetch' exists")
            else:
                logger.error("Column 'max_entries_per_fetch' NOT found")
                return False

            if 'fetch_only_recent' in column_names:
                logger.info("Column 'fetch_only_recent' exists")
            else:
                logger.error("Column 'fetch_only_recent' NOT found")
                return False

            # Check default values for existing feeds
            result = session.execute(text(
                "SELECT COUNT(*) FROM feeds WHERE max_entries_per_fetch = 100"
            )).scalar()
            logger.info(f"Feeds with default max_entries_per_fetch (100): {result}")

            result = session.execute(text(
                "SELECT COUNT(*) FROM feeds WHERE fetch_only_recent = 0"
            )).scalar()
            logger.info(f"Feeds with default fetch_only_recent (False): {result}")

        logger.info("Migration verification successful")
        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


def rollback():
    """Rollback the migration by removing the new columns."""
    config = get_config()
    db_manager = DatabaseManager(config.database.path)

    logger.warning("Starting rollback: Feed personalization settings")

    try:
        with db_manager.session() as session:
            from sqlalchemy import inspect, text

            inspector = inspect(session.bind)
            columns = [col['name'] for col in inspector.get_columns('feeds')]

            # SQLite doesn't support DROP COLUMN directly, need to recreate table
            if 'max_entries_per_fetch' in columns or 'fetch_only_recent' in columns:
                logger.warning("SQLite does not support DROP COLUMN directly")
                logger.warning("To rollback, you must manually recreate the feeds table")
                logger.warning("without the new columns and migrate existing data")
                return False

            logger.info("No columns to rollback")

        logger.warning("Rollback completed (manual intervention required for SQLite)")
        return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Feed personalization settings migration")
    parser.add_argument("--verify", action="store_true", help="Verify migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration")

    args = parser.parse_args()

    if args.rollback:
        success = rollback()
        sys.exit(0 if success else 1)
    elif args.verify:
        success = verify()
        sys.exit(0 if success else 1)
    else:
        migrate()
        verify()
