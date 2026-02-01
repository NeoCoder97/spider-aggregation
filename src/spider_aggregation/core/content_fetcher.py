"""
Content fetcher for extracting full article content from URLs.

Uses trafilatura as primary extractor with readability-lxml as fallback.
"""

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
from readability.readability import Document

from spider_aggregation.config import get_config
from spider_aggregation.logger import get_logger

logger = get_logger(__name__)

# Try to import trafilatura
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning("trafilatura not available, using readability-lxml only")


@dataclass
class ContentFetchResult:
    """Result of content fetching."""

    success: bool
    content: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    error: Optional[str] = None
    source: str = ""  # "trafilatura", "readability", or "fallback"

    def __repr__(self) -> str:
        return f"<ContentFetchResult(success={self.success}, source={self.source})>"


class ContentFetcher:
    """Fetches and extracts full content from article URLs."""

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        max_content_length: int = 500_000,
        user_agent: Optional[str] = None,
    ) -> None:
        """Initialize the content fetcher.

        Args:
            timeout_seconds: HTTP request timeout
            max_retries: Maximum number of retry attempts
            max_content_length: Maximum content length in bytes
            user_agent: Custom User-Agent header
        """
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_content_length = max_content_length

        config = get_config()

        # User agent with fallback
        self.user_agent = user_agent or config.content_fetcher.user_agent

        # Configure HTTP client
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
            max_redirects=5,
            headers={"User-Agent": self.user_agent},
        )

        logger.info(
            f"ContentFetcher initialized (trafilatura={TRAFILATURA_AVAILABLE})"
        )

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for content fetching.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid
        """
        try:
            result = urlparse(url)
            if not result.scheme or not result.netloc:
                return False

            # Only allow http and https
            if result.scheme not in ("http", "https"):
                return False

            return True
        except Exception:
            return False

    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                response = self._client.get(url)

                # Check content length
                content_length = len(response.content)
                if content_length > self.max_content_length:
                    logger.warning(
                        f"Content too large ({content_length} bytes) for {url}"
                    )
                    return None

                response.raise_for_status()
                return response.text

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                if attempt == self.max_retries - 1:
                    return None
            except Exception as e:
                logger.warning(
                    f"Error fetching HTML on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                if attempt == self.max_retries - 1:
                    return None

        return None

    def _extract_with_trafilatura(self, html: str, url: str) -> ContentFetchResult:
        """Extract content using trafilatura.

        Args:
            html: HTML content
            url: Source URL

        Returns:
            ContentFetchResult with extracted content
        """
        if not TRAFILATURA_AVAILABLE:
            return ContentFetchResult(success=False, error="trafilatura not available")

        try:
            # Extract content
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                url=url,
            )

            if not content or len(content.strip()) < 50:
                return ContentFetchResult(
                    success=False, error="trafilatura: no content extracted"
                )

            # Extract metadata
            metadata = trafilatura.metadata.extract_metadata(html)

            return ContentFetchResult(
                success=True,
                content=content.strip(),
                title=metadata.title if metadata else None,
                author=metadata.author if metadata else None,
                source="trafilatura",
            )

        except Exception as e:
            logger.warning(f"trafilatura extraction failed: {e}")
            return ContentFetchResult(success=False, error=f"trafilatura: {e}")

    def _extract_with_readability(self, html: str, url: str) -> ContentFetchResult:
        """Extract content using readability-lxml.

        Args:
            html: HTML content
            url: Source URL

        Returns:
            ContentFetchResult with extracted content
        """
        try:
            doc = Document(html, url=url)

            # Get title
            title = doc.title()

            # Get main content (HTML)
            content_html = doc.summary()

            if not content_html:
                return ContentFetchResult(
                    success=False, error="readability: no content extracted"
                )

            # Convert to plain text
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content_html, "lxml")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            content = soup.get_text(separator="\n", strip=True)

            if len(content.strip()) < 50:
                return ContentFetchResult(
                    success=False, error="readability: content too short"
                )

            return ContentFetchResult(
                success=True,
                content=content,
                title=title,
                source="readability",
            )

        except Exception as e:
            logger.warning(f"readability extraction failed: {e}")
            return ContentFetchResult(success=False, error=f"readability: {e}")

    def _extract_with_fallback(self, html: str, url: str) -> ContentFetchResult:
        """Fallback extraction using simple paragraph extraction.

        Args:
            html: HTML content
            url: Source URL

        Returns:
            ContentFetchResult with extracted content
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # Extract paragraphs
            paragraphs = soup.find_all("p")
            content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

            if len(content.strip()) < 50:
                return ContentFetchResult(
                    success=False, error="fallback: content too short"
                )

            # Get title
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else None

            return ContentFetchResult(
                success=True,
                content=content,
                title=title,
                source="fallback",
            )

        except Exception as e:
            logger.warning(f"fallback extraction failed: {e}")
            return ContentFetchResult(success=False, error=f"fallback: {e}")

    def fetch(self, url: str) -> ContentFetchResult:
        """Fetch and extract content from URL.

        Args:
            url: URL to fetch content from

        Returns:
            ContentFetchResult with extracted content
        """
        # Validate URL
        if not self._is_valid_url(url):
            return ContentFetchResult(success=False, error="Invalid URL")

        # Fetch HTML
        html = self._fetch_html(url)
        if not html:
            return ContentFetchResult(success=False, error="Failed to fetch HTML")

        # Try trafilatura first
        if TRAFILATURA_AVAILABLE:
            result = self._extract_with_trafilatura(html, url)
            if result.success:
                return result

        # Fallback to readability
        result = self._extract_with_readability(html, url)
        if result.success:
            return result

        # Final fallback
        return self._extract_with_fallback(html, url)

    def fetch_multiple(
        self, urls: list[str]
    ) -> dict[str, ContentFetchResult]:
        """Fetch content from multiple URLs.

        Args:
            urls: List of URLs to fetch

        Returns:
            Dictionary mapping URLs to ContentFetchResult
        """
        results = {}

        for url in urls:
            results[url] = self.fetch(url)

        successful = sum(1 for r in results.values() if r.success)
        logger.info(
            f"Fetched {len(urls)} URLs: {successful} successful, "
            f"{len(urls) - successful} failed"
        )

        return results

    def close(self) -> None:
        """Close the HTTP client."""
        if hasattr(self, "_client"):
            self._client.close()

    def __enter__(self) -> "ContentFetcher":
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.close()


def create_content_fetcher(
    timeout_seconds: Optional[int] = None,
    max_retries: Optional[int] = None,
    max_content_length: Optional[int] = None,
    user_agent: Optional[str] = None,
) -> ContentFetcher:
    """Factory function to create a ContentFetcher.

    Args:
        timeout_seconds: HTTP request timeout
        max_retries: Maximum retry attempts
        max_content_length: Maximum content length
        user_agent: Custom User-Agent

    Returns:
        Configured ContentFetcher instance
    """
    config = get_config()

    return ContentFetcher(
        timeout_seconds=timeout_seconds or config.content_fetcher.timeout_seconds,
        max_retries=max_retries or config.content_fetcher.max_retries,
        max_content_length=max_content_length or config.content_fetcher.max_content_length,
        user_agent=user_agent or config.content_fetcher.user_agent,
    )
