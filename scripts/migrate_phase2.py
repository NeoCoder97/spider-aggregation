#!/usr/bin/env python3
"""
Migration script for Phase 2 of spider-aggregation.

This script adds new fields to the entries table and creates the filter_rules table.
Supports rollback to Phase 1.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import inspect
from spider_aggregation.storage.database import DatabaseManager
from spider_aggregation.logger import get_logger

logger = get_logger(__name__)


def get_phase1_columns() -> set:
    """Return the expected columns for Phase 1 entries table."""
    return {
        "id", "feed_id", "title", "link", "author", "summary", "content",
        "published_at", "fetched_at", "title_hash", "link_hash", "content_hash",
        "tags", "language", "reading_time_seconds"
    }


def get_phase2_columns() -> set:
    """Return the expected columns for Phase 2 entries table."""
    phase1 = get_phase1_columns()
    # Note: full_content, keywords, generated_summary are not added as columns
    # They will be stored in existing 'content' and 'tags' fields
    return phase1


def check_current_phase(db_path: str) -> int:
    """Check the current phase of the database.

    Returns:
        1 if database is at Phase 1
        2 if database is at Phase 2
        0 if unknown
    """
    manager = DatabaseManager(db_path)

    with manager.session() as session:
        inspector = inspect(session.connection())

        # Check if filter_rules table exists
        if "filter_rules" in inspector.get_table_names():
            return 2

        # Check entries table columns
        columns = [c["name"] for c in inspector.get_columns("entries")]
        if set(columns) == get_phase1_columns():
            return 1

        return 0


def migrate_to_phase2(db_path: str) -> bool:
    """Migrate database from Phase 1 to Phase 2.

    Args:
        db_path: Path to the database file

    Returns:
        True if migration successful
    """
    logger.info(f"Migrating database at {db_path} to Phase 2...")

    current_phase = check_current_phase(db_path)

    if current_phase == 0:
        logger.error("Cannot determine current database phase")
        return False

    if current_phase == 2:
        logger.info("Database is already at Phase 2")
        return True

    if current_phase != 1:
        logger.error(f"Database is at unexpected phase: {current_phase}")
        return False

    manager = DatabaseManager(db_path)

    try:
        # Create filter_rules table
        from spider_aggregation.models.entry import FilterRuleModel

        logger.info("Creating filter_rules table...")
        FilterRuleModel.metadata.create_all(session.bind, tables=[FilterRuleModel.__table__])

        logger.info("Phase 2 migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def rollback_to_phase1(db_path: str) -> bool:
    """Rollback database from Phase 2 to Phase 1.

    Args:
        db_path: Path to the database file

    Returns:
        True if rollback successful
    """
    logger.info(f"Rolling back database at {db_path} to Phase 1...")

    current_phase = check_current_phase(db_path)

    if current_phase == 1:
        logger.info("Database is already at Phase 1")
        return True

    if current_phase != 2:
        logger.error(f"Database is at unexpected phase: {current_phase}")
        return False

    manager = DatabaseManager(db_path)

    try:
        with manager.session() as session:
            # Drop filter_rules table
            logger.info("Dropping filter_rules table...")
            session.execute("DROP TABLE IF EXISTS filter_rules")

            logger.info("Phase 2 rollback completed successfully")
            return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate spider-aggregation database to Phase 2"
    )
    parser.add_argument(
        "--db-path",
        default="data/spider_aggregation.db",
        help="Path to the database file"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback to Phase 1 instead of migrating to Phase 2"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check current database phase only"
    )

    args = parser.parse_args()

    # Ensure database file exists
    if not Path(args.db_path).exists():
        logger.error(f"Database not found at {args.db_path}")
        sys.exit(1)

    if args.check:
        phase = check_current_phase(args.db_path)
        if phase == 0:
            print("Unknown database phase")
        elif phase == 1:
            print("Phase 1")
        elif phase == 2:
            print("Phase 2")
        sys.exit(0)

    if args.rollback:
        success = rollback_to_phase1(args.db_path)
    else:
        success = migrate_to_phase2(args.db_path)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
