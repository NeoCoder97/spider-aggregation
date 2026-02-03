"""
Facade for HTTP feed fetching operations.

Provides unified interface for fetching RSS/Atom feeds from external sources.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from spider_aggregation.logger import get_logger

if TYPE_CHECKING:
    from spider_aggregation.core.fetcher import FetchResult, FetchStats


class FetcherService:
    """Facade for HTTP feed fetching operations.

    Provides unified interface for fetching RSS/Atom feeds from external sources.
    """

    def __init__(self, session: Optional[Session] = None):
        """Initialize fetcher service.

        Args:
            session: Optional database session for updating feed status
        """
        from spider_aggregation.core.factories import create_fetcher

        self._fetcher = create_fetcher(session=session)
        self._logger = get_logger(__name__)

    def fetch_feed(
        self,
        url: str,
        feed_id: Optional[int] = None,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        max_entries: int = 0,
        recent_only: bool = False,
    ) -> "FetchResult":
        """Fetch a feed from the given URL.

        Args:
            url: Feed URL to fetch
            feed_id: Optional database feed ID for status updates
            etag: Optional ETag for conditional request
            last_modified: Optional Last-Modified header for conditional request
            max_entries: Maximum entries to fetch (0=unlimited)
            recent_only: Only fetch recent entries

        Returns:
            FetchResult with entries and metadata
        """
        # If feed_id is provided, get the FeedModel from database
        if feed_id is not None and self._fetcher.session is not None:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(self._fetcher.session)
            feed = feed_repo.get_by_id(feed_id)
            if feed:
                return self._fetcher.fetch_feed(feed)

        # Otherwise, fetch directly using HTTP client
        from spider_aggregation.core.fetcher import FetchResult
        import feedparser
        import time

        http_client = self._fetcher._http_client
        start_time = time.time()

        response = http_client.get(url, timeout=self._fetcher.timeout_seconds)

        self._fetcher.stats.requests_made += 1

        # Handle conditional requests
        if response.status_code == 304:
            return FetchResult(
                success=True,
                feed_id=feed_id or 0,
                feed_url=url,
                entries_count=0,
                fetch_time_seconds=time.time() - start_time,
                http_status=304,
                etag=etag,
                last_modified=last_modified,
            )

        if response.status_code != 200:
            return FetchResult(
                success=False,
                feed_id=feed_id or 0,
                feed_url=url,
                fetch_time_seconds=time.time() - start_time,
                http_status=response.status_code,
                error=f"HTTP {response.status_code}",
            )

        # Parse feed
        parsed = feedparser.parse(response.text)
        entries = parsed.get("entries", [])

        # Apply max entries limit
        if max_entries > 0 and len(entries) > max_entries:
            entries = entries[:max_entries]

        # Get feed info
        feed_info = {
            "title": parsed.feed.get("title"),
            "link": parsed.feed.get("link"),
            "description": parsed.feed.get("description"),
        }

        return FetchResult(
            success=True,
            feed_id=feed_id or 0,
            feed_url=url,
            entries=entries,
            entries_count=len(entries),
            fetch_time_seconds=time.time() - start_time,
            http_status=response.status_code,
            feed_info=feed_info,
        )

    def fetch_feeds_to_fetch(self, session: Session) -> list:
        """Get list of feeds that need to be fetched.

        Args:
            session: Database session

        Returns:
            List of feed dictionaries
        """
        return self._fetcher.fetch_feeds_to_fetch(session)

    def update_feed_success(self, feed, etag: str, last_modified: str) -> None:
        """Update feed after successful fetch.

        Args:
            feed: Feed model instance
            etag: ETag from response
            last_modified: Last-Modified from response
        """
        from spider_aggregation.storage.repositories.feed_repo import FeedRepository

        repo = FeedRepository(self._fetcher.session)
        repo.update_fetch_info(
            feed,
            etag=etag,
            last_modified=last_modified,
            reset_errors=True,
        )

    def update_feed_error(self, feed, error: str) -> None:
        """Update feed after failed fetch.

        Args:
            feed: Feed model instance
            error: Error message
        """
        from spider_aggregation.storage.repositories.feed_repo import FeedRepository

        repo = FeedRepository(self._fetcher.session)
        repo.update_fetch_info(feed, increment_error=True, last_error=error)


def create_fetcher_service(session: Optional[Session] = None) -> FetcherService:
    """Create a FetcherService instance.

    Args:
        session: Optional database session

    Returns:
        Configured FetcherService
    """
    return FetcherService(session=session)
