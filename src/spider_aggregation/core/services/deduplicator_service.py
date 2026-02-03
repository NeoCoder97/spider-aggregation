"""
Facade for duplicate detection operations.

Provides unified interface for checking duplicate entries.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from spider_aggregation.logger import get_logger

if TYPE_CHECKING:
    from spider_aggregation.core.deduplicator import DedupResult


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
            entry_repo: EntryRepository instance (unused, kept for API compatibility)
            feed_id: Feed ID

        Returns:
            DedupResult indicating if duplicate and reason
        """
        return self._deduplicator.check_duplicate(parsed_entry, feed_id)


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
