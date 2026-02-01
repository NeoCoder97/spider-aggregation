"""
Unit tests for EntryRepository category methods.
"""

import pytest
from datetime import datetime, timedelta

from spider_aggregation.models import FeedCreate, CategoryCreate, EntryCreate
from spider_aggregation.storage.repositories.feed_repo import FeedRepository
from spider_aggregation.storage.repositories.category_repo import CategoryRepository
from spider_aggregation.storage.repositories.entry_repo import EntryRepository
from spider_aggregation.utils.hash_utils import compute_title_hash, compute_link_hash


class TestEntryRepositoryCategoryMethods:
    """Test EntryRepository category-related methods."""

    def create_test_entry(self, entry_repo, feed, title, days_ago=0):
        """Helper to create a test entry."""
        from spider_aggregation.utils.hash_utils import compute_title_hash, compute_link_hash

        published_at = datetime.utcnow() - timedelta(days=days_ago)
        link = f"https://example.com/{title.replace(' ', '-').lower()}"

        entry_data = EntryCreate(
            feed_id=feed.id,
            title=title,
            link=link,
            content=f"Content for {title}",
            published_at=published_at,
            title_hash=compute_title_hash(title),
            link_hash=compute_link_hash(link),
        )
        return entry_repo.create(entry_data)

    def test_list_by_category(self, db_session):
        """Test listing entries by category ID."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        # Create categories
        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")

        # Create feeds
        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2"))

        # Add feeds to categories
        cat_repo.add_feed_to_category(feed1, cat1)
        cat_repo.add_feed_to_category(feed2, cat2)

        # Create entries
        entry1 = self.create_test_entry(entry_repo, feed1, "Entry 1")
        entry2 = self.create_test_entry(entry_repo, feed1, "Entry 2")
        entry3 = self.create_test_entry(entry_repo, feed2, "Entry 3")

        # Get entries by category
        cat1_entries = entry_repo.list_by_category(cat1.id)
        assert len(cat1_entries) == 2
        assert {e.id for e in cat1_entries} == {entry1.id, entry2.id}

        cat2_entries = entry_repo.list_by_category(cat2.id)
        assert len(cat2_entries) == 1
        assert cat2_entries[0].id == entry3.id

    def test_list_by_category_name(self, db_session):
        """Test listing entries by category name."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        cat = cat_repo.create(name="Python")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2"))

        cat_repo.add_feed_to_category(feed1, cat)
        cat_repo.add_feed_to_category(feed2, cat)

        entry1 = self.create_test_entry(entry_repo, feed1, "Python 1")
        entry2 = self.create_test_entry(entry_repo, feed2, "Python 2")

        # Get entries by category name
        entries = entry_repo.list_by_category_name("Python")
        assert len(entries) == 2
        assert {e.id for e in entries} == {entry1.id, entry2.id}

    def test_list_by_categories(self, db_session):
        """Test listing entries by multiple category IDs."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")
        cat3 = cat_repo.create(name="其他")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2"))
        feed3 = feed_repo.create(FeedCreate(url="https://example.com/feed3"))

        cat_repo.add_feed_to_category(feed1, cat1)
        cat_repo.add_feed_to_category(feed2, cat2)
        cat_repo.add_feed_to_category(feed3, cat3)

        entry1 = self.create_test_entry(entry_repo, feed1, "Entry 1")
        entry2 = self.create_test_entry(entry_repo, feed2, "Entry 2")
        entry3 = self.create_test_entry(entry_repo, feed3, "Entry 3")

        # Get entries from cat1 OR cat2
        entries = entry_repo.list_by_categories([cat1.id, cat2.id])
        assert len(entries) == 2
        assert {e.id for e in entries} == {entry1.id, entry2.id}

    def test_list_by_categories_empty_list(self, db_session):
        """Test listing entries with empty category list."""
        entry_repo = EntryRepository(db_session)

        entries = entry_repo.list_by_categories([])
        assert entries == []

    def test_count_by_category(self, db_session):
        """Test counting entries by category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2"))

        cat_repo.add_feed_to_category(feed1, cat1)
        cat_repo.add_feed_to_category(feed2, cat2)

        # Create entries
        self.create_test_entry(entry_repo, feed1, "Entry 1")
        self.create_test_entry(entry_repo, feed1, "Entry 2")
        self.create_test_entry(entry_repo, feed2, "Entry 3")

        assert entry_repo.count_by_category(cat1.id) == 2
        assert entry_repo.count_by_category(cat2.id) == 1

    def test_search_by_category(self, db_session):
        """Test searching entries within a category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        cat = cat_repo.create(name="Python")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2"))

        cat_repo.add_feed_to_category(feed1, cat)
        # feed2 is not in the category

        entry1 = self.create_test_entry(entry_repo, feed1, "Python tutorial")
        entry2 = self.create_test_entry(entry_repo, feed1, "Django guide")
        entry3 = self.create_test_entry(entry_repo, feed2, "Python news")  # Not in category

        # Search within category
        results = entry_repo.search_by_category("Python", cat.id)
        assert len(results) == 1
        assert results[0].id == entry1.id

        # Search for "Django"
        results = entry_repo.search_by_category("Django", cat.id)
        assert len(results) == 1
        assert results[0].id == entry2.id

    def test_get_recent_by_category(self, db_session):
        """Test getting recent entries by category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        cat = cat_repo.create(name="技术博客")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2"))

        cat_repo.add_feed_to_category(feed1, cat)
        cat_repo.add_feed_to_category(feed2, cat)

        # Create entries with different ages
        entry1 = self.create_test_entry(entry_repo, feed1, "Entry 1", days_ago=1)
        entry2 = self.create_test_entry(entry_repo, feed1, "Entry 2", days_ago=3)
        entry3 = self.create_test_entry(entry_repo, feed2, "Entry 3", days_ago=10)  # Too old

        # Get entries from last 7 days
        recent = entry_repo.get_recent_by_category(cat.id, days=7)
        assert len(recent) == 2
        assert {e.id for e in recent} == {entry1.id, entry2.id}

        # Get entries from last 2 days
        recent = entry_repo.get_recent_by_category(cat.id, days=2)
        assert len(recent) == 1
        assert recent[0].id == entry1.id

    def test_get_stats_by_category(self, db_session):
        """Test getting entry statistics for a category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        cat = cat_repo.create(name="技术博客")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))

        cat_repo.add_feed_to_category(feed1, cat)

        # Create entries with different languages
        entry1 = self.create_test_entry(entry_repo, feed1, "Entry 1")
        entry1.language = "en"
        db_session.flush()

        entry2 = self.create_test_entry(entry_repo, feed1, "Entry 2")
        entry2.language = "zh"
        db_session.flush()

        entry3 = self.create_test_entry(entry_repo, feed1, "Entry 3")
        entry3.language = "en"
        db_session.flush()

        # Get stats
        stats = entry_repo.get_stats_by_category(cat.id)

        assert stats["total"] == 3
        assert stats["language_counts"]["en"] == 2
        assert stats["language_counts"]["zh"] == 1
        assert stats["most_recent"] is not None

    def test_list_by_category_pagination(self, db_session):
        """Test pagination when listing entries by category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        cat = cat_repo.create(name="测试分类")

        feed = feed_repo.create(FeedCreate(url="https://example.com/feed"))
        cat_repo.add_feed_to_category(feed, cat)

        # Create 5 entries
        for i in range(5):
            self.create_test_entry(entry_repo, feed, f"Entry {i}")

        # Test pagination
        page1 = entry_repo.list_by_category(cat.id, limit=2, offset=0)
        assert len(page1) == 2

        page2 = entry_repo.list_by_category(cat.id, limit=2, offset=2)
        assert len(page2) == 2

        page3 = entry_repo.list_by_category(cat.id, limit=2, offset=4)
        assert len(page3) == 1

    def test_list_by_category_ordering(self, db_session):
        """Test ordering when listing entries by category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)
        entry_repo = EntryRepository(db_session)

        cat = cat_repo.create(name="测试分类")

        feed = feed_repo.create(FeedCreate(url="https://example.com/feed"))
        cat_repo.add_feed_to_category(feed, cat)

        # Create entries with different published times
        entry1 = self.create_test_entry(entry_repo, feed, "Entry 1", days_ago=3)
        entry2 = self.create_test_entry(entry_repo, feed, "Entry 2", days_ago=1)
        entry3 = self.create_test_entry(entry_repo, feed, "Entry 3", days_ago=2)

        # Descending order (default)
        entries_desc = entry_repo.list_by_category(cat.id, order_desc=True)
        assert entries_desc[0].id == entry2.id  # Most recent

        # Ascending order
        entries_asc = entry_repo.list_by_category(cat.id, order_desc=False)
        assert entries_asc[0].id == entry1.id  # Oldest
