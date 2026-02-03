"""
Scheduler manager for Flask application.

Provides a clean way to manage the scheduler instance within Flask's application context,
eliminating the need for global variables.
"""

from typing import Optional

from flask import Flask, current_app

from spider_aggregation.core.scheduler import FeedScheduler
from spider_aggregation.logger import get_logger
from spider_aggregation.storage.database import DatabaseManager

logger = get_logger(__name__)


class SchedulerManager:
    """Manager for the feed scheduler within Flask application context.

    This class eliminates the need for global scheduler variables by
    storing the scheduler instance in Flask's application context.
    """

    def __init__(self, app: Optional[Flask] = None):
        """Initialize scheduler manager.

        Args:
            app: Optional Flask application instance
        """
        self._scheduler: Optional[FeedScheduler] = None
        self._db_manager: Optional[DatabaseManager] = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize the manager with a Flask application.

        Args:
            app: Flask application instance
        """
        # Store manager reference in app extensions
        app.extensions = getattr(app, "extensions", {})
        app.extensions["scheduler_manager"] = self

        # Register teardown handler
        app.teardown_appcontext(self._teardown)

    def _teardown(self, exception) -> None:
        """Teardown handler for application context."""
        # Scheduler is kept running across requests, only cleanup if needed
        pass

    def get_scheduler(self) -> Optional[FeedScheduler]:
        """Get the current scheduler instance.

        Returns:
            FeedScheduler instance or None if not initialized
        """
        return self._scheduler

    def initialize_scheduler(
        self,
        db_manager: DatabaseManager,
        max_workers: int = 3,
    ) -> FeedScheduler:
        """Initialize and start the scheduler.

        Args:
            db_manager: DatabaseManager instance
            max_workers: Maximum number of worker threads

        Returns:
            Initialized FeedScheduler instance
        """
        if self._scheduler is not None:
            logger.warning("Scheduler already initialized")
            return self._scheduler

        self._db_manager = db_manager

        try:
            from spider_aggregation.core.factories import create_scheduler

            self._scheduler = create_scheduler(
                session=None,
                max_workers=max_workers,
                db_manager=db_manager,
            )
            logger.info(f"Scheduler initialized with {max_workers} workers")
            return self._scheduler
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            raise

    def start_scheduler(self) -> bool:
        """Start the scheduler if not already running.

        Returns:
            True if started successfully or already running
        """
        if self._scheduler is None:
            logger.error("Cannot start scheduler: not initialized")
            return False

        if self._scheduler.is_running():
            logger.debug("Scheduler is already running")
            return True

        try:
            self._scheduler.start()
            logger.info("Scheduler started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False

    def stop_scheduler(self, wait: bool = True) -> bool:
        """Stop the scheduler if running.

        Args:
            wait: Whether to wait for running jobs to complete

        Returns:
            True if stopped successfully or not running
        """
        if self._scheduler is None:
            return True

        if not self._scheduler.is_running():
            return True

        try:
            self._scheduler.stop(wait=wait)
            logger.info("Scheduler stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False

    def get_stats(self) -> dict:
        """Get scheduler statistics.

        Returns:
            Dictionary with scheduler statistics
        """
        if self._scheduler is None:
            return {
                "initialized": False,
                "running": False,
                "total_jobs": 0,
                "active_jobs": 0,
            }

        stats = self._scheduler.get_stats()
        return {
            "initialized": True,
            "running": self._scheduler.is_running(),
            "total_jobs": stats.total_jobs,
            "active_jobs": stats.active_jobs,
            "total_executions": stats.total_executions,
            "successful_executions": stats.successful_executions,
            "failed_executions": stats.failed_executions,
            "uptime_seconds": stats.uptime_seconds,
        }

    def add_feed_job(self, feed_id: int, interval_minutes: int) -> bool:
        """Add a scheduled job for a feed.

        Args:
            feed_id: Feed ID
            interval_minutes: Fetch interval in minutes

        Returns:
            True if job was added successfully
        """
        if self._scheduler is None:
            logger.error("Cannot add job: scheduler not initialized")
            return False

        try:
            self._scheduler.add_feed_job(feed_id, interval_minutes)
            return True
        except Exception as e:
            logger.error(f"Failed to add feed job {feed_id}: {e}")
            return False

    def remove_feed_job(self, feed_id: int) -> bool:
        """Remove a scheduled job for a feed.

        Args:
            feed_id: Feed ID

        Returns:
            True if job was removed successfully
        """
        if self._scheduler is None:
            return False

        try:
            job_id = f"feed_{feed_id}"
            return self._scheduler.remove_job(job_id)
        except Exception as e:
            logger.error(f"Failed to remove feed job {feed_id}: {e}")
            return False


# Global manager instance (module-level, but stateless until init_app is called)
_manager: Optional[SchedulerManager] = None


def get_scheduler_manager() -> SchedulerManager:
    """Get the global scheduler manager instance.

    Returns:
        SchedulerManager instance
    """
    global _manager
    if _manager is None:
        _manager = SchedulerManager()
    return _manager


def init_scheduler_manager(app: Flask) -> SchedulerManager:
    """Initialize scheduler manager for a Flask app.

    Args:
        app: Flask application instance

    Returns:
        Initialized SchedulerManager
    """
    manager = get_scheduler_manager()
    manager.init_app(app)
    return manager


def get_scheduler() -> Optional[FeedScheduler]:
    """Get the current scheduler instance from the global manager.

    Convenience function for accessing the scheduler without
    directly importing the manager.

    Returns:
        FeedScheduler instance or None
    """
    return get_scheduler_manager().get_scheduler()
