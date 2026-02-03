"""
Category API blueprint.

This module contains all category-related API endpoints.
"""

from flask import request
from spider_aggregation.web.blueprints.base import CRUDBlueprint
from spider_aggregation.web.serializers import api_response, SerializerRegistry
from spider_aggregation.logger import get_logger
from spider_aggregation.storage.repositories.category_repo import CategoryRepository
from spider_aggregation.models.category import CategoryCreate, CategoryUpdate
from spider_aggregation.models import FeedModel


class CategoryBlueprint(CRUDBlueprint):
    """Blueprint for category CRUD operations."""

    def __init__(self, db_path: str):
        """Initialize the category blueprint.

        Args:
            db_path: Path to the database file
        """
        super().__init__(db_path, url_prefix="/api/categories")
        self._register_custom_routes()

    def _register_custom_routes(self):
        """Register custom category-specific routes."""
        # Override default list route to support enabled_only parameter
        self.blueprint.add_url_rule(
            "",
            view_func=self._list,
            methods=["GET"]
        )
        # Get feeds for a category
        self.blueprint.add_url_rule(
            "/<int:category_id>/feeds",
            view_func=self._get_feeds,
            methods=["GET"]
        )
        # Get category statistics
        self.blueprint.add_url_rule(
            "/stats",
            view_func=self._get_stats,
            methods=["GET"]
        )
        # Get entry statistics for a category
        self.blueprint.add_url_rule(
            "/<int:category_id>/entries/stats",
            view_func=self._entries_stats,
            methods=["GET"]
        )

    def _list(self):
        """List all categories with optional filtering.

        Query params:
            enabled_only: Only return enabled categories
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import api_response

        enabled_only = request.args.get("enabled_only", False, type=bool)

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            items = repo.list(enabled_only=enabled_only, limit=1000)
            data = [self.serialize(item) for item in items]

        return api_response(success=True, data=data)

    def get_repository_class(self):
        """Get the CategoryRepository class."""
        return CategoryRepository

    def get_create_schema_class(self):
        """Get the CategoryCreate schema class."""
        return CategoryCreate

    def get_update_schema_class(self):
        """Get the CategoryUpdate schema class."""
        return CategoryUpdate

    def get_model_type(self) -> str:
        """Get the model type for SerializerRegistry."""
        return "category"

    def serialize(self, model, **kwargs) -> dict:
        """Convert Category model to dictionary with feed count.

        This override adds feed_count to the serialization using
        SerializerRegistry for the base serialization.

        Args:
            model: CategoryModel instance
            **kwargs: Additional parameters (not used, for compatibility)

        Returns:
            Dictionary with feed_count included
        """
        from spider_aggregation.storage.database import DatabaseManager
        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            feed_count = repo.get_feed_count_by_category(model.id)
            # Use SerializerRegistry for base serialization
            return SerializerRegistry.serialize("category", model, feed_count=feed_count)

    def get_resource_name(self) -> str:
        """Get the resource name for messages."""
        return "分类"

    def validate_create_data(self, data: dict) -> tuple[bool, str]:
        """Validate category creation data.

        Args:
            data: Request data

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not data.get("name"):
            return False, "分类名称为必填项"
        return True, ""

    def check_exists(self, repository, data: dict) -> bool:
        """Check if a category with the same name already exists.

        Args:
            repository: CategoryRepository instance
            data: Request data

        Returns:
            True if category exists, False otherwise
        """
        return repository.get_by_name(data["name"]) is not None

    def _create(self):
        """Override create to handle CategoryRepository's custom create method."""
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import api_response
        from spider_aggregation.logger import get_logger

        logger = get_logger(__name__)
        data = request.get_json()

        if not data:
            return api_response(success=False, error="请求数据为空", status=400)

        # Validate
        is_valid, error_msg = self.validate_create_data(data)
        if not is_valid:
            return api_response(success=False, error=error_msg, status=400)

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)

            # Check if already exists
            if self.check_exists(repo, data):
                return api_response(
                    success=False,
                    error=f"{self.get_resource_name()}已存在",
                    status=400
                )

            try:
                # CategoryRepository.create has custom signature
                item = repo.create(
                    name=data["name"],
                    description=data.get("description"),
                    color=data.get("color"),
                    icon=data.get("icon"),
                    enabled=data.get("enabled", True),
                )
                return api_response(
                    success=True,
                    data=self.serialize(item),
                    message=f"{self.get_resource_name()}创建成功",
                )
            except Exception as e:
                logger.error(f"Error creating {self.get_resource_name()}: {e}")
                return api_response(success=False, error=str(e), status=400)

    def _update(self, id: int):
        """Override update to handle CategoryRepository's custom update method."""
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import api_response
        from spider_aggregation.logger import get_logger

        logger = get_logger(__name__)
        data = request.get_json()

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            item = repo.get_by_id(id)

            if not item:
                return api_response(
                    success=False,
                    error=f"未找到{self.get_resource_name()}",
                    status=404
                )

            try:
                # CategoryRepository.update takes **kwargs
                updated_item = repo.update(item, **data)
                return api_response(
                    success=True,
                    data=self.serialize(updated_item),
                    message=f"{self.get_resource_name()}更新成功",
                )
            except Exception as e:
                logger.error(f"Error updating {self.get_resource_name()}: {e}")
                return api_response(success=False, error=str(e), status=400)

    def _get_feeds(self, category_id: int):
        """Get all feeds in a category.

        Args:
            category_id: Category ID

        Returns:
            API response with list of feeds
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import feed_to_dict

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)

            # Verify category exists
            category = repo.get_by_id(category_id)
            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            feeds = repo.get_feeds_by_category(category_id, limit=1000)
            total = repo.get_feed_count_by_category(category_id)
            data = [feed_to_dict(f) for f in feeds]

        return api_response(
            success=True,
            data={"feeds": data, "total": total}
        )

    def _get_stats(self):
        """Get statistics for all categories.

        Returns:
            API response with category statistics
        """
        from spider_aggregation.storage.database import DatabaseManager

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)

            total = repo.count()
            enabled = repo.count(enabled_only=True)

            stats = {
                "total": total,
                "enabled": enabled,
            }

        return api_response(success=True, data=stats)

    def _entries_stats(self, category_id: int):
        """Get entry statistics for a category.

        Args:
            category_id: Category ID

        Returns:
            API response with category entry statistics
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.storage.repositories.entry_repo import EntryRepository

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            entry_repo = EntryRepository(session)
            category_repo = self._get_repository(session)

            # Verify category exists
            category = category_repo.get_by_id(category_id)
            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            stats = entry_repo.get_stats_by_category(category_id)

        return api_response(
            success=True,
            data=stats
        )
