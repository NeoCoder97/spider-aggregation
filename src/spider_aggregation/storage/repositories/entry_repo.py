"""
Entry repository for database operations.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Select, asc, desc, func
from sqlalchemy.orm import Session

from spider_aggregation.models import EntryModel, FeedModel
from spider_aggregation.models.entry import EntryCreate, EntryUpdate


class EntryRepository:
    """Repository for Entry CRUD operations."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with a database session.

        Args:
            session: SQLAlchemy Session instance
        """
        self.session = session

    def create(self, entry_data: EntryCreate) -> EntryModel:
        """Create a new entry.

        Args:
            entry_data: Entry creation data

        Returns:
            Created EntryModel instance
        """
        entry = EntryModel(**entry_data.model_dump())

        # Convert tags list to JSON string if provided
        if hasattr(entry_data, "tags") and entry_data.tags:
            import json

            entry.tags = json.dumps(entry_data.tags)

        self.session.add(entry)
        self.session.flush()
        self.session.refresh(entry)
        return entry

    def get_by_id(self, entry_id: int) -> Optional[EntryModel]:
        """Get an entry by ID.

        Args:
            entry_id: Entry ID

        Returns:
            EntryModel instance or None
        """
        return self.session.query(EntryModel).filter(EntryModel.id == entry_id).first()

    def get_by_link_hash(
        self, link_hash: str, feed_id: Optional[int] = None
    ) -> Optional[EntryModel]:
        """Get an entry by link hash.

        Args:
            link_hash: Hash of the entry link
            feed_id: Optional feed ID to restrict search

        Returns:
            EntryModel instance or None
        """
        query = self.session.query(EntryModel).filter(EntryModel.link_hash == link_hash)
        if feed_id is not None:
            query = query.filter(EntryModel.feed_id == feed_id)
        return query.first()

    def get_by_link_hash_any_feed(
        self, link_hash: str, feed_ids: Optional[list[int]] = None
    ) -> Optional[EntryModel]:
        """Get an entry by link hash across multiple feeds.

        Args:
            link_hash: Hash of the entry link
            feed_ids: Optional list of feed IDs to restrict search

        Returns:
            EntryModel instance or None
        """
        query = self.session.query(EntryModel).filter(EntryModel.link_hash == link_hash)
        if feed_ids:
            query = query.filter(EntryModel.feed_id.in_(feed_ids))
        return query.first()

    def get_by_title_hash(
        self, title_hash: str, feed_id: Optional[int] = None
    ) -> Optional[EntryModel]:
        """Get an entry by title hash.

        Args:
            title_hash: Hash of the entry title
            feed_id: Optional feed ID to restrict search

        Returns:
            EntryModel instance or None
        """
        query = self.session.query(EntryModel).filter(EntryModel.title_hash == title_hash)
        if feed_id is not None:
            query = query.filter(EntryModel.feed_id == feed_id)
        return query.first()

    def get_by_title_hash_any_feed(
        self, title_hash: str, feed_ids: Optional[list[int]] = None
    ) -> Optional[EntryModel]:
        """Get an entry by title hash across multiple feeds.

        Args:
            title_hash: Hash of the entry title
            feed_ids: Optional list of feed IDs to restrict search

        Returns:
            EntryModel instance or None
        """
        query = self.session.query(EntryModel).filter(EntryModel.title_hash == title_hash)
        if feed_ids:
            query = query.filter(EntryModel.feed_id.in_(feed_ids))
        return query.first()

    def get_by_content_hash(
        self, content_hash: str, feed_id: Optional[int] = None
    ) -> Optional[EntryModel]:
        """Get an entry by content hash.

        Args:
            content_hash: Hash of the entry content
            feed_id: Optional feed ID to restrict search

        Returns:
            EntryModel instance or None
        """
        query = self.session.query(EntryModel).filter(EntryModel.content_hash == content_hash)
        if feed_id is not None:
            query = query.filter(EntryModel.feed_id == feed_id)
        return query.first()

    def get_by_title_and_content(
        self, title_hash: str, content_hash: str, feed_id: Optional[int] = None
    ) -> Optional[EntryModel]:
        """Get an entry by matching both title and content hash.

        Args:
            title_hash: Hash of the entry title
            content_hash: Hash of the entry content
            feed_id: Optional feed ID to restrict search

        Returns:
            EntryModel instance or None
        """
        query = self.session.query(EntryModel).filter(
            EntryModel.title_hash == title_hash, EntryModel.content_hash == content_hash
        )
        if feed_id is not None:
            query = query.filter(EntryModel.feed_id == feed_id)
        return query.first()

    def list(
        self,
        feed_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "published_at",
        order_desc: bool = True,
    ) -> list[EntryModel]:
        """List entries with optional filtering.

        Args:
            feed_id: Filter by feed ID
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of EntryModel instances
        """
        query = self.session.query(EntryModel)

        if feed_id is not None:
            query = query.filter(EntryModel.feed_id == feed_id)

        # Apply ordering
        order_column = getattr(EntryModel, order_by, EntryModel.published_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.limit(limit).offset(offset).all()

    def count(self, feed_id: Optional[int] = None) -> int:
        """Count entries.

        Args:
            feed_id: Filter by feed ID

        Returns:
            Number of entries
        """
        query = self.session.query(EntryModel)

        if feed_id is not None:
            query = query.filter(EntryModel.feed_id == feed_id)

        return query.count()

    def update(self, entry: EntryModel, entry_data: EntryUpdate) -> EntryModel:
        """Update an entry.

        Args:
            entry: EntryModel instance to update
            entry_data: Entry update data

        Returns:
            Updated EntryModel instance
        """
        update_data = entry_data.model_dump(exclude_unset=True)

        # Handle tags separately
        if "tags" in update_data:
            import json

            if update_data["tags"] is not None:
                update_data["tags"] = json.dumps(update_data["tags"])

        for field, value in update_data.items():
            setattr(entry, field, value)

        self.session.flush()
        self.session.refresh(entry)
        return entry

    def delete(self, entry: EntryModel) -> None:
        """Delete an entry.

        Args:
            entry: EntryModel instance to delete
        """
        self.session.delete(entry)
        self.session.flush()

    def delete_by_ids(self, entry_ids: list[int]) -> int:
        """Delete entries by IDs in bulk.

        Args:
            entry_ids: List of entry IDs to delete

        Returns:
            Number of entries deleted
        """
        if not entry_ids:
            return 0
        count = (
            self.session.query(EntryModel)
            .filter(EntryModel.id.in_(entry_ids))
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return count

    def delete_by_feed(self, feed_id: int) -> int:
        """Delete all entries for a feed.

        Args:
            feed_id: Feed ID

        Returns:
            Number of entries deleted
        """
        count = (
            self.session.query(EntryModel).filter(EntryModel.feed_id == feed_id).delete()
        )
        self.session.flush()
        return count

    def search(
        self,
        query: str,
        feed_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EntryModel]:
        """Search entries by title or content.

        Args:
            query: Search query string
            feed_id: Optional feed ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching EntryModel instances
        """
        q = self.session.query(EntryModel).filter(
            (EntryModel.title.contains(query)) | (EntryModel.content.contains(query))
        )

        if feed_id is not None:
            q = q.filter(EntryModel.feed_id == feed_id)

        return q.order_by(desc(EntryModel.published_at)).limit(limit).offset(offset).all()

    def get_recent(
        self, feed_id: Optional[int] = None, days: int = 7, limit: int = 100
    ) -> list[EntryModel]:
        """Get recent entries from the last N days.

        Args:
            feed_id: Optional feed ID filter
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of recent EntryModel instances
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        q = (
            self.session.query(EntryModel)
            .filter(EntryModel.published_at >= cutoff)
            .order_by(desc(EntryModel.published_at))
        )

        if feed_id is not None:
            q = q.filter(EntryModel.feed_id == feed_id)

        return q.limit(limit).all()

    def get_stats(self, feed_id: Optional[int] = None) -> dict:
        """Get entry statistics.

        Args:
            feed_id: Optional feed ID filter

        Returns:
            Dictionary with statistics
        """
        q = self.session.query(EntryModel)

        if feed_id is not None:
            q = q.filter(EntryModel.feed_id == feed_id)

        total = q.count()

        # Count by language
        language_counts = (
            self.session.query(EntryModel.language, func.count(EntryModel.id))
            .filter(EntryModel.language.isnot(None))
            .group_by(EntryModel.language)
            .all()
        )

        # Get most recent entry date
        most_recent = (
            q.filter(EntryModel.published_at.isnot(None))
            .order_by(desc(EntryModel.published_at))
            .first()
        )

        return {
            "total": total,
            "language_counts": dict(language_counts) if language_counts else {},
            "most_recent": most_recent.published_at if most_recent else None,
        }

    def cleanup_old_entries(self, days: int = 90, feed_id: Optional[int] = None) -> int:
        """Delete entries older than the specified number of days.

        Args:
            days: Number of days to keep
            feed_id: Optional feed ID filter

        Returns:
            Number of entries deleted
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        q = self.session.query(EntryModel).filter(EntryModel.fetched_at < cutoff)

        if feed_id is not None:
            q = q.filter(EntryModel.feed_id == feed_id)

        count = q.delete()
        self.session.flush()
        return count

    # Category-related methods

    def list_by_category(
        self,
        category_id: int,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "published_at",
        order_desc: bool = True,
    ) -> list[EntryModel]:
        """List entries by category ID (via feed relationship).

        Args:
            category_id: Category ID
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of EntryModel instances
        """
        from spider_aggregation.models import feed_categories

        query = (
            self.session.query(EntryModel)
            .join(FeedModel, EntryModel.feed_id == FeedModel.id)
            .join(feed_categories)
            .filter(feed_categories.c.category_id == category_id)
        )

        # Apply ordering
        order_column = getattr(EntryModel, order_by, EntryModel.published_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.limit(limit).offset(offset).all()

    def list_by_category_name(
        self,
        category_name: str,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "published_at",
        order_desc: bool = True,
    ) -> list[EntryModel]:
        """List entries by category name (via feed relationship).

        Args:
            category_name: Category name
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of EntryModel instances
        """
        from spider_aggregation.models import CategoryModel, feed_categories

        query = (
            self.session.query(EntryModel)
            .join(FeedModel, EntryModel.feed_id == FeedModel.id)
            .join(feed_categories)
            .join(CategoryModel)
            .filter(CategoryModel.name == category_name)
        )

        # Apply ordering
        order_column = getattr(EntryModel, order_by, EntryModel.published_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.limit(limit).offset(offset).all()

    def list_by_categories(
        self,
        category_ids: list[int],
        limit: int = 100,
        offset: int = 0,
        order_by: str = "published_at",
        order_desc: bool = True,
    ) -> list[EntryModel]:
        """List entries by multiple category IDs (entries from feeds in any category).

        Args:
            category_ids: List of category IDs
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of EntryModel instances
        """
        from spider_aggregation.models import feed_categories

        if not category_ids:
            return []

        query = (
            self.session.query(EntryModel)
            .join(FeedModel, EntryModel.feed_id == FeedModel.id)
            .join(feed_categories)
            .filter(feed_categories.c.category_id.in_(category_ids))
        )

        # Apply ordering
        order_column = getattr(EntryModel, order_by, EntryModel.published_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))

        return query.limit(limit).offset(offset).all()

    def count_by_category(self, category_id: int) -> int:
        """Count entries by category ID.

        Args:
            category_id: Category ID

        Returns:
            Number of entries in the category
        """
        from spider_aggregation.models import feed_categories

        return (
            self.session.query(EntryModel)
            .join(FeedModel, EntryModel.feed_id == FeedModel.id)
            .join(feed_categories)
            .filter(feed_categories.c.category_id == category_id)
            .count()
        )

    def search_by_category(
        self,
        query: str,
        category_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EntryModel]:
        """Search entries by title or content within a category.

        Args:
            query: Search query string
            category_id: Category ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching EntryModel instances
        """
        from spider_aggregation.models import feed_categories

        q = (
            self.session.query(EntryModel)
            .join(FeedModel, EntryModel.feed_id == FeedModel.id)
            .join(feed_categories)
            .filter(feed_categories.c.category_id == category_id)
            .filter(
                (EntryModel.title.contains(query)) | (EntryModel.content.contains(query))
            )
        )

        return q.order_by(desc(EntryModel.published_at)).limit(limit).offset(offset).all()

    def get_recent_by_category(
        self, category_id: int, days: int = 7, limit: int = 100
    ) -> list[EntryModel]:
        """Get recent entries from the last N days for a category.

        Args:
            category_id: Category ID
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of recent EntryModel instances
        """
        from datetime import timedelta
        from spider_aggregation.models import feed_categories

        cutoff = datetime.utcnow() - timedelta(days=days)

        q = (
            self.session.query(EntryModel)
            .join(FeedModel, EntryModel.feed_id == FeedModel.id)
            .join(feed_categories)
            .filter(feed_categories.c.category_id == category_id)
            .filter(EntryModel.published_at >= cutoff)
            .order_by(desc(EntryModel.published_at))
        )

        return q.limit(limit).all()

    def get_stats_by_category(self, category_id: int) -> dict:
        """Get entry statistics for a category.

        Args:
            category_id: Category ID

        Returns:
            Dictionary with statistics
        """
        from spider_aggregation.models import feed_categories

        # Build base query
        base_query = (
            self.session.query(EntryModel)
            .join(FeedModel, EntryModel.feed_id == FeedModel.id)
            .join(feed_categories)
            .filter(feed_categories.c.category_id == category_id)
        )

        total = base_query.count()

        # Count by language
        language_counts = (
            base_query.filter(EntryModel.language.isnot(None))
            .with_entities(EntryModel.language, func.count(EntryModel.id))
            .group_by(EntryModel.language)
            .all()
        )

        # Get most recent entry date
        most_recent = (
            base_query.filter(EntryModel.published_at.isnot(None))
            .order_by(desc(EntryModel.published_at))
            .first()
        )

        return {
            "total": total,
            "language_counts": dict(language_counts) if language_counts else {},
            "most_recent": most_recent.published_at if most_recent else None,
        }
