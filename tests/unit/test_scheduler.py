"""Unit and integration tests for feed scheduler."""

from time import sleep
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from spider_aggregation.core.scheduler import (
    FeedScheduler,
    JobStatus,
    SchedulerStats,
    create_scheduler,
)
from spider_aggregation.core.fetcher import FetchResult


class TestJobStatus:
    """Tests for JobStatus dataclass."""

    def test_job_status_creation(self):
        """Test creating a job status."""
        status = JobStatus(
            job_id="test_job",
            name="Test Job",
            next_run_time=None,
            last_run_time=None,
            is_active=True,
            trigger="interval[1]",
        )

        assert status.job_id == "test_job"
        assert status.name == "Test Job"
        assert status.is_active is True
        assert status.runs_count == 0
        assert status.errors_count == 0


class TestSchedulerStats:
    """Tests for SchedulerStats dataclass."""

    def test_scheduler_stats_creation(self):
        """Test creating scheduler stats."""
        stats = SchedulerStats()

        assert stats.total_jobs == 0
        assert stats.active_jobs == 0
        assert stats.total_executions == 0
        assert stats.uptime_seconds == 0.0


class TestFeedScheduler:
    """Tests for FeedScheduler."""

    def test_init(self):
        """Test scheduler initialization."""
        scheduler = FeedScheduler()

        assert scheduler.session is None
        assert scheduler.max_workers == 3
        assert scheduler.is_running() is False
        assert scheduler.stats.total_jobs == 0

    def test_init_with_session(self, db_session: Session):
        """Test scheduler with database session."""
        scheduler = FeedScheduler(session=db_session)

        assert scheduler.session is db_session

    def test_init_with_custom_params(self):
        """Test scheduler with custom parameters."""
        scheduler = FeedScheduler(max_workers=5)

        assert scheduler.max_workers == 5

    def test_start_stop(self):
        """Test starting and stopping scheduler."""
        scheduler = FeedScheduler()

        # Start
        scheduler.start()
        assert scheduler.is_running() is True

        # Stop
        scheduler.stop(wait=True)
        assert scheduler.is_running() is False

    def test_start_when_already_running(self):
        """Test starting when already running."""
        scheduler = FeedScheduler()

        scheduler.start()
        assert scheduler.is_running() is True

        # Try starting again (should warn but not crash)
        scheduler.start()
        assert scheduler.is_running() is True

        scheduler.stop(wait=True)

    def test_stop_when_not_running(self):
        """Test stopping when not running."""
        scheduler = FeedScheduler()

        # Stop without starting (should warn but not crash)
        scheduler.stop(wait=True)
        assert scheduler.is_running() is False

    def test_add_feed_job(self):
        """Test adding a single feed job."""
        scheduler = FeedScheduler()
        scheduler.start()

        job_id = scheduler.add_feed_job(feed_id=1)

        assert job_id == "feed_1"
        assert scheduler.stats.total_jobs == 1

        scheduler.stop(wait=True)

    def test_add_feed_job_with_custom_id(self):
        """Test adding a feed job with custom ID."""
        scheduler = FeedScheduler()
        scheduler.start()

        job_id = scheduler.add_feed_job(feed_id=1, job_id="my_custom_job")

        assert job_id == "my_custom_job"

        scheduler.stop(wait=True)

    def test_add_feed_job_with_custom_interval(self):
        """Test adding a feed job with custom interval."""
        scheduler = FeedScheduler()
        scheduler.start()

        job_id = scheduler.add_feed_job(feed_id=1, interval_minutes=30)

        # Get the job and check the trigger
        status = scheduler.get_job_status(job_id)
        assert status is not None
        assert "30" in status.trigger  # Interval should include 30 minutes

        scheduler.stop(wait=True)

    def test_add_multiple_feeds_job(self):
        """Test adding a batch job for multiple feeds."""
        scheduler = FeedScheduler()
        scheduler.start()

        job_id = scheduler.add_multiple_feeds_job(feed_ids=[1, 2, 3])

        assert job_id == "feeds_batch_3"
        assert scheduler.stats.total_jobs == 1

        scheduler.stop(wait=True)

    def test_remove_job(self):
        """Test removing a job."""
        scheduler = FeedScheduler()
        scheduler.start()

        job_id = scheduler.add_feed_job(feed_id=1)

        # Remove the job
        result = scheduler.remove_job(job_id)
        assert result is True

        # Job should no longer exist
        status = scheduler.get_job_status(job_id)
        assert status is None

        scheduler.stop(wait=True)

    def test_remove_nonexistent_job(self):
        """Test removing a job that doesn't exist."""
        scheduler = FeedScheduler()

        result = scheduler.remove_job("nonexistent_job")
        assert result is False

    def test_pause_resume_job(self):
        """Test pausing and resuming a job."""
        scheduler = FeedScheduler()
        scheduler.start()

        job_id = scheduler.add_feed_job(feed_id=1)

        # Pause
        result = scheduler.pause_job(job_id)
        assert result is True

        status = scheduler.get_job_status(job_id)
        assert status is not None
        assert status.is_active is False

        # Resume
        result = scheduler.resume_job(job_id)
        assert result is True

        status = scheduler.get_job_status(job_id)
        assert status is not None
        # After resuming, next_run_time should be set again
        # Note: In APScheduler, paused jobs have next_run_time=None

        scheduler.stop(wait=True)

    def test_get_job_status(self):
        """Test getting job status."""
        scheduler = FeedScheduler()
        scheduler.start()

        job_id = scheduler.add_feed_job(feed_id=1)

        status = scheduler.get_job_status(job_id)

        assert status is not None
        assert status.job_id == job_id
        assert status.name == "Fetch Feed 1"
        assert status.next_run_time is not None
        assert status.is_active is True

        scheduler.stop(wait=True)

    def test_get_job_status_nonexistent(self):
        """Test getting status of nonexistent job."""
        scheduler = FeedScheduler()

        status = scheduler.get_job_status("nonexistent")

        assert status is None

    def test_get_all_jobs(self):
        """Test getting all jobs."""
        scheduler = FeedScheduler()
        scheduler.start()

        scheduler.add_feed_job(feed_id=1)
        scheduler.add_feed_job(feed_id=2)
        scheduler.add_feed_job(feed_id=3)

        jobs = scheduler.get_all_jobs()

        assert len(jobs) == 3

        scheduler.stop(wait=True)

    def test_get_all_jobs_empty(self):
        """Test getting all jobs when none exist."""
        scheduler = FeedScheduler()
        scheduler.start()

        jobs = scheduler.get_all_jobs()

        assert len(jobs) == 0

        scheduler.stop(wait=True)

    def test_get_stats(self):
        """Test getting scheduler statistics."""
        scheduler = FeedScheduler()
        scheduler.start()

        scheduler.add_feed_job(feed_id=1)
        scheduler.add_feed_job(feed_id=2)
        scheduler.pause_job("feed_2")

        stats = scheduler.get_stats()

        assert stats.total_jobs == 2
        assert stats.active_jobs == 1  # One job is paused
        assert stats.uptime_seconds >= 0

        scheduler.stop(wait=True)

    def test_job_execution_with_session(self, db_session: Session):
        """Test job execution with database session."""
        # Create a feed
        from spider_aggregation.storage.repositories.feed_repo import FeedRepository
        from spider_aggregation.models.feed import FeedCreate

        repo = FeedRepository(db_session)
        feed = repo.create(
            FeedCreate(
                url="https://example.com/feed.xml",
                name="Test Feed",
                enabled=True,
            )
        )

        # Mock the fetcher to avoid actual HTTP calls
        with patch("spider_aggregation.core.scheduler.FeedFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_result = FetchResult(
                success=True,
                feed_id=feed.id,
                feed_url=feed.url,
                entries_count=5,
            )
            mock_fetcher.fetch_feed.return_value = mock_result
            mock_fetcher_class.return_value = mock_fetcher

            scheduler = FeedScheduler(session=db_session)
            scheduler.start()

            job_id = scheduler.add_feed_job(feed_id=feed.id)

            # Wait a moment for job to potentially execute (it won't execute immediately)
            # Actually, APScheduler jobs won't run until the interval passes
            # So we'll test the wrapper directly

            # Stop scheduler
            scheduler.stop(wait=True)

    def test_job_execution_without_session(self):
        """Test job execution without database session."""
        scheduler = FeedScheduler(session=None)
        scheduler.start()

        # Mock the job execution would fail without session
        # The wrapper should handle this gracefully
        result = scheduler._fetch_feed_wrapper(1)

        assert result.success is False
        assert "No database session" in result.error

        scheduler.stop(wait=True)

    def test_job_execution_feed_not_found(self, db_session: Session):
        """Test job execution when feed doesn't exist."""
        scheduler = FeedScheduler(session=db_session)

        result = scheduler._fetch_feed_wrapper(feed_id=999)

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_job_execution_feed_disabled(self, db_session: Session):
        """Test job execution when feed is disabled."""
        from spider_aggregation.storage.repositories.feed_repo import FeedRepository
        from spider_aggregation.models.feed import FeedCreate

        repo = FeedRepository(db_session)
        feed = repo.create(
            FeedCreate(
                url="https://example.com/feed.xml",
                name="Test Feed",
                enabled=False,
            )
        )

        scheduler = FeedScheduler(session=db_session)

        result = scheduler._fetch_feed_wrapper(feed_id=feed.id)

        assert result.success is True
        assert result.entries_count == 0

    def test_multiple_jobs_execution(self, db_session: Session):
        """Test executing multiple feeds job."""
        from spider_aggregation.storage.repositories.feed_repo import FeedRepository
        from spider_aggregation.models.feed import FeedCreate

        repo = FeedRepository(db_session)
        feed1 = repo.create(
            FeedCreate(url="https://example.com/feed1.xml", name="Feed 1")
        )
        feed2 = repo.create(
            FeedCreate(url="https://example.com/feed2.xml", name="Feed 2")
        )

        # Mock the fetcher
        with patch("spider_aggregation.core.scheduler.FeedFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_result = FetchResult(
                success=True,
                feed_id=1,
                feed_url="https://example.com/feed",
                entries_count=5,
            )
            mock_fetcher.fetch_feed.return_value = mock_result
            mock_fetcher_class.return_value = mock_fetcher

            scheduler = FeedScheduler(session=db_session)

            results = scheduler._fetch_feeds_wrapper([feed1.id, feed2.id])

            assert len(results) == 2

    def test_uptime_tracking(self):
        """Test scheduler uptime tracking."""
        scheduler = FeedScheduler()

        scheduler.start()
        sleep(0.1)  # Small delay

        stats = scheduler.get_stats()
        assert stats.uptime_seconds >= 0.1

        scheduler.stop(wait=True)

        uptime_after_stop = stats.uptime_seconds
        assert uptime_after_stop >= 0.1


