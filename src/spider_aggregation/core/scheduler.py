"""
Task scheduler for automated feed fetching.

Uses APScheduler to manage periodic jobs for fetching RSS/Atom feeds.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobEvent
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from spider_aggregation.config import get_config
from spider_aggregation.core.fetcher import FeedFetcher, FetchResult
from spider_aggregation.logger import get_logger
from spider_aggregation.storage.repositories.feed_repo import FeedRepository

logger = get_logger(__name__)


@dataclass
class JobStatus:
    """Status of a scheduled job."""

    job_id: str
    name: str
    next_run_time: Optional[datetime]
    last_run_time: Optional[datetime]
    is_active: bool
    trigger: str
    runs_count: int = 0
    errors_count: int = 0
    last_result: Optional[FetchResult] = None
    last_error: Optional[str] = None


@dataclass
class SchedulerStats:
    """Statistics for scheduler operations."""

    total_jobs: int = 0
    active_jobs: int = 0
    paused_jobs: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    last_execution_time: Optional[datetime] = None
    uptime_seconds: float = 0.0


class FeedScheduler:
    """Scheduler for automated feed fetching."""

    def __init__(
        self,
        session: Optional[Session] = None,
        max_workers: int = 3,
        db_manager=None,
    ):
        """Initialize feed scheduler.

        Args:
            session: Optional database session for feed operations
            max_workers: Maximum number of concurrent worker threads
            db_manager: Optional DatabaseManager for creating sessions in jobs
        """
        config = get_config()

        self.session = session
        self.db_manager = db_manager
        self.max_workers = max_workers
        self.fetch_interval_minutes = config.scheduler.min_interval_minutes

        # Create background scheduler with thread pool executor
        self.scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=max_workers)},
            timezone=config.scheduler.timezone,
        )

        # Statistics
        self.stats = SchedulerStats()
        self.start_time: Optional[datetime] = None

        # Job tracking
        self._job_results: dict[str, FetchResult] = {}
        self._job_errors: dict[str, str] = {}

        # Add event listeners
        self.scheduler.add_listener(
            self._on_job_executed, EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._on_job_error, EVENT_JOB_ERROR
        )

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            self.start_time = datetime.now()
            logger.info(f"Scheduler started with {self.max_workers} workers")
        else:
            logger.warning("Scheduler is already running")

    def stop(self, wait: bool = True) -> None:
        """Stop the scheduler.

        Args:
            wait: Whether to wait for running jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            # Calculate uptime
            if self.start_time:
                self.stats.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            logger.info("Scheduler stopped")
        else:
            logger.warning("Scheduler is not running")

    def is_running(self) -> bool:
        """Check if the scheduler is running.

        Returns:
            True if scheduler is running
        """
        return self.scheduler.running

    def add_feed_job(
        self,
        feed_id: int,
        interval_minutes: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """Add a scheduled feed fetch job.

        Args:
            feed_id: Feed ID to fetch
            interval_minutes: Fetch interval in minutes (default from config)
            job_id: Custom job ID (auto-generated if not provided)

        Returns:
            Job ID
        """
        if job_id is None:
            job_id = f"feed_{feed_id}"

        interval = interval_minutes or self.fetch_interval_minutes

        # Create the job
        self.scheduler.add_job(
            func=self._fetch_feed_wrapper,
            trigger=IntervalTrigger(minutes=interval),
            id=job_id,
            name=f"Fetch Feed {feed_id}",
            args=[feed_id],
            replace_existing=True,
        )

        self.stats.total_jobs += 1
        logger.info(f"Added scheduled job for feed {feed_id} (every {interval} minutes)")

        return job_id

    def add_multiple_feeds_job(
        self,
        feed_ids: list[int],
        interval_minutes: Optional[int] = None,
        job_id: Optional[str] = None,
    ) -> str:
        """Add a scheduled job to fetch multiple feeds.

        Args:
            feed_ids: List of feed IDs to fetch
            interval_minutes: Fetch interval in minutes
            job_id: Custom job ID

        Returns:
            Job ID
        """
        if job_id is None:
            job_id = f"feeds_batch_{len(feed_ids)}"

        interval = interval_minutes or self.fetch_interval_minutes

        self.scheduler.add_job(
            func=self._fetch_feeds_wrapper,
            trigger=IntervalTrigger(minutes=interval),
            id=job_id,
            name=f"Fetch {len(feed_ids)} Feeds",
            args=[feed_ids],
            replace_existing=True,
        )

        self.stats.total_jobs += 1
        logger.info(f"Added batch job for {len(feed_ids)} feeds (every {interval} minutes)")

        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: Job ID to remove

        Returns:
            True if job was removed
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id}")
            return True
        except Exception:
            logger.warning(f"Job {job_id} not found")
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job.

        Args:
            job_id: Job ID to pause

        Returns:
            True if job was paused
        """
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job {job_id}")
            return True
        except Exception:
            logger.warning(f"Failed to pause job {job_id}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: Job ID to resume

        Returns:
            True if job was resumed
        """
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job {job_id}")
            return True
        except Exception:
            logger.warning(f"Failed to resume job {job_id}")
            return False

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get status of a specific job.

        Args:
            job_id: Job ID

        Returns:
            JobStatus or None if job not found
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return JobStatus(
                    job_id=job.id,
                    name=job.name,
                    next_run_time=job.next_run_time,
                    last_run_time=None,  # APScheduler doesn't track this
                    is_active=not (job.next_run_time is None),
                    trigger=str(job.trigger),
                    runs_count=0,  # Tracked via event listener
                    errors_count=0,  # Tracked via event listener
                    last_result=self._job_results.get(job_id),
                    last_error=self._job_errors.get(job_id),
                )
        except Exception:
            pass
        return None

    def get_all_jobs(self) -> list[JobStatus]:
        """Get status of all jobs.

        Returns:
            List of JobStatus for all jobs
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(JobStatus(
                job_id=job.id,
                name=job.name,
                next_run_time=job.next_run_time,
                last_run_time=None,
                is_active=not (job.next_run_time is None),
                trigger=str(job.trigger),
                last_result=self._job_results.get(job.id),
                last_error=self._job_errors.get(job.id),
            ))
        return jobs

    def get_stats(self) -> SchedulerStats:
        """Get scheduler statistics.

        Returns:
            SchedulerStats with current statistics
        """
        jobs = self.scheduler.get_jobs()
        self.stats.total_jobs = len(jobs)
        self.stats.active_jobs = len([j for j in jobs if j.next_run_time is not None])

        if self.start_time and self.scheduler.running:
            self.stats.uptime_seconds = (datetime.now() - self.start_time).total_seconds()

        return self.stats

    def _fetch_feed_wrapper(self, feed_id: int) -> FetchResult:
        """Wrapper for fetching a single feed.

        Args:
            feed_id: Feed ID to fetch

        Returns:
            FetchResult
        """
        # Use provided session or create a new one from db_manager
        if self.session:
            # Use the provided session (caller manages transaction)
            session = self.session
            manage_transaction = False
        elif self.db_manager:
            # Create a new session with proper transaction management
            manage_transaction = True
        else:
            logger.error(f"No database session or db_manager for job feed_{feed_id}")
            return FetchResult(
                success=False,
                feed_id=feed_id,
                feed_url="",
                error="No database session",
            )

        def _do_fetch(session: Session) -> FetchResult:
            """Inner function that performs the actual fetch."""
            repo = FeedRepository(session)
            feed = repo.get_by_id(feed_id)

            if not feed:
                logger.error(f"Feed {feed_id} not found")
                return FetchResult(
                    success=False,
                    feed_id=feed_id,
                    feed_url="",
                    error="Feed not found",
                )

            if not feed.enabled:
                logger.debug(f"Feed {feed_id} is disabled, skipping")
                return FetchResult(
                    success=True,
                    feed_id=feed_id,
                    feed_url=feed.url,
                    entries_count=0,
                )

            fetcher = FeedFetcher(session=session)
            result = fetcher.fetch_feed(feed)

            return result

        if manage_transaction:
            # Use context manager for proper transaction handling
            try:
                with self.db_manager.session() as session:
                    result = _do_fetch(session)

                    self.stats.total_executions += 1
                    if result.success:
                        self.stats.successful_executions += 1
                    else:
                        self.stats.failed_executions += 1

                    self.stats.last_execution_time = datetime.now()
                    self._job_results[f"feed_{feed_id}"] = result

                    return result

            except Exception as e:
                logger.exception(f"Error in job feed_{feed_id}: {e}")
                self.stats.failed_executions += 1
                self._job_errors[f"feed_{feed_id}"] = str(e)
                return FetchResult(
                    success=False,
                    feed_id=feed_id,
                    feed_url="",
                    error=str(e),
                )
        else:
            # Caller manages the session/transaction
            try:
                result = _do_fetch(self.session)

                self.stats.total_executions += 1
                if result.success:
                    self.stats.successful_executions += 1
                else:
                    self.stats.failed_executions += 1

                self.stats.last_execution_time = datetime.now()
                self._job_results[f"feed_{feed_id}"] = result

                return result

            except Exception as e:
                logger.exception(f"Error in job feed_{feed_id}: {e}")
                self.stats.failed_executions += 1
                self._job_errors[f"feed_{feed_id}"] = str(e)
                return FetchResult(
                    success=False,
                    feed_id=feed_id,
                    feed_url="",
                    error=str(e),
                )

    def _fetch_feeds_wrapper(self, feed_ids: list[int]) -> list[FetchResult]:
        """Wrapper for fetching multiple feeds.

        Args:
            feed_ids: List of feed IDs to fetch

        Returns:
            List of FetchResult
        """
        if not self.session:
            logger.error("No database session for batch job")
            return []

        results = []
        for feed_id in feed_ids:
            result = self._fetch_feed_wrapper(feed_id)
            results.append(result)

        return results

    def _on_job_executed(self, event: JobEvent) -> None:
        """Handle job executed event.

        Args:
            event: Job event
        """
        job_id = event.job_id
        if job_id and job_id in self._job_errors:
            # Clear previous error on successful execution
            del self._job_errors[job_id]

    def _on_job_error(self, event: JobEvent) -> None:
        """Handle job error event.

        Args:
            event: Job event
        """
        job_id = event.job_id
        exception = event.exception
        if job_id and exception:
            error_msg = f"{type(exception).__name__}: {str(exception)}"
            self._job_errors[job_id] = error_msg
            logger.error(f"Job {job_id} failed: {error_msg}")


def create_scheduler(
    session: Optional[Session] = None,
    max_workers: int = 3,
    db_manager=None,
) -> FeedScheduler:
    """Create a configured FeedScheduler instance.

    Args:
        session: Optional database session
        max_workers: Maximum number of concurrent worker threads
        db_manager: Optional DatabaseManager for creating sessions in jobs

    Returns:
        Configured FeedScheduler instance
    """
    return FeedScheduler(session=session, max_workers=max_workers, db_manager=db_manager)
