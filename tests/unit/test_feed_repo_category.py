"""
Unit tests for FeedRepository category methods.
"""

import pytest

from spider_aggregation.models import FeedCreate, CategoryCreate
from spider_aggregation.storage.repositories.feed_repo import FeedRepository
from spider_aggregation.storage.repositories.category_repo import CategoryRepository


class TestFeedRepositoryCategoryMethods:
    """Test FeedRepository category-related methods."""

    def test_get_by_category(self, db_session):
        """Test getting feeds by category ID."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        # Create categories
        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")

        # Create feeds
        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1", name="Feed 1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2", name="Feed 2"))
        feed3 = feed_repo.create(FeedCreate(url="https://example.com/feed3", name="Feed 3"))

        # Add feeds to categories
        cat_repo.add_feed_to_category(feed1, cat1)
        cat_repo.add_feed_to_category(feed2, cat1)
        cat_repo.add_feed_to_category(feed3, cat2)

        # Get feeds by category
        cat1_feeds = feed_repo.get_by_category(cat1.id)
        assert len(cat1_feeds) == 2
        assert {f.id for f in cat1_feeds} == {feed1.id, feed2.id}

        cat2_feeds = feed_repo.get_by_category(cat2.id)
        assert len(cat2_feeds) == 1
        assert cat2_feeds[0].id == feed3.id

    def test_get_by_category_enabled_only(self, db_session):
        """Test getting enabled feeds only by category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1", enabled=True))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2", enabled=False))
        feed3 = feed_repo.create(FeedCreate(url="https://example.com/feed3", enabled=True))

        cat_repo.add_feed_to_category(feed1, cat1)
        cat_repo.add_feed_to_category(feed2, cat1)
        cat_repo.add_feed_to_category(feed3, cat1)

        # Get all feeds
        all_feeds = feed_repo.get_by_category(cat1.id, enabled_only=False)
        assert len(all_feeds) == 3

        # Get enabled feeds only
        enabled_feeds = feed_repo.get_by_category(cat1.id, enabled_only=True)
        assert len(enabled_feeds) == 2
        assert {f.id for f in enabled_feeds} == {feed1.id, feed3.id}

    def test_get_by_category_name(self, db_session):
        """Test getting feeds by category name."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat = cat_repo.create(name="Python")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2"))

        cat_repo.add_feed_to_category(feed1, cat)
        cat_repo.add_feed_to_category(feed2, cat)

        # Get feeds by category name
        feeds = feed_repo.get_by_category_name("Python")
        assert len(feeds) == 2
        assert {f.id for f in feeds} == {feed1.id, feed2.id}

        # Non-existent category
        empty_feeds = feed_repo.get_by_category_name("NonExistent")
        assert len(empty_feeds) == 0

    def test_get_by_categories(self, db_session):
        """Test getting feeds by multiple category IDs."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")
        cat3 = cat_repo.create(name="其他")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1"))
        feed2 = feed_repo.create(FeedCreate(url="https://example.com/feed2"))
        feed3 = feed_repo.create(FeedCreate(url="https://example.com/feed3"))
        feed4 = feed_repo.create(FeedCreate(url="https://example.com/feed4"))

        # Add feeds to categories
        cat_repo.add_feed_to_category(feed1, cat1)
        cat_repo.add_feed_to_category(feed2, cat1)
        cat_repo.add_feed_to_category(feed2, cat2)  # feed2 in both cat1 and cat2
        cat_repo.add_feed_to_category(feed3, cat2)
        cat_repo.add_feed_to_category(feed4, cat3)

        # Get feeds from cat1 OR cat2
        feeds = feed_repo.get_by_categories([cat1.id, cat2.id])
        # Should get feed1, feed2, feed3 (feed4 is only in cat3)
        assert len(feeds) == 3
        assert {f.id for f in feeds} == {feed1.id, feed2.id, feed3.id}

    def test_get_by_categories_empty_list(self, db_session):
        """Test getting feeds with empty category list."""
        feed_repo = FeedRepository(db_session)

        feeds = feed_repo.get_by_categories([])
        assert feeds == []

    def test_count_by_category(self, db_session):
        """Test counting feeds by category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")

        feed1 = feed_repo.create(FeedCreate(url="https://example.com/feed1", enabled=True))
        feed2 = feed_repo.create(FeedCreate(url="https.comexample.com/feed2", enabled=False))

        cat_repo.add_feed_to_category(feed1, cat1)
        cat_repo.add_feed_to_category(feed2, cat1)

        # Count all feeds
        assert feed_repo.count_by_category(cat1.id) == 2

        # Count enabled feeds only
        assert feed_repo.count_by_category(cat1.id, enabled_only=True) == 1

        # Empty category
        assert feed_repo.count_by_category(cat2.id) == 0

    def test_get_categories(self, db_session):
        """Test getting categories for a feed."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")
        cat3 = cat_repo.create(name="Python")

        feed = feed_repo.create(FeedCreate(url="https://example.com/feed"))

        # Add categories via CategoryRepository
        cat_repo.add_feed_to_category(feed, cat1)
        cat_repo.add_feed_to_category(feed, cat2)
        cat_repo.add_feed_to_category(feed, cat3)

        # Get categories via FeedRepository
        categories = feed_repo.get_categories(feed)
        assert len(categories) == 3
        assert {c.id for c in categories} == {cat1.id, cat2.id, cat3.id}

    def test_set_categories(self, db_session):
        """Test setting categories for a feed (replace all)."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")
        cat3 = cat_repo.create(name="Python")
        cat4 = cat_repo.create(name="AI")

        feed = feed_repo.create(FeedCreate(url="https://example.com/feed"))

        # Initial categories
        cat_repo.add_feed_to_category(feed, cat1)
        cat_repo.add_feed_to_category(feed, cat2)
        assert len(feed.categories) == 2

        # Replace with new categories
        updated_feed = feed_repo.set_categories(feed, [cat2.id, cat3.id, cat4.id])

        assert len(updated_feed.categories) == 3
        assert {c.id for c in updated_feed.categories} == {cat2.id, cat3.id, cat4.id}

    def test_add_category(self, db_session):
        """Test adding a category to a feed."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")

        feed = feed_repo.create(FeedCreate(url="https://example.com/feed"))

        # Add category via FeedRepository
        feed_repo.add_category(feed, cat1)
        assert len(feed.categories) == 1
        assert feed.categories[0].id == cat1.id

        # Add another category
        feed_repo.add_category(feed, cat2)
        assert len(feed.categories) == 2

        # Adding duplicate should be idempotent
        feed_repo.add_category(feed, cat1)
        assert len(feed.categories) == 2

    def test_remove_category(self, db_session):
        """Test removing a category from a feed."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")

        feed = feed_repo.create(FeedCreate(url="https://example.com/feed"))

        feed_repo.add_category(feed, cat1)
        feed_repo.add_category(feed, cat2)
        assert len(feed.categories) == 2

        # Remove one category
        feed_repo.remove_category(feed, cat1)
        assert len(feed.categories) == 1
        assert feed.categories[0].id == cat2.id

        # Removing non-existent category should be safe
        feed_repo.remove_category(feed, cat1)
        assert len(feed.categories) == 1

    def test_clear_categories(self, db_session):
        """Test clearing all categories from a feed."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat1 = cat_repo.create(name="技术博客")
        cat2 = cat_repo.create(name="新闻")
        cat3 = cat_repo.create(name="Python")

        feed = feed_repo.create(FeedCreate(url="https://example.com/feed"))

        feed_repo.add_category(feed, cat1)
        feed_repo.add_category(feed, cat2)
        feed_repo.add_category(feed, cat3)
        assert len(feed.categories) == 3

        # Clear all categories
        feed_repo.clear_categories(feed)
        assert len(feed.categories) == 0

    def test_get_by_category_pagination(self, db_session):
        """Test pagination when getting feeds by category."""
        feed_repo = FeedRepository(db_session)
        cat_repo = CategoryRepository(db_session)

        cat = cat_repo.create(name="测试分类")

        # Create 5 feeds
        feeds = []
        for i in range(5):
            feed = feed_repo.create(FeedCreate(url=f"https://example.com/feed{i}"))
            feeds.append(feed)
            cat_repo.add_feed_to_category(feed, cat)

        # Test pagination
        page1 = feed_repo.get_by_category(cat.id, limit=2, offset=0)
        assert len(page1) == 2

        page2 = feed_repo.get_by_category(cat.id, limit=2, offset=2)
        assert len(page2) == 2

        page3 = feed_repo.get_by_category(cat.id, limit=2, offset=4)
        assert len(page3) == 1
