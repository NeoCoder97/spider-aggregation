"""
Repository mixins for shared query patterns.

This module provides reusable mixin classes for repositories that need
specialized query patterns beyond the generic BaseRepository operations.

Mixins allow repositories to compose functionality through multiple
inheritance while maintaining the Generic type system for type safety.
"""

from datetime import datetime, timedelta
from typing import TypeVar, Generic, Optional, TYPE_CHECKING, Any, Dict
from sqlalchemy import asc, desc, func

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from sqlalchemy import Select, Query
    from spider_aggregation.models import EntryModel

ModelType = TypeVar("ModelType")


class EntryCategoryQueryMixin(Generic[ModelType]):
    """Mixin for entry category queries via feed relationship.

    This mixin provides methods for querying entries by category through
    the many-to-many feed-categories relationship. It encapsulates the
    common join pattern: Entry -> Feed -> feed_categories -> Category.

    This mixin should be used with repositories that manage Entry-like
    models with a feed_id foreign key.

    Type Args:
        ModelType: The model type (typically EntryModel)
    """

    session: "Session"
    model: type[ModelType]

    def _build_entry_category_query(self, category_id: int) -> "Select[tuple[ModelType]]":
        """Build base query for entry-category filtering via feeds.

        This method encapsulates the common join pattern used across all
        category-based entry queries:

        EntryModel -> FeedModel -> feed_categories -> CategoryModel

        Args:
            category_id: Category ID to filter by

        Returns:
            SQLAlchemy query with joins applied
        """
        from spider_aggregation.models import feed_categories, FeedModel

        return (
            self.session.query(self.model)
            .join(FeedModel, self.model.feed_id == FeedModel.id)
            .join(feed_categories)
            .filter(feed_categories.c.category_id == category_id)
        )

    def _build_entry_category_name_query(self, category_name: str) -> "Select[tuple[ModelType]]":
        """Build base query for entry-category filtering by category name.

        Args:
            category_name: Category name to filter by

        Returns:
            SQLAlchemy query with joins applied
        """
        from spider_aggregation.models import CategoryModel, feed_categories, FeedModel

        return (
            self.session.query(self.model)
            .join(FeedModel, self.model.feed_id == FeedModel.id)
            .join(feed_categories)
            .join(CategoryModel)
            .filter(CategoryModel.name == category_name)
        )

    def _build_entry_categories_query(
        self, category_ids: list[int]
    ) -> Optional["Select[tuple[ModelType]]"]:
        """Build base query for entry filtering by multiple category IDs.

        Args:
            category_ids: List of category IDs to filter by

        Returns:
            SQLAlchemy query with joins applied, or None if category_ids is empty
        """
        from spider_aggregation.models import feed_categories, FeedModel

        if not category_ids:
            return None

        return (
            self.session.query(self.model)
            .join(FeedModel, self.model.feed_id == FeedModel.id)
            .join(feed_categories)
            .filter(feed_categories.c.category_id.in_(category_ids))
        )

    def _apply_ordering(
        self,
        query: "Select[tuple[ModelType]]",
        order_by: str = "published_at",
        order_desc: bool = True,
    ) -> "Select[tuple[ModelType]]":
        """Apply ordering to a query.

        Args:
            query: SQLAlchemy query
            order_by: Field name to order by
            order_desc: True for descending, False for ascending

        Returns:
            Query with ordering applied
        """
        order_column = getattr(self.model, order_by, self.model.published_at)
        if order_desc:
            return query.order_by(desc(order_column))
        else:
            return query.order_by(asc(order_column))

    def list_by_category(
        self,
        category_id: int,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "published_at",
        order_desc: bool = True,
    ) -> list[ModelType]:
        """List entries by category ID (via feed relationship).

        Args:
            category_id: Category ID
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of model instances
        """
        query = self._build_entry_category_query(category_id)
        query = self._apply_ordering(query, order_by, order_desc)
        return query.limit(limit).offset(offset).all()

    def list_by_category_name(
        self,
        category_name: str,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "published_at",
        order_desc: bool = True,
    ) -> list[ModelType]:
        """List entries by category name (via feed relationship).

        Args:
            category_name: Category name
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of model instances
        """
        query = self._build_entry_category_name_query(category_name)
        query = self._apply_ordering(query, order_by, order_desc)
        return query.limit(limit).offset(offset).all()

    def list_by_categories(
        self,
        category_ids: list[int],
        limit: int = 100,
        offset: int = 0,
        order_by: str = "published_at",
        order_desc: bool = True,
    ) -> list[ModelType]:
        """List entries by multiple category IDs (entries from feeds in any category).

        Args:
            category_ids: List of category IDs
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of model instances
        """
        query = self._build_entry_categories_query(category_ids)
        if query is None:
            return []
        query = self._apply_ordering(query, order_by, order_desc)
        return query.limit(limit).offset(offset).all()

    def count_by_category(self, category_id: int) -> int:
        """Count entries by category ID.

        Args:
            category_id: Category ID

        Returns:
            Number of entries in the category
        """
        query = self._build_entry_category_query(category_id)
        return query.count()

    def search_by_category(
        self,
        query: str,
        category_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ModelType]:
        """Search entries by title or content within a category.

        Args:
            query: Search query string
            category_id: Category ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching model instances
        """
        q = self._build_entry_category_query(category_id)
        q = q.filter(
            (self.model.title.contains(query)) | (self.model.content.contains(query))
        )
        return q.order_by(desc(self.model.published_at)).limit(limit).offset(offset).all()

    def get_recent_by_category(
        self, category_id: int, days: int = 7, limit: int = 100
    ) -> list[ModelType]:
        """Get recent entries from the last N days for a category.

        Args:
            category_id: Category ID
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of recent model instances
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = self._build_entry_category_query(category_id)
        q = q.filter(self.model.published_at >= cutoff)
        q = q.order_by(desc(self.model.published_at))
        return q.limit(limit).all()

    def get_stats_by_category(self, category_id: int) -> dict:
        """Get entry statistics for a category.

        Args:
            category_id: Category ID

        Returns:
            Dictionary with statistics:
                - total: Total number of entries
                - language_counts: Dict of language -> count
                - most_recent: Most recent entry's published_at
        """
        base_query = self._build_entry_category_query(category_id)
        total = base_query.count()

        # Count by language
        language_counts = (
            base_query.filter(self.model.language.isnot(None))
            .with_entities(self.model.language, func.count(self.model.id))
            .group_by(self.model.language)
            .all()
        )

        # Get most recent entry date
        most_recent = (
            base_query.filter(self.model.published_at.isnot(None))
            .order_by(desc(self.model.published_at))
            .first()
        )

        return {
            "total": total,
            "language_counts": dict(language_counts) if language_counts else {},
            "most_recent": most_recent.published_at if most_recent else None,
        }


class FilterQueryMixin(Generic[ModelType]):
    """Mixin for repositories with complex filter parameters.

    This mixin provides a pattern for repositories that need to handle
    both simple equality filters (via **kwargs) and complex filter logic
    that cannot be expressed as simple key-value pairs.

    Subclasses should override _apply_complex_filters() to implement
    their specific filter logic.

    Type Args:
        ModelType: The model type (typically FilterRuleModel or similar)
    """

    session: "Session"
    model: type[ModelType]

    def _apply_complex_filters(
        self, query: "Query[ModelType]", filters: Dict[str, Any]
    ) -> "Query[ModelType]":
        """Apply non-equality based filters to a query.

        This method should be overridden in subclasses to implement
        custom filter logic for complex query parameters.

        Args:
            query: SQLAlchemy query
            filters: Dict with filter keys and values

        Returns:
            Query with complex filters applied

        Example override in subclass:
            def _apply_complex_filters(self, query, filters):
                if 'rule_type' in filters and filters['rule_type'] is not None:
                    query = query.filter(self.model.rule_type == filters['rule_type'])
                if 'match_type' in filters and filters['match_type'] is not None:
                    query = query.filter(self.model.match_type == filters['match_type'])
                return query
        """
        # Base implementation does nothing - subclasses override
        return query

    def list(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
        **filters: Any,
    ) -> list[ModelType]:
        """List with complex filter support.

        This method extends the BaseRepository.list() pattern by adding
        support for complex filters through _apply_complex_filters().

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order
            **filters: Additional filter parameters (including complex ones)

        Returns:
            List of model instances
        """
        query = self.session.query(self.model)

        # Apply simple equality filters
        simple_filters = {
            k: v for k, v in filters.items()
            if k not in self._get_complex_filter_keys() and v is not None
        }
        for key, value in simple_filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        # Apply complex filters
        complex_filters = {
            k: v for k, v in filters.items()
            if k in self._get_complex_filter_keys()
        }
        query = self._apply_complex_filters(query, complex_filters)

        # Apply ordering
        order_column = getattr(self.model, order_by, getattr(self.model, "created_at", None))
        if order_column is not None:
            if order_desc:
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))

        return query.limit(limit).offset(offset).all()

    def count(self, **filters: Any) -> int:
        """Count with complex filter support.

        Args:
            **filters: Filter parameters (including complex ones)

        Returns:
            Number of matching records
        """
        query = self.session.query(self.model)

        # Apply simple equality filters
        simple_filters = {
            k: v for k, v in filters.items()
            if k not in self._get_complex_filter_keys() and v is not None
        }
        for key, value in simple_filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        # Apply complex filters
        complex_filters = {
            k: v for k, v in filters.items()
            if k in self._get_complex_filter_keys()
        }
        query = self._apply_complex_filters(query, complex_filters)

        return query.count()

    def _get_complex_filter_keys(self) -> set[str]:
        """Return the set of keys that should be handled by complex filters.

        This method should be overridden in subclasses to specify which
        filter keys require complex filtering logic.

        Returns:
            Set of filter key names
        """
        # Base implementation returns empty set
        return set()


class CategoryRelationshipMixin:
    """Mixin for managing feed-category many-to-many relationships.

    This mixin provides methods for managing the relationship between feeds
    and categories. It can be used by both FeedRepository and CategoryRepository
    to ensure consistent relationship management behavior.

    The mixin handles:
    - Adding a feed to a category (or category to a feed)
    - Removing a feed from a category (or category from a feed)
    - Setting all categories for a feed (replaces existing)
    - Clearing all categories from a feed
    """

    session: "Session"

    def add_category_to_feed(
        self, feed: "FeedModel", category: "CategoryModel", update_timestamp: bool = True
    ) -> None:
        """Add a category to a feed.

        This method adds the bidirectional relationship between a feed and a category.
        It checks for duplicates to prevent the same category being added twice.

        Args:
            feed: FeedModel instance
            category: CategoryModel instance
            update_timestamp: Whether to update feed's updated_at timestamp
        """
        from spider_aggregation.models import FeedModel

        if category not in feed.categories:
            feed.categories.append(category)
            if update_timestamp and hasattr(feed, "updated_at"):
                feed.updated_at = datetime.utcnow()
            self.session.flush()

    def remove_category_from_feed(
        self, feed: "FeedModel", category: "CategoryModel", update_timestamp: bool = True
    ) -> None:
        """Remove a category from a feed.

        This method removes the bidirectional relationship between a feed and a category.

        Args:
            feed: FeedModel instance
            category: CategoryModel instance
            update_timestamp: Whether to update feed's updated_at timestamp
        """
        from spider_aggregation.models import FeedModel

        if category in feed.categories:
            feed.categories.remove(category)
            if update_timestamp and hasattr(feed, "updated_at"):
                feed.updated_at = datetime.utcnow()
            self.session.flush()

    def set_categories_for_feed(
        self,
        feed: "FeedModel",
        category_ids: list[int],
        update_timestamp: bool = True,
        refresh: bool = True,
    ) -> "FeedModel":
        """Set categories for a feed (replaces existing categories).

        This method replaces all existing categories for a feed with the
        specified list of categories.

        Args:
            feed: FeedModel instance
            category_ids: List of category IDs
            update_timestamp: Whether to update feed's updated_at timestamp
            refresh: Whether to refresh the feed object before returning

        Returns:
            Updated FeedModel instance
        """
        from spider_aggregation.models import CategoryModel

        # Fetch all category objects
        categories = (
            self.session.query(CategoryModel)
            .filter(CategoryModel.id.in_(category_ids))
            .all()
        )

        # Replace existing categories
        feed.categories = categories
        if update_timestamp and hasattr(feed, "updated_at"):
            feed.updated_at = datetime.utcnow()
        self.session.flush()

        if refresh:
            self.session.refresh(feed)

        return feed

    def clear_categories_from_feed(
        self, feed: "FeedModel", update_timestamp: bool = True
    ) -> None:
        """Clear all categories from a feed.

        Args:
            feed: FeedModel instance
            update_timestamp: Whether to update feed's updated_at timestamp
        """
        feed.categories = []
        if update_timestamp and hasattr(feed, "updated_at"):
            feed.updated_at = datetime.utcnow()
        self.session.flush()


class JSONFieldMixin(Generic[ModelType]):
    """Mixin for models with JSON fields requiring serialization.

    This mixin provides methods to handle JSON field serialization and
    deserialization, separating data transformation logic from the
    repository's persistence concerns.

    Common use case: Tags stored as JSON strings in database but
    manipulated as lists in application code.

    Type Args:
        ModelType: The model type (typically EntryModel or similar)
    """

    def _serialize_json_field(self, field_name: str, value: Any) -> Optional[str]:
        """Serialize a value to JSON for storage.

        Args:
            field_name: Name of the field (for logging/validation)
            value: Value to serialize (typically a list or dict)

        Returns:
            JSON string or None if value is None/empty

        Example:
            self._serialize_json_field("tags", ["python", "flask"])
            # Returns: '["python", "flask"]'
        """
        if value is None:
            return None
        if isinstance(value, str) and not value:
            return None
        import json

        try:
            return json.dumps(value)
        except (TypeError, ValueError) as e:
            # Log error but don't fail - store as string representation
            import warnings
            warnings.warn(
                f"Failed to serialize {field_name} to JSON: {e}. "
                f"Storing as string representation instead.",
                RuntimeWarning,
                stacklevel=3,
            )
            return str(value)

    def _deserialize_json_field(
        self, field_name: str, default: Any = None
    ) -> Any:
        """Deserialize a JSON field from storage.

        Args:
            field_name: Name of the field to deserialize
            default: Default value if field is None or empty

        Returns:
            Deserialized value (typically list or dict) or default

        Example:
            entry.tags = '["python", "flask"]'
            self._deserialize_json_field("tags", [])
            # Returns: ["python", "flask"]
        """
        value = getattr(self.model, field_name, None)
        if not value:
            return default if default is not None else []
        import json

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # If not valid JSON, return as-is or default
            return default if default is not None else value

    def _serialize_json_fields(
        self, data: dict[str, Any], json_fields: set[str]
    ) -> dict[str, Any]:
        """Serialize multiple JSON fields in a data dict.

        This is useful when preparing data for database operations.

        Args:
            data: Dictionary of field names to values
            json_fields: Set of field names that should be JSON serialized

        Returns:
            Modified dictionary with JSON fields serialized

        Example:
            data = {"title": "...", "tags": ["python", "flask"]}
            self._serialize_json_fields(data, {"tags"})
            # data["tags"] is now: '["python", "flask"]'
        """
        for field_name in json_fields:
            if field_name in data and data[field_name] is not None:
                data[field_name] = self._serialize_json_field(
                    field_name, data[field_name]
                )
        return data

    def get_json_fields(self) -> set[str]:
        """Return the set of field names that should be JSON serialized.

        This method should be overridden in subclasses to specify
        which fields contain JSON data.

        Returns:
            Set of field names that need JSON serialization

        Example override:
            def get_json_fields(self):
                return {"tags", "metadata", "custom_data"}
        """
        # Base implementation returns empty set
        return set()
