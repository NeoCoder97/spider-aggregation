"""
Facade for keyword extraction operations.

Provides unified interface for extracting keywords from content.
"""

from typing import Optional

from spider_aggregation.logger import get_logger


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
