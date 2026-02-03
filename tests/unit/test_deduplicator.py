"""Unit tests for content deduplicator."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from spider_aggregation.core.deduplicator import (
    DedupResult,
    DedupStrategy,
    Deduplicator,
    create_deduplicator,
)
from spider_aggregation.models import EntryModel, FeedModel
from spider_aggregation.storage.repositories.feed_repo import FeedRepository
from spider_aggregation.utils.hash_utils import (
    compute_content_hash,
    compute_link_hash,
    compute_md5_hash,
    compute_sha256_hash,
    compute_similarity_hash,
    compute_title_hash,
)


class TestHashUtils:
    """Tests for hash utility functions."""

    def test_compute_md5_hash(self):
        """Test MD5 hash computation."""
        # Basic string
        result = compute_md5_hash("test content")
        assert result is not None
        assert len(result) == 32  # MD5 is 32 hex characters

        # Same content produces same hash
        assert compute_md5_hash("test") == compute_md5_hash("test")

        # Different content produces different hash
        assert compute_md5_hash("test") != compute_md5_hash("test2")

        # None and empty string
        assert compute_md5_hash(None) is None
        assert compute_md5_hash("") is None

        # Case insensitive
        assert compute_md5_hash("TEST") == compute_md5_hash("test")

        # Whitespace normalization
        assert compute_md5_hash("  test  ") == compute_md5_hash("test")

    def test_compute_sha256_hash(self):
        """Test SHA256 hash computation."""
        result = compute_sha256_hash("test content")
        assert result is not None
        assert len(result) == 64  # SHA256 is 64 hex characters

        # Same content produces same hash
        assert compute_sha256_hash("test") == compute_sha256_hash("test")

        # Different from MD5
        assert compute_md5_hash("test") != compute_sha256_hash("test")

    def test_compute_link_hash(self):
        """Test link hash computation."""
        # Basic URL
        result = compute_link_hash("https://example.com/article")
        assert result is not None

        # Case insensitive
        assert (
            compute_link_hash("https://example.com/article")
            == compute_link_hash("HTTPS://EXAMPLE.COM/ARTICLE")
        )

        # Trailing slash normalization
        assert (
            compute_link_hash("https://example.com/article")
            == compute_link_hash("https://example.com/article/")
        )

        # Tracking parameter removal
        base = "https://example.com/article"
        with_utm = "https://example.com/article?utm_source=test&utm_medium=email"
        assert compute_link_hash(base) == compute_link_hash(with_utm)

        # Invalid URLs return None
        assert compute_link_hash("not-a-url") is None
        assert compute_link_hash(None) is None

    def test_compute_title_hash(self):
        """Test title hash computation."""
        # Basic title
        result = compute_title_hash("Test Title")
        assert result is not None

        # Whitespace normalization
        assert compute_title_hash("Test   Title") == compute_title_hash("Test Title")

        # Case insensitive
        assert compute_title_hash("TEST TITLE") == compute_title_hash("test title")

        # Empty and None
        assert compute_title_hash("") is None
        assert compute_title_hash(None) is None

    def test_compute_content_hash(self):
        """Test content hash computation."""
        # Basic content
        result = compute_content_hash("This is some content")
        assert result is not None

        # Uses SHA256
        assert len(result) == 64

        # Case insensitive
        assert compute_content_hash("Content") == compute_content_hash("content")

        # Whitespace normalization
        assert compute_content_hash("Content  with   spaces") == compute_content_hash(
            "Content with spaces"
        )

        # Empty and None
        assert compute_content_hash("") is None
        assert compute_content_hash(None) is None

        # Fingerprint based on first 500 chars
        long_content = "a" * 1000
        result = compute_content_hash(long_content)
        assert result is not None

    def test_compute_similarity_hash(self):
        """Test similarity hash computation."""
        # Basic content
        result = compute_similarity_hash("This is some content")
        assert result is not None

        # Short content
        result = compute_similarity_hash("Short")
        assert result is not None

        # Long content uses sampling
        long = "word " * 500
        result = compute_similarity_hash(long)
        assert result is not None

        # Empty and None
        assert compute_similarity_hash("") is None
        assert compute_similarity_hash(None) is None


class TestDeduplicator:
    """Tests for Deduplicator."""

    def test_init(self):
        """Test deduplicator initialization."""
        dedup = Deduplicator()

        assert dedup.session is None
        assert dedup.strategy == DedupStrategy.MEDIUM
        assert dedup.stats["checks"] == 0

    def test_init_with_session(self, db_session: Session):
        """Test deduplicator with database session."""
        dedup = Deduplicator(session=db_session)

        assert dedup.session is db_session

    def test_init_with_custom_strategy(self):
        """Test deduplicator with custom strategy."""
        dedup = Deduplicator(strategy=DedupStrategy.STRICT)

        assert dedup.strategy == DedupStrategy.STRICT

    def test_check_duplicate_no_session(self):
        """Test duplicate check without session."""
        dedup = Deduplicator(session=None)

        entry = {
            "title": "Test Entry",
            "link": "https://example.com/article",
        }

        result = dedup.check_duplicate(entry, feed_id=1)

        assert result.is_duplicate is False
        assert result.reason == "No database session"

    def test_check_duplicate_by_link(self, db_session: Session):
        """Test duplicate detection by link."""
        # Create a feed and entry
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add existing entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        link_hash = compute_link_hash("https://example.com/article")
        title_hash = compute_title_hash("Test Entry")
        existing = entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Entry",
                link="https://example.com/article",
                link_hash=link_hash,
                title_hash=title_hash,
            )
        )

        # Check for duplicate
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.RELAXED)
        entry = {
            "title": "Different Title",  # Different title but same link
            "link": "https://example.com/article",
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        assert result.is_duplicate is True
        assert "Duplicate link" in result.reason
        assert result.existing_entry.id == existing.id

    def test_check_duplicate_by_title(self, db_session: Session):
        """Test duplicate detection by title."""
        # Create a feed and entry
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add existing entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        title_hash = compute_title_hash("Test Entry Title")
        link_hash = compute_link_hash("https://example.com/article1")
        existing = entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Entry Title",
                link="https://example.com/article1",
                link_hash=link_hash,
                title_hash=title_hash,
            )
        )

        # Check for duplicate with same title, different link
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.RELAXED)
        entry = {
            "title": "Test Entry Title",  # Same title
            "link": "https://example.com/article2",  # Different link
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        assert result.is_duplicate is True
        assert "Duplicate title" in result.reason
        assert result.existing_entry.id == existing.id

    def test_check_duplicate_no_match(self, db_session: Session):
        """Test when no duplicate is found."""
        # Create a feed
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Check for new entry
        dedup = Deduplicator(session=db_session)
        entry = {
            "title": "Brand New Entry",
            "link": "https://example.com/new-article",
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        assert result.is_duplicate is False
        assert result.reason == "No duplicate"

    def test_strict_strategy(self, db_session: Session):
        """Test STRICT strategy requires both title AND content match."""
        # Create a feed and entry
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add existing entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        title_hash = compute_title_hash("Test Entry")
        content_hash = compute_content_hash("Test content here")
        link_hash = compute_link_hash("https://example.com/a1")
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Entry",
                link="https://example.com/a1",
                content="Test content here",
                link_hash=link_hash,
                title_hash=title_hash,
                content_hash=content_hash,
            )
        )

        # Check: same title but different content - should NOT match in strict mode
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.STRICT)
        entry = {
            "title": "Test Entry",
            "content": "Different content",
            "link": "https://example.com/a2",
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        # Strict mode requires BOTH title AND content match
        assert result.is_duplicate is False

    def test_medium_strategy(self, db_session: Session):
        """Test MEDIUM strategy matches on title OR content."""
        # Create a feed and entry
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add existing entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        title_hash = compute_title_hash("Test Entry")
        link_hash = compute_link_hash("https://example.com/a1")
        content_hash = compute_content_hash("Original content")
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Entry",
                link="https://example.com/a1",
                content="Original content",
                link_hash=link_hash,
                title_hash=title_hash,
                content_hash=content_hash,
            )
        )

        # Check: same title but different content - should match in medium mode
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.MEDIUM)
        entry = {
            "title": "Test Entry",
            "content": "Different content",
            "link": "https://example.com/a2",
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        # Medium mode matches on title OR content
        assert result.is_duplicate is True
        assert "Duplicate title" in result.reason

    def test_check_duplicate_across_feeds(self, db_session: Session):
        """Test duplicate checking across multiple feeds."""
        # Create two feeds
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed1 = repo.create(
            FeedCreate(url="https://example.com/feed1.xml", name="Feed 1")
        )
        feed2 = repo.create(
            FeedCreate(url="https://example.com/feed2.xml", name="Feed 2")
        )

        # Add entry to feed1
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        link_hash = compute_link_hash("https://example.com/article")
        title_hash = compute_title_hash("Test Entry")
        existing = entry_repo.create(
            EntryCreate(
                feed_id=feed1.id,
                title="Test Entry",
                link="https://example.com/article",
                link_hash=link_hash,
                title_hash=title_hash,
            )
        )

        # Check across feeds
        dedup = Deduplicator(session=db_session)
        entry = {
            "title": "Different Title",
            "link": "https://example.com/article",  # Same link
        }

        # Check in specific feeds
        result = dedup.check_duplicate_across_feeds(
            entry, feed_ids=[feed1.id, feed2.id]
        )

        assert result.is_duplicate is True
        assert "across feeds" in result.reason

    def test_compute_hashes(self):
        """Test hash computation for entry."""
        dedup = Deduplicator()

        entry = {
            "title": "Test Entry",
            "link": "https://example.com/article",
            "content": "Test content",
            "summary": "Test summary",
        }

        hashes = dedup.compute_hashes(entry)

        assert hashes["link_hash"] is not None
        assert hashes["title_hash"] is not None
        assert hashes["content_hash"] is not None

    def test_compute_hashes_with_fallback(self):
        """Test hash computation falls back to summary when content is missing."""
        dedup = Deduplicator()

        entry = {
            "title": "Test Entry",
            "link": "https://example.com/article",
            "summary": "Test summary",  # Only summary, no content
        }

        hashes = dedup.compute_hashes(entry)

        # content_hash should use summary as fallback
        assert hashes["content_hash"] is not None

    def test_get_stats(self):
        """Test getting deduplication statistics."""
        dedup = Deduplicator()

        stats = dedup.get_stats()

        assert stats["checks"] == 0
        assert stats["duplicates_found"] == 0

    def test_stats_tracking(self, db_session: Session):
        """Test that statistics are tracked correctly."""
        # Create a feed
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add existing entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        title_hash = compute_title_hash("Test Entry")
        link_hash = compute_link_hash("https://example.com/article")
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Entry",
                link="https://example.com/article",
                link_hash=link_hash,
                title_hash=title_hash,
            )
        )

        # Check duplicates
        dedup = Deduplicator(session=db_session)
        entry = {"title": "Test", "link": "https://example.com/article"}
        dedup.check_duplicate(entry, feed_id=feed.id)

        stats = dedup.get_stats()

        assert stats["checks"] == 1
        assert stats["duplicates_found"] == 1
        assert stats["link_matches"] == 1

    def test_reset_stats(self, db_session: Session):
        """Test resetting statistics."""
        # Create a feed
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add existing entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        title_hash = compute_title_hash("Test Entry")
        link_hash = compute_link_hash("https://example.com/article")
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Entry",
                link="https://example.com/article",
                link_hash=link_hash,
                title_hash=title_hash,
            )
        )

        # Check duplicates
        dedup = Deduplicator(session=db_session)
        entry = {"title": "Test", "link": "https://example.com/article"}
        dedup.check_duplicate(entry, feed_id=feed.id)

        # Reset
        dedup.reset_stats()

        stats = dedup.get_stats()
        assert stats["checks"] == 0
        assert stats["duplicates_found"] == 0


class TestDedupResult:
    """Tests for DedupResult."""

    def test_duplicate_result(self):
        """Test result for duplicate entry."""
        from spider_aggregation.models import EntryModel

        entry = EntryModel(id=1, title="Test")
        result = DedupResult(
            is_duplicate=True, reason="Duplicate link", existing_entry=entry
        )

        assert result.is_duplicate is True
        assert result.reason == "Duplicate link"
        assert result.existing_entry.id == 1

    def test_non_duplicate_result(self):
        """Test result for non-duplicate entry."""
        result = DedupResult(is_duplicate=False, reason="No duplicate")

        assert result.is_duplicate is False
        assert result.reason == "No duplicate"
        assert result.existing_entry is None

    def test_repr(self):
        """Test result string representation."""
        result = DedupResult(is_duplicate=True, reason="Test reason")

        repr_str = repr(result)
        assert "is_duplicate=True" in repr_str
        assert "Test reason" in repr_str


class TestCreateDeduplicator:
    """Tests for create_deduplicator factory function."""

    def test_create_deduplicator_default(self):
        """Test creating deduplicator with defaults."""
        dedup = create_deduplicator()

        assert isinstance(dedup, Deduplicator)
        assert dedup.strategy == DedupStrategy.MEDIUM

    def test_create_deduplicator_with_session(self, db_session: Session):
        """Test creating deduplicator with session."""
        dedup = create_deduplicator(session=db_session)

        assert isinstance(dedup, Deduplicator)
        assert dedup.session is db_session

    def test_create_deduplicator_with_strategy(self):
        """Test creating deduplicator with custom strategy."""
        dedup = create_deduplicator(strategy=DedupStrategy.STRICT)

        assert isinstance(dedup, Deduplicator)
        assert dedup.strategy == DedupStrategy.STRICT


class TestDeduplicatorExtended:
    """Extended tests for Deduplicator to improve coverage."""

    def test_relaxed_strategy_title_match(self, db_session: Session):
        """Test RELAXED strategy matches on title only."""
        # Create a feed and entry
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add existing entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        title_hash = compute_title_hash("Test Entry Title")
        link_hash = compute_link_hash("https://example.com/article1")
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Entry Title",
                link="https://example.com/article1",
                link_hash=link_hash,
                title_hash=title_hash,
            )
        )

        # Check with RELAXED strategy - same title, different link
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.RELAXED)
        entry = {
            "title": "Test Entry Title",
            "link": "https://example.com/article2",  # Different link
            "content": "Different content",
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        # RELAXED should match on title
        assert result.is_duplicate is True
        assert "Duplicate title" in result.reason

    def test_relaxed_strategy_no_title_match(self, db_session: Session):
        """Test RELAXED strategy doesn't match when title differs."""
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Original Title",
                link="https://example.com/article1",
                link_hash=compute_link_hash("https://example.com/article1"),
                title_hash=compute_title_hash("Original Title"),
            )
        )

        # Different title, different link
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.RELAXED)
        entry = {
            "title": "Different Title",
            "link": "https://example.com/article2",
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        # Should NOT match (no title match)
        assert result.is_duplicate is False

    def test_cross_feed_dedup_with_feed_ids_filter(self, db_session: Session):
        """Test cross-feed deduplication with specific feed IDs."""
        # Create three feeds
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed1 = repo.create(FeedCreate(url="https://example.com/feed1.xml", name="Feed 1"))
        feed2 = repo.create(FeedCreate(url="https://example.com/feed2.xml", name="Feed 2"))
        feed3 = repo.create(FeedCreate(url="https://example.com/feed3.xml", name="Feed 3"))

        # Add entry to feed1
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        entry_repo.create(
            EntryCreate(
                feed_id=feed1.id,
                title="Test Entry",
                link="https://example.com/article",
                link_hash=compute_link_hash("https://example.com/article"),
                title_hash=compute_title_hash("Test Entry"),
            )
        )

        # Check across feed1 and feed2 only (should find duplicate)
        dedup = Deduplicator(session=db_session)
        entry = {"title": "Test", "link": "https://example.com/article"}

        result = dedup.check_duplicate_across_feeds(
            entry, feed_ids=[feed1.id, feed2.id]
        )

        assert result.is_duplicate is True

        # Check across feed3 only (should NOT find duplicate)
        result = dedup.check_duplicate_across_feeds(
            entry, feed_ids=[feed3.id]
        )

        assert result.is_duplicate is False

    def test_cross_feed_dedup_all_feeds(self, db_session: Session):
        """Test cross-feed deduplication across all feeds."""
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed1 = repo.create(FeedCreate(url="https://example.com/feed1.xml", name="Feed 1"))
        feed2 = repo.create(FeedCreate(url="https://example.com/feed2.xml", name="Feed 2"))

        # Add entry to feed1
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        entry_repo.create(
            EntryCreate(
                feed_id=feed1.id,
                title="Test Entry",
                link="https://example.com/article",
                link_hash=compute_link_hash("https://example.com/article"),
                title_hash=compute_title_hash("Test Entry"),
            )
        )

        # Check across all feeds (no feed_ids filter)
        dedup = Deduplicator(session=db_session)
        entry = {"title": "Test", "link": "https://example.com/article"}

        result = dedup.check_duplicate_across_feeds(entry, feed_ids=None)

        assert result.is_duplicate is True
        assert "across feeds" in result.reason

    def test_cross_feed_dedup_by_title(self, db_session: Session):
        """Test cross-feed deduplication by title."""
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed1 = repo.create(FeedCreate(url="https://example.com/feed1.xml", name="Feed 1"))
        feed2 = repo.create(FeedCreate(url="https://example.com/feed2.xml", name="Feed 2"))

        # Add entry to feed1
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        title_hash = compute_title_hash("Shared Title")
        entry_repo.create(
            EntryCreate(
                feed_id=feed1.id,
                title="Shared Title",
                link="https://example.com/article1",
                link_hash=compute_link_hash("https://example.com/article1"),
                title_hash=title_hash,
            )
        )

        # Check for duplicate by title across feeds
        dedup = Deduplicator(session=db_session)
        entry = {
            "title": "Shared Title",
            "link": "https://example.com/article2",  # Different link
        }

        result = dedup.check_duplicate_across_feeds(
            entry, feed_ids=[feed1.id, feed2.id]
        )

        assert result.is_duplicate is True
        assert "across feeds" in result.reason

    def test_medium_strategy_content_match(self, db_session: Session):
        """Test MEDIUM strategy matches on content when enabled."""
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add entry with specific content
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        content_hash = compute_content_hash("This is the original content")
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Different Title",
                link="https://example.com/article1",
                link_hash=compute_link_hash("https://example.com/article1"),
                title_hash=compute_title_hash("Different Title"),
                content_hash=content_hash,
            )
        )

        # Check with content match but different title
        # Need to enable content check in the deduplicator
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.MEDIUM)

        # Mock enable_content_check to True for this test
        with patch.object(dedup, "enable_content_check", True):
            entry = {
                "title": "Completely Different Title",
                "link": "https://example.com/article2",
                "content": "This is the original content",  # Same content
            }

            result = dedup.check_duplicate(entry, feed_id=feed.id)

            # MEDIUM with content check should match
            assert result.is_duplicate is True
            assert "Duplicate content" in result.reason

    def test_strict_strategy_both_match(self, db_session: Session):
        """Test STRICT strategy requires both title AND content match."""
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Title",
                link="https://example.com/article1",
                link_hash=compute_link_hash("https://example.com/article1"),
                title_hash=compute_title_hash("Test Title"),
                content_hash=compute_content_hash("Test Content"),
            )
        )

        # Same title AND same content - should match
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.STRICT)
        entry = {
            "title": "Test Title",
            "content": "Test Content",
            "link": "https://example.com/article2",
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        assert result.is_duplicate is True
        assert "title and content" in result.reason

    def test_compute_hashes_with_summary_fallback(self):
        """Test compute_hashes falls back to summary for content_hash."""
        dedup = Deduplicator()

        entry = {
            "title": "Test",
            "link": "https://example.com/article",
            "summary": "Summary text",  # Only summary, no content
        }

        hashes = dedup.compute_hashes(entry)

        # content_hash should be computed from summary
        assert hashes["content_hash"] is not None

    def test_compute_hashes_with_no_content_fields(self):
        """Test compute_hashes when no content fields exist."""
        dedup = Deduplicator()

        entry = {
            "title": "Test",
            "link": "https://example.com/article",
            # No summary or content
        }

        hashes = dedup.compute_hashes(entry)

        # content_hash should be None
        assert hashes["content_hash"] is None
        # But other hashes should be computed
        assert hashes["link_hash"] is not None
        assert hashes["title_hash"] is not None

    def test_check_duplicate_disabled_title_check(self, db_session: Session):
        """Test duplicate check with title checking disabled."""
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed = repo.create(FeedCreate(url="https://example.com/feed.xml", name="Test Feed"))

        # Add existing entry
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository
        from spider_aggregation.models.entry import EntryCreate

        entry_repo = EntryRepository(db_session)
        title_hash = compute_title_hash("Test Title")
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Title",
                link="https://example.com/article1",
                link_hash=compute_link_hash("https://example.com/article1"),
                title_hash=title_hash,
            )
        )

        # Check with title checking disabled via mock
        dedup = Deduplicator(session=db_session, strategy=DedupStrategy.RELAXED)

        # Mock enable_title_check to False
        with patch.object(dedup, "enable_title_check", False):
            entry = {
                "title": "Test Title",  # Same title
                "link": "https://example.com/article2",  # Different link
            }

            result = dedup.check_duplicate(entry, feed_id=feed.id)

            # Should NOT match (title checking disabled, link is different)
            assert result.is_duplicate is False
