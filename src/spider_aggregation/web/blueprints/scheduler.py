"""
Scheduler API blueprint.

This module contains all scheduler management API endpoints.
"""

import threading
from flask import request
from spider_aggregation.web.serializers import api_response
from spider_aggregation.logger import get_logger


# Global scheduler instance reference
# This will be set by the app.py module
_scheduler_instance = None
_scheduler_lock = threading.Lock()


def get_scheduler():
    """Get the global scheduler instance.

    Returns:
        FeedScheduler instance or None
    """
    global _scheduler_instance
    return _scheduler_instance


def set_scheduler(scheduler):
    """Set the global scheduler instance.

    Args:
        scheduler: FeedScheduler instance
    """
    global _scheduler_instance
    with _scheduler_lock:
        _scheduler_instance = scheduler


class SchedulerBlueprint:
    """Blueprint for scheduler management operations."""

    def __init__(self, db_path: str):
        """Initialize the scheduler blueprint.

        Args:
            db_path: Path to the database file
        """
        from flask import Blueprint

        self.db_path = db_path
        self.blueprint = Blueprint(
            "scheduler",
            __name__,
            url_prefix="/api/scheduler"
        )
        self._register_routes()

    def _register_routes(self):
        """Register all scheduler routes."""
        self.blueprint.add_url_rule(
            "/status",
            view_func=self._status,
            methods=["GET"]
        )
        self.blueprint.add_url_rule(
            "/start",
            view_func=self._start,
            methods=["POST"]
        )
        self.blueprint.add_url_rule(
            "/stop",
            view_func=self._stop,
            methods=["POST"]
        )
        self.blueprint.add_url_rule(
            "/fetch-all",
            view_func=self._fetch_all,
            methods=["POST"]
        )

    def _status(self):
        """Get scheduler status.

        Returns:
            API response with scheduler status
        """
        from spider_aggregation.storage.database import DatabaseManager

        scheduler = get_scheduler()

        if scheduler:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            db_manager = DatabaseManager(self.db_path)

            with db_manager.session() as session:
                feed_repo = FeedRepository(session)
                total_feeds = feed_repo.count()
                enabled_feeds = feed_repo.count(enabled_only=True)

            jobs = scheduler.get_all_jobs()

            return api_response(
                success=True,
                data={
                    "is_running": scheduler.is_running(),
                    "total_feeds_count": total_feeds,
                    "enabled_feeds_count": enabled_feeds,
                    "jobs": [
                        {
                            "id": job.job_id,
                            "name": job.name,
                            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                        }
                        for job in jobs
                    ],
                }
            )
        else:
            # Get feed counts even when scheduler is not initialized
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            db_manager = DatabaseManager(self.db_path)
            with db_manager.session() as session:
                feed_repo = FeedRepository(session)
                total_feeds = feed_repo.count()
                enabled_feeds = feed_repo.count(enabled_only=True)

            return api_response(
                success=True,
                data={
                    "is_running": False,
                    "total_feeds_count": total_feeds,
                    "enabled_feeds_count": enabled_feeds,
                    "jobs": [],
                }
            )

    def _start(self):
        """Start the scheduler.

        Returns:
            API response
        """
        logger = get_logger(__name__)
        scheduler = get_scheduler()

        if not scheduler:
            return api_response(
                success=False,
                error="调度器未初始化",
                status=500
            )

        if scheduler.is_running():
            return api_response(
                success=True,
                message="调度器已在运行"
            )

        try:
            scheduler.start()
            logger.info("Scheduler started via API")
            return api_response(
                success=True,
                message="调度器启动成功"
            )
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            return api_response(
                success=False,
                error=str(e),
                status=500
            )

    def _stop(self):
        """Stop the scheduler.

        Returns:
            API response
        """
        logger = get_logger(__name__)
        scheduler = get_scheduler()

        if not scheduler:
            return api_response(
                success=False,
                error="调度器未初始化",
                status=500
            )

        if not scheduler.is_running():
            return api_response(
                success=True,
                message="调度器未运行"
            )

        try:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped via API")
            return api_response(
                success=True,
                message="调度器停止成功"
            )
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            return api_response(
                success=False,
                error=str(e),
                status=500
            )

    def _fetch_all(self):
        """Manually trigger fetch for all enabled feeds.

        Returns:
            API response with fetch results
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.core.services import (
            FetcherService,
            ParserService,
            DeduplicatorService,
            FilterService,
        )

        logger = get_logger(__name__)
        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

            feed_repo = FeedRepository(session)
            entry_repo = EntryRepository(session)
            filter_rule_repo = FilterRuleRepository(session)

            # Use Service Facades for all core operations
            fetcher = FetcherService(session=session)
            parser = ParserService()
            deduplicator = DeduplicatorService(session=session)
            filter_service = FilterService()

            # Get feeds to fetch
            feeds = feed_repo.get_feeds_to_fetch()

            results = []
            total_entries_created = 0

            for feed in feeds:
                try:
                    # Fetch
                    fetch_result = fetcher.fetch_feed(
                        url=feed.url,
                        feed_id=feed.id,
                        etag=feed.etag,
                        last_modified=feed.last_modified,
                        max_entries=feed.max_entries_per_fetch,
                        recent_only=feed.fetch_only_recent,
                    )

                    if not fetch_result.success:
                        feed_repo.update_fetch_info(
                            feed,
                            increment_error=True,
                            last_error=fetch_result.error
                        )
                        results.append({
                            "feed_id": feed.id,
                            "feed_name": feed.name,
                            "success": False,
                            "error": fetch_result.error
                        })
                        continue

                    # Parse and store entries
                    entries_created = 0
                    for entry_data in fetch_result.entries:
                        parsed = parser.parse_entry(entry_data, feed_id=feed.id)

                        # Check for duplicates
                        duplicate = deduplicator.check_duplicate(
                            parsed,
                            entry_repo,
                            feed_id=feed.id
                        )

                        if duplicate.is_duplicate:
                            continue

                        # Apply filter rules
                        filter_result = filter_service.apply(parsed, filter_rule_repo)
                        if not filter_result.allowed:
                            continue

                        # Create entry
                        from spider_aggregation.models import EntryCreate
                        entry_create = EntryCreate(**parsed)
                        entry_repo.create(entry_create)
                        entries_created += 1

                    # Update fetch info
                    feed_repo.update_fetch_info(
                        feed,
                        last_fetched_at=fetch_result.last_fetched_at,
                        reset_errors=True,
                        etag=fetch_result.etag,
                        last_modified=fetch_result.last_modified
                    )

                    total_entries_created += entries_created
                    results.append({
                        "feed_id": feed.id,
                        "feed_name": feed.name,
                        "success": True,
                        "entries_created": entries_created,
                        "http_status": fetch_result.http_status,
                    })

                except Exception as e:
                    logger.error(f"Error fetching feed {feed.id}: {e}")
                    results.append({
                        "feed_id": feed.id,
                        "feed_name": feed.name,
                        "success": False,
                        "error": str(e)
                    })

        logger.info(f"Manual fetch all completed: {total_entries_created} entries created")

        return api_response(
            success=True,
            data={
                "feeds_fetched": len(feeds),
                "total_entries_created": total_entries_created,
                "results": results
            },
            message=f"成功获取 {len(feeds)} 个订阅源，共创建 {total_entries_created} 条新内容"
        )
