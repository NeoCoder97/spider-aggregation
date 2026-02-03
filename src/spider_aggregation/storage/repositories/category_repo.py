"""
Category repository for database operations.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from spider_aggregation.models import CategoryModel
from spider_aggregation.models.category import CategoryCreate, CategoryUpdate
from spider_aggregation.models.feed import FeedModel
from spider_aggregation.storage.repositories.base import BaseRepository
from spider_aggregation.storage.mixins import CategoryRelationshipMixin


class CategoryRepository(
    BaseRepository[CategoryModel, CategoryCreate, CategoryUpdate],
    CategoryRelationshipMixin,
):
    """Repository for Category CRUD operations.

    Inherits common CRUD operations from BaseRepository.
    """

    def __init__(self, session: Session) -> None:
        """Initialize repository with a database session.

        Args:
            session: SQLAlchemy Session instance
        """
        super().__init__(session, CategoryModel)

    def create(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        enabled: bool = True,
    ) -> CategoryModel:
        """Create a new category.

        Args:
            name: Category name (must be unique)
            description: Optional description
            color: Optional hex color code (e.g., #ff5733)
            icon: Optional icon name or class
            enabled: Whether the category is enabled (default: True)

        Returns:
            Created CategoryModel instance
        """
        category = CategoryModel(
            name=name,
            description=description,
            color=color,
            icon=icon,
            enabled=enabled,
        )

        self.session.add(category)
        self.session.flush()
        self.session.refresh(category)
        return category

    def get_by_name(self, name: str) -> Optional[CategoryModel]:
        """Get a category by name.

        Args:
            name: Category name

        Returns:
            CategoryModel instance or None
        """
        return (
            self.session.query(CategoryModel).filter(CategoryModel.name == name).first()
        )

    def list(
        self, enabled_only: bool = False, limit: int = 1000, offset: int = 0
    ) -> list[CategoryModel]:
        """List categories with optional filtering.

        Args:
            enabled_only: Only return enabled categories
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of CategoryModel instances
        """
        filters = {}
        if enabled_only:
            filters["enabled"] = True
        return super().list(limit=limit, offset=offset, order_by="name", order_desc=False, **filters)

    def count(self, enabled_only: bool = False) -> int:
        """Count categories.

        Args:
            enabled_only: Only count enabled categories

        Returns:
            Number of categories
        """
        filters = {}
        if enabled_only:
            filters["enabled"] = True
        return super().count(**filters)

    def update(self, category: CategoryModel, **kwargs) -> CategoryModel:
        """Update a category.

        Args:
            category: CategoryModel instance to update
            **kwargs: Fields to update (name, description, color, icon, enabled)

        Returns:
            Updated CategoryModel instance
        """
        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)

        self.session.flush()
        self.session.refresh(category)
        return category

    def add_feed_to_category(
        self, feed: FeedModel, category: CategoryModel
    ) -> None:
        """Add a feed to a category.

        Delegates to CategoryRelationshipMixin.add_category_to_feed().

        Args:
            feed: FeedModel instance
            category: CategoryModel instance
        """
        # Don't update timestamp when called from CategoryRepository
        self.add_category_to_feed(feed, category, update_timestamp=False)

    def remove_feed_from_category(
        self, feed: FeedModel, category: CategoryModel
    ) -> None:
        """Remove a feed from a category.

        Delegates to CategoryRelationshipMixin.remove_category_from_feed().

        Args:
            feed: FeedModel instance
            category: CategoryModel instance
        """
        # Don't update timestamp when called from CategoryRepository
        self.remove_category_from_feed(feed, category, update_timestamp=False)

    def get_feeds_by_category(
        self,
        category_id: int,
        enabled_only: bool = False,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[FeedModel]:
        """Get all feeds in a category.

        Args:
            category_id: Category ID
            enabled_only: Only return enabled feeds
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of FeedModel instances
        """
        query = (
            self.session.query(FeedModel)
            .join(FeedModel.categories)
            .filter(CategoryModel.id == category_id)
        )

        if enabled_only:
            query = query.filter(FeedModel.enabled == True)

        return query.order_by(desc(FeedModel.created_at)).limit(limit).offset(offset).all()

    def get_feed_count_by_category(self, category_id: int, enabled_only: bool = False) -> int:
        """Count feeds in a category.

        Args:
            category_id: Category ID
            enabled_only: Only count enabled feeds

        Returns:
            Number of feeds in the category
        """
        query = (
            self.session.query(FeedModel)
            .join(FeedModel.categories)
            .filter(CategoryModel.id == category_id)
        )

        if enabled_only:
            query = query.filter(FeedModel.enabled == True)

        return query.count()

    def set_categories_for_feed(
        self, feed: FeedModel, category_ids: list[int]
    ) -> FeedModel:
        """Set categories for a feed (replaces existing categories).

        Delegates to CategoryRelationshipMixin.set_categories_for_feed().

        Args:
            feed: FeedModel instance
            category_ids: List of category IDs

        Returns:
            Updated FeedModel instance
        """
        # Use mixin method, refresh for CategoryRepository usage
        return self.set_categories_for_feed(feed, category_ids, update_timestamp=True, refresh=True)
