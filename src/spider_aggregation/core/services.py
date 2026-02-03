"""
Facade services for core modules.

This module provides unified entry points (Facade pattern) for all core business logic modules.
External code (web layer, etc.) should ONLY interact with these services, not direct module classes.

Architecture Rules:
    - Web layer MUST use these services, never import from fetcher/parser/deduplicator directly
    - Each service encapsulates one functional domain
    - Services use factory functions for component creation
    - Services provide simple, high-level interfaces

Services:
    - FetcherService: HTTP feed fetching
    - ParserService: Content parsing
    - DeduplicatorService: Duplicate detection
    - FilterService: Content filtering
    - SchedulerService: Task scheduling
    - ContentService: Full content fetching
    - KeywordService: Keyword extraction
    - SummarizerService: Content summarization

Example:
    # ✅ Correct - Use service facade
    from spider_aggregation.core.services import FetcherService, ParserService

    fetcher = FetcherService()
    result = fetcher.fetch_feed(url)

    parser = ParserService()
    parsed = parser.parse_entry(entry_data)

    # ❌ Wrong - Direct import (forbidden)
    from spider_aggregation.core.fetcher import FeedFetcher  # VIOLATION
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from spider_aggregation.logger import get_logger

if TYPE_CHECKING:
    from spider_aggregation.core.fetcher import FetchResult, FetchStats
    from spider_aggregation.core.parser import FeedMetadata


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


class ParserService:
    """Facade for content parsing operations.

    Provides unified interface for parsing feed entries and metadata.
    """

    def __init__(
        self,
        max_content_length: Optional[int] = None,
        strip_html: bool = True,
        preserve_paragraphs: bool = True,
    ):
        """Initialize parser service.

        Args:
            max_content_length: Maximum content length in characters
            strip_html: Whether to strip HTML tags
            preserve_paragraphs: Whether to preserve paragraphs
        """
        from spider_aggregation.core.factories import create_parser

        self._parser = create_parser(
            max_content_length=max_content_length,
            strip_html=strip_html,
            preserve_paragraphs=preserve_paragraphs,
        )
        self._logger = get_logger(__name__)

    def parse_entry(self, entry_data: dict, feed_id: int) -> dict:
        """Parse a single feed entry.

        Args:
            entry_data: Raw entry data from feedparser
            feed_id: Associated feed ID

        Returns:
            Parsed entry dict with normalized data
        """
        parsed = self._parser.parse_entry(entry_data)
        # Add feed_id to the parsed result
        parsed["feed_id"] = feed_id
        return parsed

    def parse_feed_metadata(self, feed_data: dict, url: str) -> "FeedMetadata":
        """Parse feed metadata from feedparser result.

        Args:
            feed_data: Raw feed data from feedparser
            url: Feed URL

        Returns:
            FeedMetadata with title, description, etc.
        """
        return self._parser.parse_feed_metadata(feed_data, url)


class DeduplicatorService:
    """Facade for duplicate detection operations.

    Provides unified interface for checking duplicate entries.
    """

    def __init__(self, session: Optional[Session] = None, strategy: str = "medium"):
        """Initialize deduplicator service.

        Args:
            session: Database session for duplicate checking
            strategy: Deduplication strategy (strict/medium/relaxed)
        """
        from spider_aggregation.core.factories import create_deduplicator

        self._deduplicator = create_deduplicator(session=session, strategy=strategy)
        self._logger = get_logger(__name__)

    def check_duplicate(self, parsed_entry: dict, entry_repo, feed_id: int) -> "DedupResult":
        """Check if an entry is a duplicate.

        Args:
            parsed_entry: Parsed entry data
            entry_repo: EntryRepository instance
            feed_id: Feed ID

        Returns:
            DedupResult indicating if duplicate and reason
        """
        return self._deduplicator.check_duplicate(parsed_entry, entry_repo, feed_id)


class FilterService:
    """Facade for content filtering operations.

    Provides unified interface for filtering entries based on rules.
    """

    def __init__(self, rules: Optional[list] = None):
        """Initialize filter service.

        Args:
            rules: Optional list of FilterRuleModel instances
        """
        from spider_aggregation.core.factories import create_filter_engine

        self._engine = create_filter_engine(rules=rules)
        self._logger = get_logger(__name__)

    def apply(self, parsed_entry: dict, filter_rule_repo) -> "FilterResult":
        """Apply filter rules to an entry.

        Args:
            parsed_entry: Parsed entry data
            filter_rule_repo: FilterRuleRepository instance

        Returns:
            FilterResult indicating if entry is allowed
        """
        return self._engine.apply(parsed_entry, filter_rule_repo)

    def reload_rules(self, rules: list) -> None:
        """Reload filter rules.

        Args:
            rules: New list of FilterRuleModel instances
        """
        self._engine.reload_rules(rules)


class SchedulerService:
    """Facade for task scheduling operations.

    Provides unified interface for managing feed fetching schedules.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        max_workers: Optional[int] = None,
        db_manager=None,
    ):
        """Initialize scheduler service.

        Args:
            session: Optional database session
            max_workers: Maximum worker threads
            db_manager: Optional DatabaseManager instance
        """
        from spider_aggregation.core.factories import create_scheduler

        self._scheduler = create_scheduler(
            session=session,
            max_workers=max_workers,
            db_manager=db_manager,
        )
        self._logger = get_logger(__name__)

    def start(self) -> None:
        """Start the scheduler."""
        self._scheduler.start()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler.

        Args:
            wait: Wait for running jobs to complete
        """
        self._scheduler.shutdown(wait=wait)

    def add_feed_job(self, feed_id: int, interval_minutes: int) -> None:
        """Add a scheduled job for a feed.

        Args:
            feed_id: Feed ID
            interval_minutes: Fetch interval in minutes
        """
        self._scheduler.add_feed_job(feed_id, interval_minutes)

    def remove_feed_job(self, feed_id: int) -> None:
        """Remove a scheduled job for a feed.

        Args:
            feed_id: Feed ID
        """
        self._scheduler.remove_feed_job(feed_id)

    def get_stats(self) -> dict:
        """Get scheduler statistics.

        Returns:
            Dictionary with scheduler stats
        """
        return self._scheduler.get_stats()


class ContentService:
    """Facade for full content fetching operations.

    Provides unified interface for fetching full article content.
    """

    def __init__(self, timeout_seconds: Optional[int] = None):
        """Initialize content service.

        Args:
            timeout_seconds: Request timeout in seconds
        """
        from spider_aggregation.core.factories import create_content_fetcher

        self._fetcher = create_content_fetcher(timeout_seconds=timeout_seconds)
        self._logger = get_logger(__name__)

    def fetch_content(self, url: str) -> "ContentFetchResult":
        """Fetch full content from a URL.

        Args:
            url: Article URL

        Returns:
            ContentFetchResult with full content
        """
        return self._fetcher.fetch_content(url)


class KeywordService:
    """Facade for keyword extraction operations.

    Provides unified interface for extracting keywords from content.
    """

    def __init__(self, max_keywords: Optional[int] = None, language: str = "auto"):
        """Initialize keyword service.

        Args:
            max_keywords: Maximum number of keywords to extract
            language: Language code (auto/en/zh)
        """
        from spider_aggregation.core.factories import create_keyword_extractor

        self._extractor = create_keyword_extractor(
            max_keywords=max_keywords,
            language=language,
        )
        self._logger = get_logger(__name__)

    def extract(self, text: str) -> list[str]:
        """Extract keywords from text.

        Args:
            text: Input text

        Returns:
            List of keyword strings
        """
        return self._extractor.extract(text)


class SummarizerService:
    """Facade for content summarization operations.

    Provides unified interface for generating content summaries.
    """

    def __init__(
        self,
        max_summary_length: Optional[int] = None,
        extractive_sentences: Optional[int] = None,
    ):
        """Initialize summarizer service.

        Args:
            max_summary_length: Maximum summary length in characters
            extractive_sentences: Number of sentences for extractive summary
        """
        from spider_aggregation.core.factories import create_summarizer

        self._summarizer = create_summarizer(
            max_summary_length=max_summary_length,
            extractive_sentences=extractive_sentences,
        )
        self._logger = get_logger(__name__)

    def summarize(self, content: str) -> str:
        """Generate a summary of content.

        Args:
            content: Input content

        Returns:
            Summary string
        """
        return self._summarizer.summarize(content)


# Convenience functions for quick service creation
def create_fetcher_service(session: Optional[Session] = None) -> FetcherService:
    """Create a FetcherService instance.

    Args:
        session: Optional database session

    Returns:
        Configured FetcherService
    """
    return FetcherService(session=session)


def create_parser_service(
    max_content_length: Optional[int] = None,
) -> ParserService:
    """Create a ParserService instance.

    Args:
        max_content_length: Maximum content length

    Returns:
        Configured ParserService
    """
    return ParserService(max_content_length=max_content_length)


def create_deduplicator_service(
    session: Optional[Session] = None,
    strategy: str = "medium",
) -> DeduplicatorService:
    """Create a DeduplicatorService instance.

    Args:
        session: Optional database session
        strategy: Deduplication strategy

    Returns:
        Configured DeduplicatorService
    """
    return DeduplicatorService(session=session, strategy=strategy)


def create_filter_service(rules: Optional[list] = None) -> FilterService:
    """Create a FilterService instance.

    Args:
        rules: Optional list of filter rules

    Returns:
        Configured FilterService
    """
    return FilterService(rules=rules)


def create_scheduler_service(
    session: Optional[Session] = None,
    max_workers: Optional[int] = None,
    db_manager=None,
) -> SchedulerService:
    """Create a SchedulerService instance.

    Args:
        session: Optional database session
        max_workers: Maximum worker threads
        db_manager: Optional DatabaseManager

    Returns:
        Configured SchedulerService
    """
    return SchedulerService(
        session=session,
        max_workers=max_workers,
        db_manager=db_manager,
    )


def create_content_service(timeout_seconds: Optional[int] = None) -> ContentService:
    """Create a ContentService instance.

    Args:
        timeout_seconds: Request timeout

    Returns:
        Configured ContentService
    """
    return ContentService(timeout_seconds=timeout_seconds)


def create_keyword_service(
    max_keywords: Optional[int] = None,
    language: str = "auto",
) -> KeywordService:
    """Create a KeywordService instance.

    Args:
        max_keywords: Maximum keywords
        language: Language code

    Returns:
        Configured KeywordService
    """
    return KeywordService(max_keywords=max_keywords, language=language)


def create_summarizer_service(
    max_summary_length: Optional[int] = None,
    extractive_sentences: Optional[int] = None,
) -> SummarizerService:
    """Create a SummarizerService instance.

    Args:
        max_summary_length: Maximum summary length
        extractive_sentences: Number of sentences

    Returns:
        Configured SummarizerService
    """
    return SummarizerService(
        max_summary_length=max_summary_length,
        extractive_sentences=extractive_sentences,
    )
