"""
Facade for content parsing operations.

Provides unified interface for parsing feed entries and metadata.
"""

from typing import TYPE_CHECKING, Optional

from spider_aggregation.logger import get_logger

if TYPE_CHECKING:
    from spider_aggregation.core.parser import FeedMetadata


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
        from spider_aggregation.utils.hash_utils import (
            compute_title_hash,
            compute_link_hash,
            compute_content_hash,
        )

        parsed = self._parser.parse_entry(entry_data)
        # Add feed_id to the parsed result
        parsed["feed_id"] = feed_id

        # Add hash fields for deduplication
        parsed["title_hash"] = compute_title_hash(parsed.get("title")) or ""
        parsed["link_hash"] = compute_link_hash(parsed.get("link")) or ""
        parsed["content_hash"] = compute_content_hash(parsed.get("content"))

        # Keep tags as list - EntryRepository will handle JSON serialization
        # The ContentParser returns tags as a list, which is what EntryCreate expects

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
