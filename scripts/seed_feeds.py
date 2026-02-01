#!/usr/bin/env python3
"""
Seed the database with sample feed data.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spider_aggregation.models import FeedModel
from spider_aggregation.storage.database import get_db


SAMPLE_FEEDS = [
    {
        "url": "https://news.ycombinator.com/rss",
        "name": "Hacker News",
        "description": "Hacker News RSS Feed",
        "enabled": True,
        "fetch_interval_minutes": 60,
    },
    {
        "url": "https://www.reddit.com/r/programming/.rss",
        "name": "Reddit Programming",
        "description": "Programming subreddit RSS feed",
        "enabled": True,
        "fetch_interval_minutes": 120,
    },
    {
        "url": "https://techcrunch.com/feed/",
        "name": "TechCrunch",
        "description": "TechCrunch RSS Feed",
        "enabled": True,
        "fetch_interval_minutes": 60,
    },
    {
        "url": "https://feeds.feedburner.com/oreilly/radar",
        "name": "O'Reilly Radar",
        "description": "O'Reilly Radar RSS Feed",
        "enabled": True,
        "fetch_interval_minutes": 180,
    },
]


def main() -> None:
    """Seed the database with sample feeds."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed database with sample feeds")
    parser.add_argument("--clear", action="store_true", help="Clear existing feeds before seeding")
    args = parser.parse_args()

    with get_db() as session:
        if args.clear:
            print("Clearing existing feeds...")
            session.query(FeedModel).delete()
            session.commit()

        # Check if feeds already exist
        existing_count = session.query(FeedModel).count()

        for feed_data in SAMPLE_FEEDS:
            # Check if feed already exists
            existing = session.query(FeedModel).filter_by(url=feed_data["url"]).first()

            if existing:
                print(f"Feed already exists: {feed_data['name']}")
                continue

            feed = FeedModel(**feed_data)
            session.add(feed)
            print(f"Added feed: {feed_data['name']}")

        session.commit()

        total = session.query(FeedModel).count()
        print(f"\nTotal feeds in database: {total}")


if __name__ == "__main__":
    main()
