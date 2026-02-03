"""
Facade for task scheduling operations.

Provides unified interface for managing feed fetching schedules.
"""

from typing import Optional

from sqlalchemy.orm import Session

from spider_aggregation.logger import get_logger


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
