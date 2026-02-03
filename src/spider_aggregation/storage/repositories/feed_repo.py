"""
Feed repository for database operations.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from spider_aggregation.models import FeedModel, CategoryModel
from spider_aggregation.models.feed import FeedCreate, FeedUpdate
from spider_aggregation.storage.repositories.base import BaseRepository
from spider_aggregation.storage.repositories.mixins import CategoryQueryMixin
from spider_aggregation.storage.mixins import CategoryRelationshipMixin


class FeedRepository(
    BaseRepository[FeedModel, FeedCreate, FeedUpdate],
    CategoryQueryMixin[FeedModel],
    CategoryRelationshipMixin,
):
    """Repository for Feed CRUD operations.

    Inherits common CRUD operations from BaseRepository and category-based
    query methods from CategoryQueryMixin.
    """

    def __init__(self, session: Session) -> None:
        """Initialize repository with a database session.

        Args:
            session: SQLAlchemy Session instance
        """
        super().__init__(session, FeedModel)

    def get_by_url(self, url: str) -> Optional[FeedModel]:
        """Get a feed by URL.

        Args:
            url: Feed URL

        Returns:
            FeedModel instance or None
        """
        return self.session.query(FeedModel).filter(FeedModel.url == url).first()

    def list(
        self,
        enabled_only: bool = False,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> list[FeedModel]:
        """List feeds with optional filtering.

        Args:
            enabled_only: Only return enabled feeds
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of FeedModel instances
        """
        filters = {}
        if enabled_only:
            filters["enabled"] = True
        return super().list(limit=limit, offset=offset, order_by=order_by, order_desc=order_desc, **filters)

    def count(self, enabled_only: bool = False) -> int:
        """Count feeds.

        Args:
            enabled_only: Only count enabled feeds

        Returns:
            Number of feeds
        """
        filters = {}
        if enabled_only:
            filters["enabled"] = True
        return super().count(**filters)

    def update_fetch_info(
        self,
        feed: FeedModel,
        last_fetched_at: Optional[datetime] = None,
        increment_error: bool = False,
        last_error: Optional[str] = None,
        reset_errors: bool = False,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> FeedModel:
        """Update fetch information for a feed.

        Args:
            feed: FeedModel instance
            last_fetched_at: Last fetch timestamp
            increment_error: Increment error count
            last_error: Last error message
            reset_errors: Reset error count to 0
            etag: ETag from HTTP response
            last_modified: Last-Modified from HTTP response

        Returns:
            Updated FeedModel instance
        """
        if last_fetched_at:
            feed.last_fetched_at = last_fetched_at

        if reset_errors:
            feed.fetch_error_count = 0
            feed.last_error = None
            feed.last_error_at = None
        elif increment_error:
            feed.fetch_error_count += 1
            feed.last_error = last_error
            feed.last_error_at = datetime.utcnow()

        if etag:
            feed.etag = etag

        if last_modified:
            feed.last_modified = last_modified

        feed.updated_at = datetime.utcnow()
        self.session.flush()
        self.session.refresh(feed)
        return feed

    def get_feeds_to_fetch(self, max_feeds: int = 50) -> list[FeedModel]:
        """Get feeds that should be fetched.

        Returns enabled feeds sorted by last fetched time.
        Skips feeds that have exceeded their error threshold.

        Args:
            max_feeds: Maximum number of feeds to return

        Returns:
            List of FeedModel instances
        """
        from spider_aggregation.config import get_config

        config = get_config()

        # Get feeds with error count below threshold
        query = (
            self.session.query(FeedModel)
            .filter(FeedModel.enabled == True)
            .filter(FeedModel.fetch_error_count < config.feed.max_consecutive_errors)
            .order_by(asc(FeedModel.last_fetched_at))
        )

        return query.limit(max_feeds).all()

    def disable_feed(self, feed: FeedModel, reason: Optional[str] = None) -> FeedModel:
        """Disable a feed.

        Args:
            feed: FeedModel instance
            reason: Optional reason for disabling

        Returns:
            Updated FeedModel instance
        """
        feed.enabled = False
        feed.updated_at = datetime.utcnow()

        if reason:
            feed.last_error = reason
            feed.last_error_at = datetime.utcnow()

        self.session.flush()
        self.session.refresh(feed)
        return feed

    def enable_feed(self, feed: FeedModel) -> FeedModel:
        """Enable a feed.

        Args:
            feed: FeedModel instance

        Returns:
            Updated FeedModel instance
        """
        feed.enabled = True
        feed.fetch_error_count = 0
        feed.last_error = None
        feed.last_error_at = None
        feed.updated_at = datetime.utcnow()

        self.session.flush()
        self.session.refresh(feed)
        return feed

    # Category relationship methods (from CategoryRelationshipMixin)

    def get_categories(self, feed: FeedModel) -> list[CategoryModel]:
        """Get all categories for a feed.

        Args:
            feed: FeedModel instance

        Returns:
            List of CategoryModel instances
        """
        # Load categories if not already loaded
        if not feed.categories:
            self.session.refresh(feed)

        return feed.categories

    def set_categories(
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
        # Use mixin method, don't refresh to avoid DetachedInstanceError
        return self.set_categories_for_feed(feed, category_ids, update_timestamp=True, refresh=False)

    def add_category(self, feed: FeedModel, category: CategoryModel) -> None:
        """Add a category to a feed.

        Delegates to CategoryRelationshipMixin.add_category_to_feed().

        Args:
            feed: FeedModel instance
            category: CategoryModel instance
        """
        self.add_category_to_feed(feed, category)

    def remove_category(self, feed: FeedModel, category: CategoryModel) -> None:
        """Remove a category from a feed.

        Delegates to CategoryRelationshipMixin.remove_category_from_feed().

        Args:
            feed: FeedModel instance
            category: CategoryModel instance
        """
        self.remove_category_from_feed(feed, category)

    def clear_categories(self, feed: FeedModel) -> None:
        """Clear all categories from a feed.

        Delegates to CategoryRelationshipMixin.clear_categories_from_feed().

        Args:
            feed: FeedModel instance
        """
        self.clear_categories_from_feed(feed)
