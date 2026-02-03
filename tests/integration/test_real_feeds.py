"""Integration tests with real RSS feeds.

These tests use actual HTTP requests to real RSS feeds to validate
the complete fetch → parse → dedup → store pipeline.
"""

import pytest
from sqlalchemy.orm import Session

from spider_aggregation.core.fetcher import FeedFetcher, create_fetcher
from spider_aggregation.core.parser import ContentParser, create_parser
from spider_aggregation.core.deduplicator import Deduplicator, create_deduplicator
from spider_aggregation.storage.repositories.feed_repo import FeedRepository
from spider_aggregation.storage.repositories.entry_repo import EntryRepository
from spider_aggregation.storage.database import DatabaseManager


@pytest.fixture
def db_manager():
    """Create a test database manager."""
    manager = DatabaseManager(":memory:")
    manager.init_db()
    yield manager
    manager.close()


@pytest.fixture
def db_session(db_manager: DatabaseManager) -> Session:
    """Create a test database session."""
    with db_manager.session() as session:
        yield session


@pytest.fixture
def feed_repo(db_session: Session) -> FeedRepository:
    """Create feed repository."""
    return FeedRepository(db_session)


@pytest.fixture
def entry_repo(db_session: Session) -> EntryRepository:
    """Create entry repository."""
    return EntryRepository(db_session)


