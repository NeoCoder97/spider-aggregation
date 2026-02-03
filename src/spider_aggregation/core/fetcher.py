"""
RSS/Atom feed fetcher with error handling and retry logic.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import feedparser
import httpx
from sqlalchemy.orm import Session

from spider_aggregation.config import get_config
from spider_aggregation.logger import get_logger
from spider_aggregation.models import FeedModel
from spider_aggregation.storage.repositories.feed_repo import FeedRepository

logger = get_logger(__name__)


@dataclass
class FetchResult:
    """Result of a feed fetch operation."""

    success: bool
    feed_id: int
    feed_url: str
    entries_count: int = 0
    entries: list = field(default_factory=list)
    error: Optional[str] = None
    fetch_time_seconds: float = 0.0
    http_status: Optional[int] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None

    # Raw feedparser data
    feed_data: Optional[dict] = None
    feed_info: Optional[dict] = None

    def __post_init__(self):
        """Validate fetch result."""
        if self.success and self.error:
            raise ValueError("Successful fetch cannot have an error")
        if not self.success and not self.error:
            self.error = "Unknown error"


@dataclass
class FetchStats:
    """Statistics for feed fetching operations."""

    total_feeds: int = 0
    successful_fetches: int = 0
    failed_fetches: int = 0
    total_entries: int = 0
    total_time_seconds: float = 0.0
    errors_by_type: dict = field(default_factory=dict)

    def add_result(self, result: FetchResult) -> None:
        """Add a fetch result to statistics.

        Args:
            result: FetchResult to add
        """
        self.total_feeds += 1
        self.total_time_seconds += result.fetch_time_seconds

        if result.success:
            self.successful_fetches += 1
            self.total_entries += result.entries_count
        else:
            self.failed_fetches += 1
            error_type = result.error.split(":")[0] if result.error else "unknown"
            self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_feeds == 0:
            return 0.0
        return self.successful_fetches / self.total_feeds

    @property
    def avg_time_seconds(self) -> float:
        """Calculate average fetch time."""
        if self.total_feeds == 0:
            return 0.0
        return self.total_time_seconds / self.total_feeds


class FeedFetcher:
    """RSS/Atom feed fetcher with retry logic and error handling."""

    def __init__(
        self,
        session: Optional[Session] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        user_agent: Optional[str] = None,
    ):
        """Initialize feed fetcher.

        Args:
            session: Optional database session for updating feed status
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            user_agent: User-Agent header for HTTP requests
        """
        config = get_config()

        self.session = session
        self.timeout_seconds = timeout_seconds or config.fetcher.timeout_seconds
        self.max_retries = max_retries or config.fetcher.max_retries
        self.user_agent = user_agent or config.fetcher.user_agent
        self.retry_delay_seconds = config.fetcher.retry_delay_seconds

        # HTTP client configuration
        self.follow_redirects = config.fetcher.follow_redirects
        self.max_redirects = config.fetcher.max_redirects

        self.stats = FetchStats()

    def fetch_url(
        self,
        url: str,
        feed_id: Optional[int] = None,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        max_entries: Optional[int] = None,
    ) -> FetchResult:
        """Fetch a feed directly from URL without FeedModel.

        Args:
            url: Feed URL to fetch
            feed_id: Optional feed ID for the result
            etag: Optional ETag for conditional request
            last_modified: Optional Last-Modified for conditional request
            max_entries: Maximum entries to return (None for unlimited)

        Returns:
            FetchResult with entries or error
        """
        start_time = time.time()
        feed_id = feed_id or 0

        logger.debug(f"Fetching URL: {url}")

        last_error = None
        http_status = None
        response_etag = None
        response_last_modified = None
        entries = []

        for attempt in range(self.max_retries + 1):
            try:
                # Fetch with HTTP client
                http_result = self._fetch_http(
                    url,
                    etag=etag if not attempt else None,
                    last_modified=last_modified if not attempt else None,
                )

                http_status = http_result.status_code
                response_etag = http_result.headers.get("ETag")
                response_last_modified = http_result.headers.get("Last-Modified")

                # Check for Not Modified
                if http_status == 304:
                    logger.debug(f"Feed not modified: {url}")
                    return FetchResult(
                        success=True,
                        feed_id=feed_id,
                        feed_url=url,
                        entries_count=0,
                        fetch_time_seconds=time.time() - start_time,
                        http_status=http_status,
                        etag=response_etag,
                        last_modified=response_last_modified,
                    )

                # Parse with feedparser
                parsed = feedparser.parse(http_result.content)
                entries = parsed.get("entries", [])

                # Apply max entries limit
                if max_entries and max_entries > 0 and len(entries) > max_entries:
                    original_count = len(entries)
                    entries = entries[:max_entries]
                    logger.info(f"Limited {url} to {len(entries)} entries (original: {original_count})")

                # Get feed info
                feed_info = {
                    "title": parsed.feed.get("title"),
                    "link": parsed.feed.get("link"),
                    "description": parsed.feed.get("description"),
                }

                fetch_time = time.time() - start_time

                logger.info(f"Fetched {len(entries)} entries from {url} in {fetch_time:.2f}s")

                result = FetchResult(
                    success=True,
                    feed_id=feed_id,
                    feed_url=url,
                    entries_count=len(entries),
                    entries=entries,
                    fetch_time_seconds=fetch_time,
                    http_status=http_status,
                    etag=response_etag,
                    last_modified=response_last_modified,
                    feed_data=parsed,
                    feed_info=feed_info,
                )

                self.stats.add_result(result)
                return result

            except httpx.TimeoutException as e:
                last_error = f"Timeout: {str(e)}"
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries + 1})")

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {str(e)}"
                http_status = e.response.status_code

                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    logger.error(f"Client error fetching {url}: {last_error}")
                    break

                logger.warning(f"HTTP error fetching {url} (attempt {attempt + 1})")

            except httpx.RequestError as e:
                last_error = f"Request error: {str(e)}"
                logger.warning(f"Network error fetching {url} (attempt {attempt + 1})")

            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}: {str(e)}"
                logger.error(f"Error fetching {url}: {last_error}")
                break

            # Retry delay
            if attempt < self.max_retries:
                time.sleep(self.retry_delay_seconds * (attempt + 1))

        # All retries failed
        fetch_time = time.time() - start_time
        result = FetchResult(
            success=False,
            feed_id=feed_id,
            feed_url=url,
            fetch_time_seconds=fetch_time,
            error=last_error or "Unknown error",
            http_status=http_status,
        )

        self.stats.add_result(result)
        return result

    def fetch_feed(self, feed: FeedModel) -> FetchResult:
        """Fetch a single feed.

        Args:
            feed: FeedModel instance to fetch

        Returns:
            FetchResult with entries or error
        """
        start_time = time.time()
        feed_id = feed.id
        feed_url = feed.url

        logger.debug(f"Fetching feed: {feed.name or feed_url} (ID: {feed_id})")

        last_error = None
        http_status = None
        etag = None
        last_modified = None
        entries = []

        for attempt in range(self.max_retries + 1):
            try:
                # Fetch with HTTP client first to get headers
                http_result = self._fetch_http(
                    feed_url,
                    etag=feed.etag if not attempt else None,
                    last_modified=feed.last_modified if not attempt else None,
                )

                http_status = http_result.status_code
                etag = http_result.headers.get("ETag")
                last_modified = http_result.headers.get("Last-Modified")

                # Check for Not Modified
                if http_status == 304:
                    logger.debug(f"Feed not modified: {feed_url}")
                    return FetchResult(
                        success=True,
                        feed_id=feed_id,
                        feed_url=feed_url,
                        entries_count=0,
                        fetch_time_seconds=time.time() - start_time,
                        http_status=http_status,
                        etag=etag,
                        last_modified=last_modified,
                    )

                # Parse with feedparser
                parsed = feedparser.parse(http_result.content)
                entries = parsed.get("entries", [])

                # Apply max entries limit from feed settings
                # Handle None case and treat 0 as no limit
                max_entries = None
                if feed.max_entries_per_fetch is not None and feed.max_entries_per_fetch > 0:
                    max_entries = feed.max_entries_per_fetch

                if max_entries and len(entries) > max_entries:
                    original_count = len(entries)
                    entries = entries[:max_entries]
                    logger.info(f"Limited feed {feed_url} to {len(entries)} entries (original: {original_count})")

                # Apply date filter if feed.fetch_only_recent is enabled
                if feed.fetch_only_recent:
                    config = get_config()
                    recent_days = config.fetcher.fetch_recent_days
                    if recent_days > 0:
                        from datetime import datetime, timedelta
                        cutoff_date = datetime.utcnow() - timedelta(days=recent_days)
                        original_count = len(entries)

                        # Filter entries that have published/updated dates within the recent period
                        filtered_entries = []
                        for e in entries:
                            # Try to get a date from the entry
                            entry_date = None
                            if e.get('published_parsed'):
                                entry_date = datetime(*e['published_parsed'][:6])
                            elif e.get('updated_parsed'):
                                entry_date = datetime(*e['updated_parsed'][:6])

                            # Keep entry if it has a valid date within the recent period, or if no date is available
                            if entry_date is None or entry_date >= cutoff_date:
                                filtered_entries.append(e)

                        entries = filtered_entries
                        if len(entries) < original_count:
                            logger.info(f"Filtered {original_count - len(entries)} old entries from {feed_url} (older than {recent_days} days)")

                # Get feed info
                feed_info = {
                    "title": parsed.feed.get("title"),
                    "link": parsed.feed.get("link"),
                    "description": parsed.feed.get("description"),
                }

                fetch_time = time.time() - start_time

                logger.info(
                    f"Fetched {len(entries)} entries from {feed.name or feed_url} "
                    f"in {fetch_time:.2f}s"
                )

                result = FetchResult(
                    success=True,
                    feed_id=feed_id,
                    feed_url=feed_url,
                    entries_count=len(entries),
                    entries=entries,
                    fetch_time_seconds=fetch_time,
                    http_status=http_status,
                    etag=etag,
                    last_modified=last_modified,
                    feed_data=parsed,
                    feed_info=feed_info,
                )

                self.stats.add_result(result)

                # Update feed in database if session provided
                if self.session:
                    self._update_feed_after_success(feed, result, etag, last_modified)

                return result

            except httpx.TimeoutException as e:
                last_error = f"Timeout: {str(e)}"
                logger.warning(f"Timeout fetching {feed_url} (attempt {attempt + 1}/{self.max_retries + 1})")

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {str(e)}"
                http_status = e.response.status_code

                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    logger.error(f"Client error fetching {feed_url}: {last_error}")
                    break

                logger.warning(f"HTTP error fetching {feed_url} (attempt {attempt + 1})")

            except httpx.RequestError as e:
                last_error = f"Request error: {str(e)}"
                logger.warning(f"Network error fetching {feed_url} (attempt {attempt + 1})")

            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}: {str(e)}"
                logger.error(f"Error fetching {feed_url}: {last_error}")
                break

            # Retry delay
            if attempt < self.max_retries:
                time.sleep(self.retry_delay_seconds * (attempt + 1))

        # All retries failed
        fetch_time = time.time() - start_time
        result = FetchResult(
            success=False,
            feed_id=feed_id,
            feed_url=feed_url,
            fetch_time_seconds=fetch_time,
            error=last_error or "Unknown error",
            http_status=http_status,
        )

        self.stats.add_result(result)

        # Update feed error status in database if session provided
        if self.session:
            self._update_feed_after_error(feed, result)

        return result

    def _fetch_http(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> httpx.Response:
        """Fetch URL with HTTP client.

        Args:
            url: URL to fetch
            etag: Optional ETag for conditional request
            last_modified: Optional Last-Modified for conditional request

        Returns:
            httpx Response

        Raises:
            httpx.TimeoutException: On timeout
            httpx.HTTPStatusError: On HTTP error
            httpx.RequestError: On network error
        """
        headers = {"User-Agent": self.user_agent}

        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=self.follow_redirects,
            max_redirects=self.max_redirects,
        ) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response

    def _update_feed_after_success(
        self,
        feed: FeedModel,
        result: FetchResult,
        etag: Optional[str],
        last_modified: Optional[str],
    ) -> None:
        """Update feed after successful fetch.

        Args:
            feed: FeedModel instance
            result: FetchResult from successful fetch
            etag: ETag from response
            last_modified: Last-Modified from response
        """
        if not self.session:
            return

        repo = FeedRepository(self.session)

        repo.update_fetch_info(
            feed,
            last_fetched_at=datetime.utcnow(),
            reset_errors=True,
            etag=etag,
            last_modified=last_modified,
        )

        # Update feed metadata from response
        if result.feed_info:
            if result.feed_info.get("title") and not feed.name:
                feed.name = result.feed_info["title"]
            if result.feed_info.get("description") and not feed.description:
                feed.description = result.feed_info["description"]

    def _update_feed_after_error(self, feed: FeedModel, result: FetchResult) -> None:
        """Update feed after failed fetch.

        Args:
            feed: FeedModel instance
            result: FetchResult from failed fetch
        """
        if not self.session:
            return

        repo = FeedRepository(self.session)

        repo.update_fetch_info(
            feed,
            last_fetched_at=datetime.utcnow(),
            increment_error=True,
            last_error=result.error,
        )

        # Check if feed should be disabled
        config = get_config()
        if feed.fetch_error_count >= config.feed.max_consecutive_errors:
            logger.warning(f"Disabling feed due to errors: {feed.url}")
            repo.disable_feed(feed, reason=f"Too many errors: {result.error}")

    def fetch_multiple(self, feeds: list[FeedModel]) -> list[FetchResult]:
        """Fetch multiple feeds.

        Args:
            feeds: List of FeedModel instances to fetch

        Returns:
            List of FetchResult instances
        """
        results = []

        for feed in feeds:
            try:
                result = self.fetch_feed(feed)
                results.append(result)
            except Exception as e:
                logger.exception(f"Unexpected error fetching {feed.url}: {e}")
                results.append(
                    FetchResult(
                        success=False,
                        feed_id=feed.id,
                        feed_url=feed.url,
                        error=f"Unexpected error: {type(e).__name__}: {str(e)}",
                        fetch_time_seconds=0.0,
                    )
                )

        return results

    def fetch_feeds_to_fetch(self, limit: int = 50) -> list[FetchResult]:
        """Fetch feeds that are due for fetching.

        Args:
            limit: Maximum number of feeds to fetch

        Returns:
            List of FetchResult instances
        """
        if not self.session:
            raise ValueError("Database session required for fetch_feeds_to_fetch")

        repo = FeedRepository(self.session)
        feeds = repo.get_feeds_to_fetch(max_feeds=limit)

        logger.info(f"Fetching {len(feeds)} feeds")

        return self.fetch_multiple(feeds)

    def validate_url(self, url: str) -> tuple[bool, Optional[str]]:
        """Validate a feed URL.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            result = urlparse(url)
            if not result.scheme or not result.netloc:
                return False, "Invalid URL format"

            if result.scheme not in ("http", "https", "file"):
                return False, f"Unsupported scheme: {result.scheme}"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"


def create_fetcher(session: Optional[Session] = None) -> FeedFetcher:
    """Create a configured FeedFetcher instance.

    Args:
        session: Optional database session

    Returns:
        Configured FeedFetcher instance
    """
    return FeedFetcher(session=session)
