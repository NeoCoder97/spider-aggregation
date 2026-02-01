"""Unit tests for feed fetcher."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from spider_aggregation.core import FeedFetcher, FetchResult, FetchStats, create_fetcher
from spider_aggregation.models import FeedModel
from spider_aggregation.storage.repositories.feed_repo import FeedRepository


@pytest.fixture
def mock_feed():
    """Create a mock feed."""
    return FeedModel(
        id=1,
        url="https://example.com/feed.xml",
        name="Test Feed",
        description="Test Description",
        enabled=True,
        fetch_interval_minutes=60,
    )


@pytest.fixture
def db_session():
    """Create an in-memory database session."""
    from spider_aggregation.storage.database import DatabaseManager

    manager = DatabaseManager(":memory:")
    manager.init_db()

    with manager.session() as session:
        yield session

    manager.close()


class TestFetchResult:
    """Tests for FetchResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful result."""
        result = FetchResult(
            success=True,
            feed_id=1,
            feed_url="https://example.com/feed.xml",
            entries_count=5,
            entries=[{"title": "Test"}],
        )

        assert result.success is True
        assert result.error is None
        assert result.entries_count == 5

    def test_failed_result(self):
        """Test creating a failed result."""
        result = FetchResult(
            success=False,
            feed_id=1,
            feed_url="https://example.com/feed.xml",
            error="Network error",
        )

        assert result.success is False
        assert result.error == "Network error"
        assert result.entries_count == 0

    def test_result_validation(self):
        """Test result validation."""
        with pytest.raises(ValueError):
            FetchResult(
                success=True,
                feed_id=1,
                feed_url="https://example.com/feed.xml",
                error="Should not have error",
            )


class TestFetchStats:
    """Tests for FetchStats dataclass."""

    def test_add_success_result(self):
        """Test adding a successful result."""
        stats = FetchStats()
        result = FetchResult(
            success=True,
            feed_id=1,
            feed_url="https://example.com/feed.xml",
            entries_count=5,
            fetch_time_seconds=1.0,
        )

        stats.add_result(result)

        assert stats.total_feeds == 1
        assert stats.successful_fetches == 1
        assert stats.failed_fetches == 0
        assert stats.total_entries == 5
        assert stats.total_time_seconds == 1.0

    def test_add_failed_result(self):
        """Test adding a failed result."""
        stats = FetchStats()
        result = FetchResult(
            success=False,
            feed_id=1,
            feed_url="https://example.com/feed.xml",
            error="Timeout",
            fetch_time_seconds=1.0,
        )

        stats.add_result(result)

        assert stats.total_feeds == 1
        assert stats.successful_fetches == 0
        assert stats.failed_fetches == 1
        assert stats.errors_by_type == {"Timeout": 1}

    def test_success_rate(self):
        """Test success rate calculation."""
        stats = FetchStats()

        # No results
        assert stats.success_rate == 0.0

        # Add some results
        stats.add_result(
            FetchResult(
                success=True,
                feed_id=1,
                feed_url="https://example.com/feed1.xml",
                fetch_time_seconds=1.0,
            )
        )
        stats.add_result(
            FetchResult(
                success=False,
                feed_id=2,
                feed_url="https://example.com/feed2.xml",
                error="Error",
                fetch_time_seconds=1.0,
            )
        )

        assert stats.success_rate == 0.5

    def test_avg_time(self):
        """Test average time calculation."""
        stats = FetchStats()

        # No results
        assert stats.avg_time_seconds == 0.0

        # Add some results
        stats.add_result(
            FetchResult(
                success=True,
                feed_id=1,
                feed_url="https://example.com/feed.xml",
                fetch_time_seconds=2.0,
            )
        )
        stats.add_result(
            FetchResult(
                success=True,
                feed_id=2,
                feed_url="https://example.com/feed2.xml",
                fetch_time_seconds=4.0,
            )
        )

        assert stats.avg_time_seconds == 3.0


class TestFeedFetcher:
    """Tests for FeedFetcher."""

    def test_init(self):
        """Test fetcher initialization."""
        fetcher = FeedFetcher()

        assert fetcher.timeout_seconds > 0
        assert fetcher.max_retries >= 0
        assert fetcher.user_agent is not None
        assert fetcher.stats.total_feeds == 0

    def test_init_with_session(self, db_session: Session):
        """Test fetcher initialization with database session."""
        fetcher = FeedFetcher(session=db_session)

        assert fetcher.session is db_session

    def test_init_with_custom_params(self):
        """Test fetcher initialization with custom parameters."""
        fetcher = FeedFetcher(
            timeout_seconds=60,
            max_retries=5,
            user_agent="CustomAgent/1.0",
        )

        assert fetcher.timeout_seconds == 60
        assert fetcher.max_retries == 5
        assert fetcher.user_agent == "CustomAgent/1.0"

    @patch("spider_aggregation.core.fetcher.httpx.Client")
    def test_fetch_feed_success(self, mock_client_class, mock_feed):
        """Test successful feed fetch."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<rss><channel><item><title>Test Entry</title></item></channel></rss>'
        mock_response.headers = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        fetcher = FeedFetcher()
        result = fetcher.fetch_feed(mock_feed)

        assert result.success is True
        assert result.feed_id == mock_feed.id
        assert result.entries_count >= 0
        assert result.http_status == 200

    @patch("spider_aggregation.core.fetcher.httpx.Client")
    def test_fetch_feed_timeout(self, mock_client_class, mock_feed):
        """Test feed fetch with timeout."""
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        fetcher = FeedFetcher(max_retries=1)
        fetcher.retry_delay_seconds = 0  # Set to 0 for testing
        result = fetcher.fetch_feed(mock_feed)

        assert result.success is False
        assert "Timeout" in result.error

    @patch("spider_aggregation.core.fetcher.httpx.Client")
    def test_fetch_feed_not_modified(self, mock_client_class, mock_feed):
        """Test feed fetch with 304 Not Modified."""
        mock_response = MagicMock()
        mock_response.status_code = 304
        mock_response.headers = {"ETag": "abc123"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        fetcher = FeedFetcher()
        result = fetcher.fetch_feed(mock_feed)

        assert result.success is True
        assert result.entries_count == 0
        assert result.http_status == 304
        assert result.etag == "abc123"

    def test_fetch_multiple(self, mock_feed):
        """Test fetching multiple feeds."""
        fetcher = FeedFetcher()

        # Mock the fetch_feed method
        with patch.object(fetcher, "fetch_feed") as mock_fetch:
            mock_fetch.return_value = FetchResult(
                success=True,
                feed_id=1,
                feed_url=mock_feed.url,
                entries_count=5,
            )

            results = fetcher.fetch_multiple([mock_feed, mock_feed])

            assert len(results) == 2
            assert mock_fetch.call_count == 2

    def test_validate_url_valid(self):
        """Test URL validation with valid URLs."""
        fetcher = FeedFetcher()

        valid, error = fetcher.validate_url("https://example.com/feed.xml")
        assert valid is True
        assert error is None

        valid, error = fetcher.validate_url("http://example.com/rss")
        assert valid is True
        assert error is None

    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs."""
        fetcher = FeedFetcher()

        valid, error = fetcher.validate_url("not-a-url")
        assert valid is False
        assert "Invalid URL format" in error

        valid, error = fetcher.validate_url("ftp://example.com/feed.xml")
        assert valid is False
        assert "Unsupported scheme" in error

    def test_fetch_feeds_to_fetch_requires_session(self, mock_feed):
        """Test that fetch_feeds_to_fetch requires a session."""
        fetcher = FeedFetcher(session=None)

        with pytest.raises(ValueError, match="Database session required"):
            fetcher.fetch_feeds_to_fetch()


class TestCreateFetcher:
    """Tests for create_fetcher factory function."""

    def test_create_fetcher_without_session(self):
        """Test creating fetcher without session."""
        fetcher = create_fetcher()

        assert isinstance(fetcher, FeedFetcher)
        assert fetcher.session is None

    def test_create_fetcher_with_session(self, db_session: Session):
        """Test creating fetcher with session."""
        fetcher = create_fetcher(session=db_session)

        assert isinstance(fetcher, FeedFetcher)
        assert fetcher.session is db_session


class TestFeedFetcherIntegration:
    """Integration tests for feed fetcher with database."""

    def test_fetch_with_database_update(self, db_session: Session):
        """Test that fetch updates feed status in database."""
        # Create a feed in the database
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed_data = FeedCreate(
            url="https://example.com/feed.xml",
            name="Test Feed",
        )
        feed = repo.create(feed_data)

        # Mock successful fetch
        with patch("spider_aggregation.core.fetcher.httpx.Client") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'<rss><channel><item><title>Test</title></item></channel></rss>'
            mock_response.headers = {"ETag": "new-etag"}

            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client

            # Fetch with session
            fetcher = FeedFetcher(session=db_session)
            result = fetcher.fetch_feed(feed)

            # Verify feed was updated
            db_session.refresh(feed)
            assert feed.fetch_error_count == 0
            assert feed.last_fetched_at is not None

    def test_fetch_with_database_error_update(self, db_session: Session):
        """Test that fetch updates feed errors in database."""
        # Create a feed in the database
        repo = FeedRepository(db_session)
        from spider_aggregation.models.feed import FeedCreate

        feed_data = FeedCreate(
            url="https://example.com/feed.xml",
            name="Test Feed",
        )
        feed = repo.create(feed_data)

        # Mock failed fetch
        with patch("spider_aggregation.core.fetcher.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client

            # Fetch with session
            fetcher = FeedFetcher(session=db_session, max_retries=0)
            result = fetcher.fetch_feed(feed)

            # Verify feed error was updated
            db_session.refresh(feed)
            assert feed.fetch_error_count == 1
            assert feed.last_error is not None
            assert "Timeout" in feed.last_error
