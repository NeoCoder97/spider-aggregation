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
    ) -> "FetchResult":
        """Fetch a feed from the given URL.

        Args:
            url: Feed URL to fetch
            feed_id: Optional database feed ID for status updates
            etag: Optional ETag for conditional request
            last_modified: Optional Last-Modified header for conditional request
            max_entries: Maximum entries to fetch (0=unlimited)

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

        # Otherwise, fetch directly using URL
        return self._fetcher.fetch_url(
            url=url,
            feed_id=feed_id,
            etag=etag,
            last_modified=last_modified,
            max_entries=max_entries if max_entries > 0 else None,
        )

    def fetch_feeds_to_fetch(self, session: Session) -> list:
        """Get list of feeds that need to be fetched.

        Args:
            session: Database session

        Returns:
            List of feed dictionaries
        """
        return self._fetcher.fetch_feeds_to_fetch(limit=50)

    @property
    def stats(self) -> "FetchStats":
        """Get fetch statistics.

        Returns:
            FetchStats with fetch operation statistics
        """
        return self._fetcher.stats


def create_fetcher_service(session: Optional[Session] = None) -> FetcherService:
    """Create a FetcherService instance.

    Args:
        session: Optional database session

    Returns:
        Configured FetcherService
    """
    return FetcherService(session=session)
