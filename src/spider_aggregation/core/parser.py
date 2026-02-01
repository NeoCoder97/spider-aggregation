"""
Content parser for normalizing and cleaning feed entries.

Handles field standardization, date parsing, HTML cleaning, and content length limits.
"""

import re
from datetime import datetime
from html import unescape
from typing import Optional

from bs4 import BeautifulSoup

from spider_aggregation.config import get_config
from spider_aggregation.logger import get_logger

logger = get_logger(__name__)


class ContentParser:
    """Parser for normalizing and cleaning feed entry content."""

    def __init__(
        self,
        max_content_length: Optional[int] = None,
        strip_html: bool = True,
        preserve_paragraphs: bool = True,
    ):
        """Initialize content parser.

        Args:
            max_content_length: Maximum content length in characters
            strip_html: Whether to strip HTML tags
            preserve_paragraphs: Whether to preserve paragraphs when stripping HTML
        """
        config = get_config()

        self.max_content_length = max_content_length or config.fetcher.max_content_length
        self.strip_html = strip_html
        self.preserve_paragraphs = preserve_paragraphs

    def parse_entry(self, raw_entry: dict) -> dict:
        """Parse and normalize a raw feed entry.

        Args:
            raw_entry: Raw entry from feedparser

        Returns:
            Normalized entry dictionary
        """
        parsed = {
            "title": self._normalize_title(raw_entry.get("title")),
            "link": self._normalize_link(raw_entry.get("link")),
            "author": self._normalize_author(raw_entry.get("author")),
            "summary": self._normalize_summary(raw_entry.get("summary")),
            "content": self._normalize_content(
                raw_entry.get("content") or raw_entry.get("summary")
            ),
            "published_at": self._parse_date(raw_entry.get("published")),
            "updated_at": self._parse_date(raw_entry.get("updated")),
            "tags": self._extract_tags(raw_entry),
            "language": self._detect_language(raw_entry),
            "reading_time_seconds": None,
        }

        # Calculate reading time
        if parsed["content"]:
            parsed["reading_time_seconds"] = self._calculate_reading_time(parsed["content"])

        return parsed

    def _normalize_title(self, title: Optional[str]) -> Optional[str]:
        """Normalize entry title.

        Args:
            title: Raw title

        Returns:
            Normalized title
        """
        if not title:
            return None

        # Unescape HTML entities
        title = unescape(title)

        # Strip whitespace and normalize internal whitespace
        title = re.sub(r"\s+", " ", title.strip())

        # Limit length
        if len(title) > 500:
            title = title[:497] + "..."

        return title if title else None

    def _normalize_link(self, link: Optional[str]) -> Optional[str]:
        """Normalize entry link.

        Args:
            link: Raw link

        Returns:
            Normalized link
        """
        if not link:
            return None

        # Strip whitespace
        link = link.strip()

        # Basic validation
        if not link.startswith(("http://", "https://", "ftp://")):
            logger.warning(f"Invalid link format: {link}")
            return None

        return link

    def _normalize_author(self, author: Optional[str]) -> Optional[str]:
        """Normalize entry author.

        Args:
            author: Raw author

        Returns:
            Normalized author
        """
        if not author:
            return None

        # Handle dict format (some feeds)
        if isinstance(author, dict):
            author = author.get("name") or author.get("email")

        # Unescape HTML entities
        author = unescape(str(author))

        # Strip whitespace and common prefixes
        author = author.strip()
        author = re.sub(r"^(by|posted by)\s+", "", author, flags=re.IGNORECASE)

        # Limit length
        if len(author) > 200:
            author = author[:197] + "..."

        return author if author else None

    def _normalize_summary(self, summary: Optional[str]) -> Optional[str]:
        """Normalize entry summary.

        Args:
            summary: Raw summary

        Returns:
            Normalized summary
        """
        if not summary:
            return None

        # Clean HTML if enabled
        if self.strip_html:
            summary = self._strip_html(summary, preserve_paragraphs=True)

        # Unescape HTML entities
        summary = unescape(summary)

        # Strip whitespace
        summary = summary.strip()

        # Limit length
        if len(summary) > 1000:
            summary = summary[:997] + "..."

        return summary if summary else None

    def _normalize_content(self, content: Optional[str]) -> Optional[str]:
        """Normalize entry content.

        Args:
            content: Raw content

        Returns:
            Normalized content
        """
        if not content:
            return None

        # Clean HTML if enabled
        if self.strip_html:
            content = self._strip_html(content, preserve_paragraphs=self.preserve_paragraphs)

        # Unescape HTML entities
        content = unescape(content)

        # Normalize whitespace
        content = self._normalize_whitespace(content)

        # Limit length
        if len(content) > self.max_content_length:
            content = content[: self.max_content_length - 3] + "..."
            logger.debug(f"Content truncated to {self.max_content_length} characters")

        return content if content else None

    def _strip_html(self, html: str, preserve_paragraphs: bool = True) -> str:
        """Strip HTML tags from content.

        Args:
            html: HTML content
            preserve_paragraphs: Whether to preserve paragraphs

        Returns:
            Plain text content
        """
        if not html:
            return ""

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Get text
        if preserve_paragraphs:
            # Preserve paragraph structure
            text = soup.get_text(separator="\n\n")
        else:
            text = soup.get_text()

        return text.strip()

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.

        Args:
            text: Text with potential irregular whitespace

        Returns:
            Text with normalized whitespace
        """
        if not text:
            return ""

        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)

        # Replace multiple newlines with double newline
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Final strip
        return text.strip()

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object.

        Args:
            date_str: Date string in various formats

        Returns:
            datetime object or None
        """
        if not date_str:
            return None

        if isinstance(date_str, datetime):
            return date_str

        # Try parsing with feedparser's built-in parser first
        try:
            import feedparser

            parsed = feedparser._parse_date(date_str)
            if parsed:
                # Convert time.struct_time to datetime
                return datetime(*parsed[:6])
        except Exception:
            pass

        # Try common date formats
        date_formats = [
            # ISO 8601 formats
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            # RFC 2822 format
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S",
            "%a, %d %b %Y %H:%M:%S %Z",
            # Common formats
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d.%m.%Y",
            # With month names
            "%d %b %Y",
            "%b %d, %Y",
            "%b %d %Y %H:%M:%S",
            # Additional formats
            "%Y%m%d",
            "%Y%m%d %H%M%S",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue

        # Try parsing without timezone
        try:
            # Remove timezone info and try again
            date_str_clean = re.sub(r"[+-]\d{2}:\d{2}$", "", date_str.strip())
            date_str_clean = re.sub(r"[+-]\d{4}$", "", date_str_clean)
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str_clean, fmt)
                except (ValueError, TypeError):
                    continue
        except Exception:
            pass

        logger.warning(f"Failed to parse date: {date_str}")
        return None

    def _extract_tags(self, raw_entry: dict) -> Optional[list[str]]:
        """Extract tags from entry.

        Args:
            raw_entry: Raw entry from feedparser

        Returns:
            List of tags
        """
        tags = []

        # Try tags field
        if "tags" in raw_entry:
            raw_tags = raw_entry.get("tags")
            if isinstance(raw_tags, list):
                tags = [tag.get("term") if isinstance(tag, dict) else tag for tag in raw_tags]
            elif isinstance(raw_tags, str):
                tags = raw_tags.split(",")

        # Try categories
        if not tags and "categories" in raw_entry:
            raw_categories = raw_entry.get("categories")
            if isinstance(raw_categories, list):
                tags = [
                    cat.get("term") if isinstance(cat, dict) else cat
                    for cat in raw_categories
                ]
            elif isinstance(raw_categories, str):
                tags = raw_categories.split(",")

        # Clean and deduplicate tags
        cleaned_tags = []
        for tag in tags:
            if tag:
                tag = str(tag).strip().lower()
                if tag and tag not in cleaned_tags:
                    cleaned_tags.append(tag)

        return cleaned_tags if cleaned_tags else None

    def _detect_language(self, raw_entry: dict) -> Optional[str]:
        """Detect entry language.

        Args:
            raw_entry: Raw entry from feedparser

        Returns:
            Language code (e.g., 'en', 'zh')
        """
        # Try to get language from feedparser
        if "language" in raw_entry:
            lang = raw_entry.get("language")
            if lang:
                # Normalize language code (e.g., "en-US" -> "en")
                lang = str(lang).split("-")[0].lower()
                if lang in ["en", "zh", "ja", "ko", "fr", "de", "es", "ru", "pt"]:
                    return lang

        # Simple detection based on content
        content = raw_entry.get("summary") or raw_entry.get("description") or ""
        if content:
            # Detect Japanese characters (Hiragana, Katakana)
            if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", content):
                return "ja"
            # Detect Chinese characters (after Japanese check to avoid overlap)
            if re.search(r"[\u4e00-\u9fff]", content):
                return "zh"
            # Default to English if has Latin characters
            if re.search(r"[a-zA-Z]", content):
                return "en"

        return None

    def _calculate_reading_time(self, content: str) -> int:
        """Calculate estimated reading time in seconds.

        Args:
            content: Content text

        Returns:
            Reading time in seconds
        """
        if not content:
            return 0

        # Count words (approximate)
        # Split by whitespace to get word count
        words = content.split()
        word_count = len(words)

        # Average reading speed: ~200-250 words per minute
        # For Chinese: ~400-500 characters per minute (we use word_count which underestimates)
        # For English: ~200-250 words per minute
        words_per_minute = 200

        reading_time_minutes = word_count / words_per_minute
        reading_time_seconds = int(reading_time_minutes * 60)

        return max(10, reading_time_seconds)  # Minimum 10 seconds


