"""
Feed API blueprint.

This module contains all feed-related API endpoints.
"""

from flask import request
from spider_aggregation.web.blueprints.base import CRUDBlueprint
from spider_aggregation.web.serializers import api_response
from spider_aggregation.logger import get_logger
from spider_aggregation.storage.repositories.feed_repo import FeedRepository
from spider_aggregation.models import FeedCreate, FeedUpdate


class FeedBlueprint(CRUDBlueprint):
    """Blueprint for feed CRUD operations."""

    def __init__(self, db_path: str):
        """Initialize the feed blueprint.

        Args:
            db_path: Path to the database file
        """
        super().__init__(db_path, url_prefix="/api/feeds")
        self._register_custom_routes()

    def _register_custom_routes(self):
        """Register custom feed-specific routes."""
        # Manual fetch endpoint
        self.blueprint.add_url_rule(
            "/<int:feed_id>/fetch",
            view_func=self._fetch_feed,
            methods=["POST"]
        )
        # Get categories for a feed
        self.blueprint.add_url_rule(
            "/<int:feed_id>/categories",
            view_func=self._get_categories,
            methods=["GET"]
        )
        # Set categories for a feed
        self.blueprint.add_url_rule(
            "/<int:feed_id>/categories",
            view_func=self._set_categories,
            methods=["PUT", "POST"]
        )
        # Add category to feed
        self.blueprint.add_url_rule(
            "/<int:feed_id>/categories/<int:category_id>",
            view_func=self._add_category,
            methods=["PUT", "POST"]
        )
        # Remove category from feed
        self.blueprint.add_url_rule(
            "/<int:feed_id>/categories/<int:category_id>",
            view_func=self._remove_category,
            methods=["DELETE"]
        )

    def get_repository_class(self):
        """Get the FeedRepository class."""
        return FeedRepository

    def get_create_schema_class(self):
        """Get the FeedCreate schema class."""
        return FeedCreate

    def get_update_schema_class(self):
        """Get the FeedUpdate schema class."""
        return FeedUpdate

    def get_model_type(self) -> str:
        """Get the model type for SerializerRegistry."""
        return "feed"

    def get_resource_name(self) -> str:
        """Get the resource name for messages."""
        return "订阅源"

    def validate_create_data(self, data: dict) -> tuple[bool, str]:
        """Validate feed creation data.

        Args:
            data: Request data

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not data.get("url"):
            return False, "订阅源链接为必填项"
        return True, ""

    def check_exists(self, repository, data: dict) -> bool:
        """Check if a feed with the same URL already exists.

        Args:
            repository: FeedRepository instance
            data: Request data

        Returns:
            True if feed exists, False otherwise
        """
        return repository.get_by_url(data["url"]) is not None

    def _fetch_feed(self, feed_id: int):
        """Manually trigger a fetch for a specific feed.

        Args:
            feed_id: Feed ID

        Returns:
            API response
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.core.fetcher import FeedFetcher
        from spider_aggregation.core.parser import ContentParser
        from spider_aggregation.core.deduplicator import Deduplicator
        from spider_aggregation.core.filter_engine import FilterEngine

        logger = get_logger(__name__)
        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            feed = repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            # Fetch and process feed
            fetcher = FeedFetcher()
            parser = ContentParser()
            deduplicator = Deduplicator()

            from spider_aggregation.storage.repositories.entry_repo import EntryRepository
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

            entry_repo = EntryRepository(session)
            filter_rule_repo = FilterRuleRepository(session)

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
                repo.update_fetch_info(feed, increment_error=True, last_error=fetch_result.error)
                return api_response(
                    success=False,
                    error=fetch_result.error or "获取订阅源失败",
                    status=500
                )

            # Parse entries
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
                filter_engine = FilterEngine()
                filter_result = filter_engine.apply(parsed, filter_rule_repo)
                if not filter_result.allowed:
                    continue

                # Create entry
                from spider_aggregation.models import EntryCreate
                entry_create = EntryCreate(**parsed)
                entry_repo.create(entry_create)
                entries_created += 1

            # Update fetch info
            repo.update_fetch_info(
                feed,
                last_fetched_at=fetch_result.last_fetched_at,
                reset_errors=True,
                etag=fetch_result.etag,
                last_modified=fetch_result.last_modified
            )

            logger.info(f"Manually fetched feed {feed.id}: {entries_created} new entries")

            return api_response(
                success=True,
                data={
                    "entries_created": entries_created,
                    "feed": self.serialize(feed)
                },
                message=f"成功获取 {entries_created} 条新内容"
            )

    def _get_categories(self, feed_id: int):
        """Get categories for a feed.

        Args:
            feed_id: Feed ID

        Returns:
            API response with list of categories
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import category_to_dict

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            feed = repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            categories = repo.get_categories(feed)
            data = [category_to_dict(c) for c in categories]

        return api_response(success=True, data=data)

    def _set_categories(self, feed_id: int):
        """Set categories for a feed (replaces existing categories).

        Args:
            feed_id: Feed ID

        Returns:
            API response
        """
        from spider_aggregation.storage.database import DatabaseManager

        data = request.get_json()
        category_ids = data.get("category_ids", [])

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            feed = repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            repo.set_categories(feed, category_ids)
            # Refresh to get updated categories
            session.refresh(feed)

            from spider_aggregation.web.serializers import category_to_dict
            categories = repo.get_categories(feed)
            data = [category_to_dict(c) for c in categories]

        return api_response(
            success=True,
            data=data,
            message="分类设置成功"
        )

    def _add_category(self, feed_id: int, category_id: int):
        """Add a category to a feed.

        Args:
            feed_id: Feed ID
            category_id: Category ID

        Returns:
            API response
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.models import CategoryModel

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            feed = repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            category = session.query(CategoryModel).filter(
                CategoryModel.id == category_id
            ).first()

            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            repo.add_category(feed, category)

            from spider_aggregation.web.serializers import category_to_dict
            categories = repo.get_categories(feed)
            data = [category_to_dict(c) for c in categories]

        return api_response(
            success=True,
            data=data,
            message="分类添加成功"
        )

    def _remove_category(self, feed_id: int, category_id: int):
        """Remove a category from a feed.

        Args:
            feed_id: Feed ID
            category_id: Category ID

        Returns:
            API response
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.models import CategoryModel

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            feed = repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            category = session.query(CategoryModel).filter(
                CategoryModel.id == category_id
            ).first()

            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            repo.remove_category(feed, category)

            from spider_aggregation.web.serializers import category_to_dict
            categories = repo.get_categories(feed)
            data = [category_to_dict(c) for c in categories]

        return api_response(
            success=True,
            data=data,
            message="分类移除成功"
        )