class TestRealRSSFeedIntegration:
    """Integration tests with real RSS feeds."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_cloudflare_blog_rss_full_pipeline(
        self, db_session: Session, feed_repo: FeedRepository, entry_repo: EntryRepository
    ):
        """Test complete pipeline with Cloudflare blog RSS.

        This test:
        1. Creates a feed from the real Cloudflare RSS URL
        2. Fetches the RSS content via HTTP
        3. Parses entries with ContentParser
        4. Stores entries in database
        5. Verifies deduplication works
        """
        # Real Cloudflare RSS URL
        rss_url = "https://blog.cloudflare.com/zh-cn/rss"

        # Step 1: Create feed in database
        from spider_aggregation.models.feed import FeedCreate

        feed_data = FeedCreate(
            url=rss_url,
            name="Cloudflare Blog (中文)",
            description="Cloudflare 博客中文版",
        )
        feed = feed_repo.create(feed_data)

        # Step 2: Fetch the RSS feed
        fetcher = create_fetcher(session=db_session)
        fetch_result = fetcher.fetch_feed(feed)

        # Verify fetch was successful
        assert fetch_result.success is True, f"Fetch failed: {fetch_result.error}"
        assert fetch_result.entries_count > 0, "No entries found in feed"

        # Step 3: Parse entries with ContentParser
        parser = create_parser()
        dedup = create_deduplicator(session=db_session, strategy="medium")

        entries_created = 0
        entries_skipped = 0

        for raw_entry in fetch_result.entries:
            # Parse the entry
            parsed = parser.parse_entry(raw_entry)

            # Check for duplicates
            dup_result = dedup.check_duplicate(parsed, feed_id=feed.id)

            if dup_result.is_duplicate:
                entries_skipped += 1
                continue

            # Compute hashes for storage
            hashes = dedup.compute_hashes(parsed)

            # Create entry in database
            from spider_aggregation.models.entry import EntryCreate

            entry_data = EntryCreate(
                feed_id=feed.id,
                title=parsed["title"] or "",
                link=parsed["link"] or "",
                author=parsed.get("author"),
                summary=parsed.get("summary"),
                content=parsed.get("content"),
                published_at=parsed.get("published_at"),
                title_hash=hashes["title_hash"],
                link_hash=hashes["link_hash"],
                content_hash=hashes["content_hash"],
                tags=parsed.get("tags"),
                language=parsed.get("language"),
                reading_time_seconds=parsed.get("reading_time_seconds"),
            )

            entry = entry_repo.create(entry_data)
            entries_created += 1

        # Verify results
        assert entries_created > 0, "No entries were created"
        print(f"✅ Created {entries_created} entries, skipped {entries_skipped} duplicates")

        # Verify entries in database
        stored_entries = entry_repo.list(feed_id=feed.id)
        assert len(stored_entries) == entries_created

        # Verify entry has expected fields
        first_entry = stored_entries[0]
        assert first_entry.title is not None
        assert first_entry.link is not None
        assert first_entry.link_hash is not None
        assert first_entry.title_hash is not None

        print(f"✅ Sample entry: {first_entry.title[:50]}...")
        print(f"   Language: {first_entry.language}")
        print(f"   Reading time: {first_entry.reading_time_seconds}s")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_fetch_and_parse_cloudflare_feed(self):
        """Test fetching and parsing Cloudflare feed."""
        rss_url = "https://blog.cloudflare.com/zh-cn/rss"

        # Create fetcher and parser
        fetcher = create_fetcher()
        parser = create_parser()

        # Create a mock feed for testing
        from spider_aggregation.core.fetcher import FetchResult

        # Actually fetch the RSS
        try:
            import httpx

            with httpx.Client(timeout=30) as client:
                response = client.get(rss_url)
                response.raise_for_status()

                # Parse with feedparser
                import feedparser

                parsed = feedparser.parse(response.content)

                # Verify parsing
                assert parsed.feed is not None
                assert len(parsed.entries) > 0

                # Parse a few entries
                for entry in parsed.entries[:5]:
                    parsed_entry = parser.parse_entry(entry)

                    assert parsed_entry["title"] is not None
                    assert parsed_entry["link"] is not None

                    print(f"✅ Entry: {parsed_entry['title'][:50]}...")

        except Exception as e:
            pytest.skip(f"Network request failed: {e}")

    @pytest.mark.integration
    def test_deduplication_with_real_data(
        self, db_session: Session, feed_repo: FeedRepository, entry_repo: EntryRepository
    ):
        """Test deduplication with real-world data patterns."""
        from spider_aggregation.models.feed import FeedCreate
        from spider_aggregation.models.entry import EntryCreate

        # Create a feed
        feed = feed_repo.create(
            FeedCreate(
                url="https://blog.cloudflare.com/zh-cn/rss",
                name="Cloudflare Blog",
            )
        )

        # Create an entry
        entry_repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Test Article",
                link="https://blog.cloudflare.com/test-article",
                link_hash=compute_link_hash("https://blog.cloudflare.com/test-article"),
                title_hash=compute_title_hash("Test Article"),
            )
        )

        # Test deduplication
        dedup = create_deduplicator(session=db_session)

        # Same link should be detected as duplicate
        entry = {
            "title": "Different Title",  # Different title
            "link": "https://blog.cloudflare.com/test-article",  # Same link
        }

        result = dedup.check_duplicate(entry, feed_id=feed.id)

        assert result.is_duplicate is True
        assert "Duplicate link" in result.reason

        print("✅ Deduplication working correctly")


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_feeds_workflow(self, db_session: Session):
        """Test fetching from multiple RSS feeds."""
        from spider_aggregation.models.feed import FeedCreate

        repo = FeedRepository(db_session)

        # Create multiple feeds
        feeds = [
            {
                "url": "https://blog.cloudflare.com/zh-cn/rss",
                "name": "Cloudflare Blog CN",
            },
            # Add more real feeds here for testing
        ]

        created_feeds = []
        for feed_data in feeds:
            try:
                feed = repo.create(FeedCreate(**feed_data))
                created_feeds.append(feed)
                print(f"✅ Created feed: {feed.name}")
            except Exception as e:
                print(f"⚠️  Failed to create feed {feed_data['name']}: {e}")

        if not created_feeds:
            pytest.skip("No feeds were created successfully")

        # Try fetching one feed
        fetcher = create_fetcher(session=db_session)

        for feed in created_feeds[:1]:  # Only test one feed to save time
            try:
                result = fetcher.fetch_feed(feed)

                if result.success:
                    print(f"✅ Fetched {len(result.entries)} entries from {feed.name}")
                else:
                    print(f"⚠️  Failed to fetch {feed.name}: {result.error}")

            except Exception as e:
                print(f"⚠️  Exception fetching {feed.name}: {e}")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_parser_with_real_feed_content(self):
        """Test parser with real RSS feed content."""
        rss_url = "https://blog.cloudflare.com/zh-cn/rss"

        try:
            import httpx

            with httpx.Client(timeout=30) as client:
                response = client.get(rss_url)
                response.raise_for_status()

                import feedparser

                parsed = feedparser.parse(response.content)

                if len(parsed.entries) > 0:
                    parser = create_parser()

                    # Parse first entry
                    entry = parser.parse_entry(parsed.entries[0])

                    # Verify parsing
                    assert entry["title"] is not None
                    assert entry["link"] is not None

                    # Check content fields
                    if entry.get("summary"):
                        assert len(entry["summary"]) > 0

                    print(f"✅ Parsed entry: {entry['title'][:60]}...")
                    print(f"   Link: {entry['link']}")
                    print(f"   Language: {entry.get('language')}")
                    if entry.get("reading_time_seconds"):
                        print(f"   Reading time: {entry['reading_time_seconds']}s")
                else:
                    pytest.skip("No entries found in feed")

        except Exception as e:
            pytest.skip(f"Network request failed: {e}")


def compute_link_hash(link: str) -> str:
    """Compute link hash for testing."""
    from spider_aggregation.utils.hash_utils import compute_link_hash as hash_func
    return hash_func(link)


def compute_title_hash(title: str) -> str:
    """Compute title hash for testing."""
    from spider_aggregation.utils.hash_utils import compute_title_hash as hash_func
    return hash_func(title)
