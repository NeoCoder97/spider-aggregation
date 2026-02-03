"""
Facade for full content fetching operations.

Provides unified interface for fetching full article content.
"""

from typing import TYPE_CHECKING, Optional

from spider_aggregation.logger import get_logger

if TYPE_CHECKING:
    from spider_aggregation.core.content_fetcher import ContentFetchResult


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
        return self._fetcher.fetch(url)


def create_content_service(timeout_seconds: Optional[int] = None) -> ContentService:
    """Create a ContentService instance.

    Args:
        timeout_seconds: Request timeout

    Returns:
        Configured ContentService
    """
    return ContentService(timeout_seconds=timeout_seconds)