class FeedMetadataParser:
    """Parser for feed metadata."""

    def __init__(self):
        """Initialize feed metadata parser."""
        pass

    def parse_feed_info(self, raw_feed) -> dict:
        """Parse and normalize feed metadata.

        Args:
            raw_feed: Raw feed data from feedparser (can be dict or object)

        Returns:
            Normalized feed metadata
        """
        # Extract feed data - handle both dict and object
        if hasattr(raw_feed, "feed"):
            feed = raw_feed.feed
        else:
            feed = raw_feed

        # Get entry count - handle both dict and object
        entries = []
        if hasattr(raw_feed, "entries"):
            entries = raw_feed.entries
        elif isinstance(raw_feed, dict):
            entries = raw_feed.get("entries", [])

        return {
            "title": self._normalize_title(feed.get("title") if feed else None),
            "link": self._normalize_link(feed.get("link") if feed else None),
            "description": self._normalize_description(
                feed.get("description") if feed else None
            ),
            "language": feed.get("language") if feed else None,
            "updated_at": ContentParser()._parse_date(feed.get("updated") if feed else None),
            "entry_count": len(entries),
        }

    def _normalize_title(self, title: Optional[str]) -> Optional[str]:
        """Normalize feed title."""
        if not title:
            return None

        title = unescape(str(title)).strip()
        return title if title else None

    def _normalize_link(self, link: Optional[str]) -> Optional[str]:
        """Normalize feed link."""
        if not link:
            return None

        link = link.strip()
        if link.startswith(("http://", "https://")):
            return link
        return None

    def _normalize_description(self, description: Optional[str]) -> Optional[str]:
        """Normalize feed description."""
        if not description:
            return None

        description = unescape(str(description))

        # Strip HTML if present
        if "<" in description:
            soup = BeautifulSoup(description, "html.parser")
            description = soup.get_text()

        return description.strip() if description.strip() else None


def create_parser(
    max_content_length: Optional[int] = None,
    strip_html: bool = True,
    preserve_paragraphs: bool = True,
) -> ContentParser:
    """Create a configured ContentParser instance.

    Args:
        max_content_length: Maximum content length
        strip_html: Whether to strip HTML
        preserve_paragraphs: Whether to preserve paragraphs

    Returns:
        Configured ContentParser instance
    """
    return ContentParser(
        max_content_length=max_content_length,
        strip_html=strip_html,
        preserve_paragraphs=preserve_paragraphs,
    )
