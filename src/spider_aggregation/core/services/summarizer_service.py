"""
Facade for content summarization operations.

Provides unified interface for generating content summaries.
"""

from typing import Optional

from spider_aggregation.logger import get_logger


class SummarizerService:
    """Facade for content summarization operations.

    Provides unified interface for generating content summaries.
    """

    def __init__(
        self,
        method: Optional[str] = None,
        max_sentences: Optional[int] = None,
    ):
        """Initialize summarizer service.

        Args:
            method: Summarization method (extractive or ai)
            max_sentences: Maximum sentences in summary
        """
        from spider_aggregation.core.factories import create_summarizer

        self._summarizer = create_summarizer(
            method=method,
            max_sentences=max_sentences,
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


def create_summarizer_service(
    method: Optional[str] = None,
    max_sentences: Optional[int] = None,
) -> SummarizerService:
    """Create a SummarizerService instance.

    Args:
        method: Summarization method (extractive or ai)
        max_sentences: Maximum sentences in summary

    Returns:
        Configured SummarizerService
    """
    return SummarizerService(
        method=method,
        max_sentences=max_sentences,
    )
