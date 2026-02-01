#!/usr/bin/env python3
"""
Initialize the spider-aggregation database.

This script creates all necessary database tables.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spider_aggregation.storage.database import init_db


def main() -> None:
    """Initialize the database."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize spider-aggregation database")
    parser.add_argument(
        "--drop", action="store_true", help="Drop existing tables before creating new ones"
    )
    args = parser.parse_args()

    print("Initializing database...")
    init_db(drop_all=args.drop)
    print("Database initialized successfully!")


if __name__ == "__main__":
    main()