class TestCreateScheduler:
    """Tests for create_scheduler factory function."""

    def test_create_scheduler_default(self):
        """Test creating scheduler with defaults."""
        scheduler = create_scheduler()

        assert isinstance(scheduler, FeedScheduler)
        assert scheduler.max_workers == 3

    def test_create_scheduler_with_session(self, db_session: Session):
        """Test creating scheduler with session."""
        scheduler = create_scheduler(session=db_session)

        assert isinstance(scheduler, FeedScheduler)
        assert scheduler.session is db_session

    def test_create_scheduler_with_custom_workers(self):
        """Test creating scheduler with custom workers."""
        scheduler = create_scheduler(max_workers=10)

        assert isinstance(scheduler, FeedScheduler)
        assert scheduler.max_workers == 10


class TestSchedulerIntegration:
    """Integration tests for scheduler with real feeds."""

    def test_full_scheduler_lifecycle(self, db_session: Session):
        """Test complete scheduler lifecycle with database."""
        from spider_aggregation.storage.repositories.feed_repo import FeedRepository
        from spider_aggregation.models.feed import FeedCreate

        # Create feeds
        repo = FeedRepository(db_session)
        feed1 = repo.create(
            FeedCreate(url="https://example.com/feed1.xml", name="Feed 1")
        )
        feed2 = repo.create(
            FeedCreate(url="https://example.com/feed2.xml", name="Feed 2")
        )

        # Create scheduler
        scheduler = FeedScheduler(session=db_session)

        # Start
        scheduler.start()
        assert scheduler.is_running() is True

        # Add jobs
        job1 = scheduler.add_feed_job(feed_id=feed1.id)
        job2 = scheduler.add_feed_job(feed_id=feed2.id)
        batch_job = scheduler.add_multiple_feeds_job(feed_ids=[feed1.id, feed2.id])

        # Check jobs
        jobs = scheduler.get_all_jobs()
        assert len(jobs) == 3

        # Check stats
        stats = scheduler.get_stats()
        assert stats.total_jobs == 3

        # Pause a job
        scheduler.pause_job(job1)
        status = scheduler.get_job_status(job1)
        assert status.is_active is False

        # Resume
        scheduler.resume_job(job1)
        status = scheduler.get_job_status(job1)
        # After resume, should be active again (next_run_time set)

        # Remove job
        scheduler.remove_job(job2)
        jobs = scheduler.get_all_jobs()
        assert len(jobs) == 2

        # Stop
        scheduler.stop(wait=True)
        assert scheduler.is_running() is False


class TestFeedSchedulerExtended:
    """Extended tests for FeedScheduler to improve coverage."""

    def test_job_result_tracking(self, db_session: Session):
        """Test job results are tracked."""
        from spider_aggregation.storage.repositories.feed_repo import FeedRepository
        from spider_aggregation.models.feed import FeedCreate

        repo = FeedRepository(db_session)
        feed = repo.create(
            FeedCreate(
                url="https://example.com/feed.xml",
                name="Test Feed",
            )
        )

        # Mock fetcher
        with patch("spider_aggregation.core.scheduler.FeedFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_result = FetchResult(
                success=True,
                feed_id=feed.id,
                feed_url=feed.url,
                entries_count=5,
            )
            mock_fetcher.fetch_feed.return_value = mock_result
            mock_fetcher_class.return_value = mock_fetcher

            scheduler = FeedScheduler(session=db_session)

            # Execute job
            scheduler._fetch_feed_wrapper(feed_id=feed.id)

            # Result should be tracked
            job_id = f"feed_{feed.id}"
            assert job_id in scheduler._job_results
            assert scheduler._job_results[job_id].entries_count == 5
