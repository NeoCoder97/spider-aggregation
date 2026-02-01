#!/usr/bin/env python3
"""
Seed common filter rules for spider-aggregation.

This script adds useful default filter rules to help filter out:
- Advertisements and sponsored content
- Low-quality content
- Specific language preferences
- Common spam patterns
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spider_aggregation.storage.database import DatabaseManager
from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository
from spider_aggregation.models.entry import FilterRuleCreate
from spider_aggregation.logger import get_logger

logger = get_logger(__name__)


# Common filter rules
DEFAULT_FILTER_RULES = [
    # Advertisement/Sponsored content filters
    {
        "name": "过滤广告关键词",
        "enabled": True,
        "rule_type": "keyword",
        "match_type": "exclude",
        "pattern": "广告|推广|赞助|sponsored|advertisement",
        "priority": 100,
    },
    {
        "name": "过滤推广链接",
        "enabled": True,
        "rule_type": "regex",
        "match_type": "exclude",
        "pattern": r"(promotion|promo|referral|affiliate|tracking)",
        "priority": 90,
    },

    # Quality filters
    {
        "name": "过滤标题过短的文章",
        "enabled": False,  # Disabled by default
        "rule_type": "regex",
        "match_type": "exclude",
        "pattern": r"^.{1,5}$",  # Title less than 5 characters
        "priority": 80,
    },
    {
        "name": "过滤无实际内容的文章",
        "enabled": False,
        "rule_type": "keyword",
        "match_type": "exclude",
        "pattern": "(点击查看|更多内容|请关注|阅读全文)",
        "priority": 70,
    },

    # Language preference - only include Chinese
    {
        "name": "仅保留中文内容",
        "enabled": False,  # Disabled by default, enable if you only want Chinese content
        "rule_type": "language",
        "match_type": "include",
        "pattern": "zh",
        "priority": 60,
    },

    # Language preference - only include English
    {
        "name": "仅保留英文内容",
        "enabled": False,  # Disabled by default
        "rule_type": "language",
        "match_type": "include",
        "pattern": "en",
        "priority": 60,
    },

    # Exclude specific languages
    {
        "name": "排除非主要语言",
        "enabled": True,
        "rule_type": "language",
        "match_type": "exclude",
        "pattern": "unknown|und",
        "priority": 50,
    },

    # Spam/low-quality patterns
    {
        "name": "过滤标题党",
        "enabled": False,
        "rule_type": "keyword",
        "match_type": "exclude",
        "pattern": "震惊|万万没想到|不看后悔|必看|速转|朋友圈疯传",
        "priority": 40,
    },

    # Content quality
    {
        "name": "过滤重复发布内容",
        "enabled": True,
        "rule_type": "keyword",
        "match_type": "exclude",
        "pattern": "(reprint|转载|来源|原文链接)",
        "priority": 30,
    },

    # Tech/Developer focused filters
    {
        "name": "仅保留技术相关内容",
        "enabled": False,
        "rule_type": "keyword",
        "match_type": "include",
        "pattern": "(开发|编程|算法|架构|代码|编程语言|框架|数据库|API|前端|后端|DevOps|AI|机器学习)",
        "priority": 20,
    },

    # Include specific topics of interest
    {
        "name": "包含Python相关内容",
        "enabled": False,
        "rule_type": "keyword",
        "match_type": "include",
        "pattern": "Python|Django|Flask|FastAPI",
        "priority": 10,
    },

    # Date-based quality filter
    {
        "name": "过滤旧新闻（超过1年）",
        "enabled": False,
        "rule_type": "regex",
        "match_type": "exclude",
        "pattern": r"(2020|2021|2022|2023).{0,5}(年|news|article)",
        "priority": 5,
    },
]


def seed_filter_rules(db_path: str, skip_existing: bool = True) -> int:
    """Seed default filter rules.

    Args:
        db_path: Path to the database file
        skip_existing: If True, skip rules that already exist by name

    Returns:
        Number of rules created
    """
    manager = DatabaseManager(db_path)

    created_count = 0
    skipped_count = 0

    with manager.session() as session:
        rule_repo = FilterRuleRepository(session)

        for rule_data in DEFAULT_FILTER_RULES:
            # Check if rule already exists
            existing = rule_repo.get_by_name(rule_data["name"])
            if existing:
                if skip_existing:
                    logger.info(f"Skipping existing rule: {rule_data['name']}")
                    skipped_count += 1
                    continue
                else:
                    logger.info(f"Updating existing rule: {rule_data['name']}")
                    rule_repo.update(existing, FilterRuleCreate(**rule_data))
                    created_count += 1
                    continue

            # Create new rule
            try:
                rule_create = FilterRuleCreate(**rule_data)
                rule_repo.create(rule_create)
                created_count += 1
                logger.info(f"Created rule: {rule_data['name']}")
            except Exception as e:
                logger.error(f"Failed to create rule '{rule_data['name']}': {e}")

    logger.info(f"Filter rules seeded: {created_count} created, {skipped_count} skipped")
    return created_count


def list_filter_rules(db_path: str) -> None:
    """List all current filter rules."""
    manager = DatabaseManager(db_path)

    with manager.session() as session:
        rule_repo = FilterRuleRepository(session)
        rules = rule_repo.list()

        if not rules:
            print("No filter rules found.")
            return

        print(f"\nCurrent filter rules ({len(rules)} total):")
        print("-" * 80)
        for rule in rules:
            status = "✓" if rule.enabled else "✗"
            print(f"{status} [{rule.priority}] {rule.name}")
            print(f"   Type: {rule.rule_type}, Match: {rule.match_type}")
            print(f"   Pattern: {rule.pattern[:60]}...")
            print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed default filter rules for spider-aggregation"
    )
    parser.add_argument(
        "--db-path",
        default="data/spider_aggregation.db",
        help="Path to the database file"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List current filter rules instead of seeding"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing rules instead of skipping them"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating"
    )

    args = parser.parse_args()

    # Ensure database file exists
    db_file = Path(args.db_path)
    if not db_file.exists():
        logger.error(f"Database not found at {args.db_path}")
        logger.error("Please run 'python scripts/init_db.py' first")
        sys.exit(1)

    if args.list:
        list_filter_rules(args.db_path)
    elif args.dry_run:
        print("Would create the following filter rules:")
        print("-" * 80)
        for rule in DEFAULT_FILTER_RULES:
            status = "✓" if rule["enabled"] else "✗"
            print(f"{status} [{rule['priority']}] {rule['name']}")
            print(f"   Type: {rule['rule_type']}, Match: {rule['match_type']}")
            print(f"   Pattern: {rule['pattern'][:60]}...")
            print()
        print(f"Total: {len(DEFAULT_FILTER_RULES)} rules")
    else:
        count = seed_filter_rules(
            db_path=args.db_path,
            skip_existing=not args.force
        )
        print(f"\n✓ Created {count} filter rules")
        print(f"Run 'python {Path(__file__).name} --list' to see all rules")


if __name__ == "__main__":
    main()
