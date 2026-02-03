"""
Base CRUD blueprint for common API endpoint patterns.

This module provides a base blueprint class that encapsulates common CRUD
operations for API endpoints to eliminate code duplication.
"""

from abc import ABC, abstractmethod
from typing import Type, TypeVar, Callable, Optional, Any

from flask import Blueprint, request, jsonify

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
RepositoryType = TypeVar("RepositoryType")


class CRUDBlueprint(ABC):
    """Base CRUD blueprint with common endpoints.

    This class provides a template for creating CRUD API blueprints with
    consistent patterns across all resources.

    Subclasses must implement the abstract methods to provide the specific
    repository, schema classes, and serializer function.
    """

    def __init__(self, db_path: str, url_prefix: str):
        """Initialize the CRUD blueprint.

        Args:
            db_path: Path to the database file
            url_prefix: URL prefix for all routes in this blueprint
        """
        self.db_path = db_path
        self.blueprint = Blueprint(
            self._get_blueprint_name(),
            self.__class__.__name__,
            url_prefix=url_prefix
        )
        self._register_routes()

    def _get_blueprint_name(self) -> str:
        """Get the blueprint name from the class name."""
        return self.__class__.__name__.replace("Blueprint", "").lower()

    def _register_routes(self):
        """Register all CRUD routes on the blueprint."""
        self.blueprint.add_url_rule("", view_func=self._list, methods=["GET"])
        self.blueprint.add_url_rule("/<int:id>", view_func=self._get_by_id, methods=["GET"])
        self.blueprint.add_url_rule("", view_func=self._create, methods=["POST"])
        self.blueprint.add_url_rule("/<int:id>", view_func=self._update, methods=["PUT", "POST"])
        self.blueprint.add_url_rule("/<int:id>", view_func=self._delete, methods=["DELETE"])
        self.blueprint.add_url_rule("/<int:id>/toggle", view_func=self._toggle, methods=["PATCH", "POST"])

    @abstractmethod
    def get_repository_class(self) -> Type[RepositoryType]:
        """Get the repository class for this resource.

        Returns:
            Repository class
        """
        pass

    @abstractmethod
    def get_create_schema_class(self) -> Type[CreateSchemaType]:
        """Get the Pydantic create schema class.

        Returns:
            Create schema class
        """
        pass

    @abstractmethod
    def get_update_schema_class(self) -> Type[UpdateSchemaType]:
        """Get the Pydantic update schema class.

        Returns:
            Update schema class
        """
        pass

    @abstractmethod
    def serialize(self, model: ModelType) -> dict:
        """Convert model to dictionary.

        Args:
            model: Model instance

        Returns:
            Dictionary representation
        """
        pass

    @abstractmethod
    def get_resource_name(self) -> str:
        """Get the resource name for messages.

        Returns:
            Resource name (e.g., "Feed", "Category")
        """
        pass

    def get_model_type(self) -> str:
        """Get the model type for serialization.

        This method is used by the default serialize() implementation
        to look up the serializer from SerializerRegistry.

        Override this method if your model type differs from the
        resource name.

        Returns:
            Model type identifier for SerializerRegistry

        Example:
            # For feeds, returns "feed"
            # For filter rules, returns "filter_rule"
        """
        # Default implementation: lowercase resource name
        return self.get_resource_name().lower()

    def serialize(self, model: ModelType, **kwargs) -> dict:
        """Convert model to dictionary using SerializerRegistry.

        This default implementation uses the SerializerRegistry.
        Subclasses can override this method to provide custom serialization.

        Args:
            model: Model instance
            **kwargs: Additional arguments to pass to the serializer

        Returns:
            Dictionary representation
        """
        from spider_aggregation.web.serializers import SerializerRegistry

        return SerializerRegistry.serialize(self.get_model_type(), model, **kwargs)

    def validate_create_data(self, data: dict) -> tuple[bool, str]:
        """Validate data before creating a resource.

        Override this method to add custom validation.

        Args:
            data: Request data

        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, ""

    def check_exists(self, repository, data: dict) -> bool:
        """Check if a resource already exists.

        Override this method to add custom existence checks.

        Args:
            repository: Repository instance
            data: Request data

        Returns:
            True if resource exists, False otherwise
        """
        return False

    def _get_repository(self, session):
        """Get a repository instance.

        Args:
            session: SQLAlchemy session

        Returns:
            Repository instance
        """
        return self.get_repository_class()(session)

    def _list(self):
        """List all resources."""
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import api_response

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            items = repo.list(limit=1000)
            data = [self.serialize(item) for item in items]

        return api_response(success=True, data=data)

    def _get_by_id(self, id: int):
        """Get a resource by ID."""
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import api_response

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            item = repo.get_by_id(id)

            if not item:
                resource_name = self.get_resource_name()
                return api_response(
                    success=False,
                    error=f"未找到{resource_name}",
                    status=404
                )

            data = self.serialize(item)

        return api_response(success=True, data=data)

    def _create(self):
        """Create a new resource."""
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
                resource_name = self.get_resource_name()
                return api_response(
                    success=False,
                    error=f"{resource_name}已存在",
                    status=400
                )

            try:
                create_schema = self.get_create_schema_class()
                item_data = create_schema(**data)
                item = repo.create(item_data)
                return api_response(
                    success=True,
                    data=self.serialize(item),
                    message=f"{self.get_resource_name()}创建成功",
                )
            except Exception as e:
                logger.error(f"Error creating {self.get_resource_name()}: {e}")
                return api_response(success=False, error=str(e), status=400)

    def _update(self, id: int):
        """Update a resource."""
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
                resource_name = self.get_resource_name()
                return api_response(
                    success=False,
                    error=f"未找到{resource_name}",
                    status=404
                )

            try:
                update_schema = self.get_update_schema_class()
                item_data = update_schema(**data)
                updated_item = repo.update(item, item_data)
                return api_response(
                    success=True,
                    data=self.serialize(updated_item),
                    message=f"{self.get_resource_name()}更新成功",
                )
            except Exception as e:
                logger.error(f"Error updating {self.get_resource_name()}: {e}")
                return api_response(success=False, error=str(e), status=400)

    def _delete(self, id: int):
        """Delete a resource."""
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import api_response

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            item = repo.get_by_id(id)

            if not item:
                resource_name = self.get_resource_name()
                return api_response(
                    success=False,
                    error=f"未找到{resource_name}",
                    status=404
                )

            repo.delete(item)
            return api_response(
                success=True,
                message=f"{self.get_resource_name()}删除成功",
            )

    def _toggle(self, id: int):
        """Toggle the enabled status of a resource."""
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.web.serializers import api_response

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            item = repo.get_by_id(id)

            if not item:
                resource_name = self.get_resource_name()
                return api_response(
                    success=False,
                    error=f"未找到{resource_name}",
                    status=404
                )

            # Toggle enabled status
            item.enabled = not item.enabled
            session.flush()
            session.refresh(item)

            return api_response(
                success=True,
                data=self.serialize(item),
                message=f"{self.get_resource_name()}状态更新成功",
            )
