"""Integration tests for database layer."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from spider_aggregation.models import FeedModel, EntryModel
from spider_aggregation.models.feed import FeedCreate, FeedUpdate
from spider_aggregation.models.entry import EntryCreate
from spider_aggregation.storage.repositories.feed_repo import FeedRepository
from spider_aggregation.storage.repositories.entry_repo import EntryRepository
from spider_aggregation.storage.database import DatabaseManager, init_db


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


class TestFeedRepository:
    """Tests for FeedRepository."""

    def test_create_feed(self, db_session: Session):
        """Test creating a new feed."""
        repo = FeedRepository(db_session)
        feed_data = FeedCreate(
            url="https://example.com/feed.xml",
            name="Test Feed",
            description="Test Description",
        )

        feed = repo.create(feed_data)

        assert feed.id is not None
        assert feed.url == "https://example.com/feed.xml"
        assert feed.name == "Test Feed"
        assert feed.description == "Test Description"
        assert feed.enabled is True
        assert feed.fetch_error_count == 0

    def test_get_by_id(self, db_session: Session):
        """Test getting a feed by ID."""
        repo = FeedRepository(db_session)
        feed_data = FeedCreate(url="https://example.com/feed.xml", name="Test Feed")

        created = repo.create(feed_data)
        found = repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.url == created.url

    def test_get_by_url(self, db_session: Session):
        """Test getting a feed by URL."""
        repo = FeedRepository(db_session)
        feed_data = FeedCreate(url="https://example.com/feed.xml", name="Test Feed")

        created = repo.create(feed_data)
        found = repo.get_by_url("https://example.com/feed.xml")

        assert found is not None
        assert found.id == created.id

    def test_list_feeds(self, db_session: Session):
        """Test listing feeds."""
        repo = FeedRepository(db_session)

        # Create multiple feeds
        for i in range(5):
            repo.create(
                FeedCreate(url=f"https://example.com/feed{i}.xml", name=f"Feed {i}")
            )

        # List all
        feeds = repo.list()
        assert len(feeds) == 5

        # List with limit
        feeds = repo.list(limit=3)
        assert len(feeds) == 3

        # List enabled only
        feeds = repo.list(enabled_only=True)
        assert len(feeds) == 5

    def test_count_feeds(self, db_session: Session):
        """Test counting feeds."""
        repo = FeedRepository(db_session)

        assert repo.count() == 0

        for i in range(3):
            repo.create(FeedCreate(url=f"https://example.com/feed{i}.xml"))

        assert repo.count() == 3

    def test_update_feed(self, db_session: Session):
        """Test updating a feed."""
        repo = FeedRepository(db_session)
        feed_data = FeedCreate(url="https://example.com/feed.xml", name="Test Feed")

        feed = repo.create(feed_data)
        updated = repo.update(feed, FeedUpdate(name="Updated Name"))

        assert updated.name == "Updated Name"
        assert updated.url == "https://example.com/feed.xml"

    def test_delete_feed(self, db_session: Session):
        """Test deleting a feed."""
        repo = FeedRepository(db_session)
        feed_data = FeedCreate(url="https://example.com/feed.xml", name="Test Feed")

        feed = repo.create(feed_data)
        feed_id = feed.id

        repo.delete(feed)

        assert repo.get_by_id(feed_id) is None

    def test_update_fetch_info(self, db_session: Session):
        """Test updating fetch information."""
        from datetime import datetime

        repo = FeedRepository(db_session)
        feed_data = FeedCreate(url="https://example.com/feed.xml", name="Test Feed")

        feed = repo.create(feed_data)
        now = datetime.utcnow()

        repo.update_fetch_info(feed, last_fetched_at=now)

        assert feed.last_fetched_at is not None

    def test_disable_and_enable_feed(self, db_session: Session):
        """Test disabling and enabling a feed."""
        repo = FeedRepository(db_session)
        feed_data = FeedCreate(url="https://example.com/feed.xml", name="Test Feed")

        feed = repo.create(feed_data)
        assert feed.enabled is True

        repo.disable_feed(feed, reason="Test disable")
        assert feed.enabled is False
        assert "Test disable" in feed.last_error

        repo.enable_feed(feed)
        assert feed.enabled is True
        assert feed.last_error is None
        assert feed.fetch_error_count == 0


class TestEntryRepository:
    """Tests for EntryRepository."""

    @pytest.fixture
    def feed(self, db_session: Session) -> FeedModel:
        """Create a test feed."""
        repo = FeedRepository(db_session)
        feed_data = FeedCreate(url="https://example.com/feed.xml", name="Test Feed")
        return repo.create(feed_data)

    def test_create_entry(self, db_session: Session, feed: FeedModel):
        """Test creating a new entry."""
        repo = EntryRepository(db_session)
        entry_data = EntryCreate(
            feed_id=feed.id,
            title="Test Entry",
            link="https://example.com/entry",
            title_hash="abc123",
            link_hash="def456",
        )

        entry = repo.create(entry_data)

        assert entry.id is not None
        assert entry.title == "Test Entry"
        assert entry.link == "https://example.com/entry"
        assert entry.feed_id == feed.id

    def test_get_by_id(self, db_session: Session, feed: FeedModel):
        """Test getting an entry by ID."""
        repo = EntryRepository(db_session)
        entry_data = EntryCreate(
            feed_id=feed.id,
            title="Test Entry",
            link="https://example.com/entry",
            title_hash="abc123",
            link_hash="def456",
        )

        created = repo.create(entry_data)
        found = repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id

    def test_get_by_link_hash(self, db_session: Session, feed: FeedModel):
        """Test getting an entry by link hash."""
        repo = EntryRepository(db_session)
        entry_data = EntryCreate(
            feed_id=feed.id,
            title="Test Entry",
            link="https://example.com/entry",
            title_hash="abc123",
            link_hash="def456",
        )

        repo.create(entry_data)
        found = repo.get_by_link_hash("def456")

        assert found is not None
        assert found.link == "https://example.com/entry"

    def test_list_entries(self, db_session: Session, feed: FeedModel):
        """Test listing entries."""
        repo = EntryRepository(db_session)

        # Create multiple entries
        for i in range(5):
            repo.create(
                EntryCreate(
                    feed_id=feed.id,
                    title=f"Entry {i}",
                    link=f"https://example.com/entry{i}",
                    title_hash=f"hash{i}",
                    link_hash=f"link_hash{i}",
                )
            )

        # List all
        entries = repo.list()
        assert len(entries) == 5

        # List by feed
        entries = repo.list(feed_id=feed.id)
        assert len(entries) == 5

        # List with limit
        entries = repo.list(limit=3)
        assert len(entries) == 3

    def test_count_entries(self, db_session: Session, feed: FeedModel):
        """Test counting entries."""
        repo = EntryRepository(db_session)

        assert repo.count() == 0

        for i in range(3):
            repo.create(
                EntryCreate(
                    feed_id=feed.id,
                    title=f"Entry {i}",
                    link=f"https://example.com/entry{i}",
                    title_hash=f"hash{i}",
                    link_hash=f"link_hash{i}",
                )
            )

        assert repo.count() == 3
        assert repo.count(feed_id=feed.id) == 3

    def test_update_entry(self, db_session: Session, feed: FeedModel):
        """Test updating an entry."""
        from spider_aggregation.models.entry import EntryUpdate

        repo = EntryRepository(db_session)
        entry_data = EntryCreate(
            feed_id=feed.id,
            title="Test Entry",
            link="https://example.com/entry",
            title_hash="abc123",
            link_hash="def456",
        )

        entry = repo.create(entry_data)
        updated = repo.update(entry, EntryUpdate(title="Updated Title"))

        assert updated.title == "Updated Title"

    def test_delete_entry(self, db_session: Session, feed: FeedModel):
        """Test deleting an entry."""
        repo = EntryRepository(db_session)
        entry_data = EntryCreate(
            feed_id=feed.id,
            title="Test Entry",
            link="https://example.com/entry",
            title_hash="abc123",
            link_hash="def456",
        )

        entry = repo.create(entry_data)
        entry_id = entry.id

        repo.delete(entry)

        assert repo.get_by_id(entry_id) is None

    def test_delete_by_feed(self, db_session: Session, feed: FeedModel):
        """Test deleting all entries for a feed."""
        entry_repo = EntryRepository(db_session)

        # Create entries
        for i in range(3):
            entry_repo.create(
                EntryCreate(
                    feed_id=feed.id,
                    title=f"Entry {i}",
                    link=f"https://example.com/entry{i}",
                    title_hash=f"hash{i}",
                    link_hash=f"link_hash{i}",
                )
            )

        # Delete all entries for feed
        count = entry_repo.delete_by_feed(feed.id)

        assert count == 3
        assert entry_repo.count(feed_id=feed.id) == 0

    def test_search_entries(self, db_session: Session, feed: FeedModel):
        """Test searching entries."""
        repo = EntryRepository(db_session)

        repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Python Programming",
                link="https://example.com/1",
                title_hash="hash1",
                link_hash="link1",
                content="Learn Python programming",
            )
        )

        repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="JavaScript Guide",
                link="https://example.com/2",
                title_hash="hash2",
                link_hash="link2",
                content="Learn JavaScript",
            )
        )

        # Search for "Python"
        results = repo.search("Python")
        assert len(results) == 1
        assert "Python" in results[0].title

    def test_get_stats(self, db_session: Session, feed: FeedModel):
        """Test getting entry statistics."""
        repo = EntryRepository(db_session)

        repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="Entry 1",
                link="https://example.com/1",
                title_hash="hash1",
                link_hash="link1",
                language="en",
            )
        )

        repo.create(
            EntryCreate(
                feed_id=feed.id,
                title="条目 2",
                link="https://example.com/2",
                title_hash="hash2",
                link_hash="link2",
                language="zh",
            )
        )

        stats = repo.get_stats()

        assert stats["total"] == 2
        assert stats["language_counts"]["en"] == 1
        assert stats["language_counts"]["zh"] == 1


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    def test_init_db(self, db_manager: DatabaseManager):
        """Test database initialization."""
        # Tables should be created
        with db_manager.session() as session:
            # Query should not raise error
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            table_names = [row[0] for row in result]

            assert "feeds" in table_names
            assert "entries" in table_names

    def test_session_context_manager(self, db_manager: DatabaseManager):
        """Test session as context manager."""
        with db_manager.session() as session:
            feed = FeedModel(
                url="https://example.com/feed.xml",
                name="Test Feed",
            )
            session.add(feed)
            session.flush()

        # Session should be closed and committed
        with db_manager.session() as session:
            feeds = session.query(FeedModel).all()
            assert len(feeds) == 1

    def test_drop_all(self):
        """Test dropping all tables."""
        manager = DatabaseManager(":memory:")
        manager.init_db()

        # Create some data
        with manager.session() as session:
            feed = FeedModel(url="https://example.com/feed.xml", name="Test Feed")
            session.add(feed)

        # Drop and recreate
        manager.init_db(drop_all=True)

        # Tables should be empty
        with manager.session() as session:
            feeds = session.query(FeedModel).all()
            assert len(feeds) == 0

        manager.close()
