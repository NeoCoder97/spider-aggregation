"""
Entry repository for database operations.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from spider_aggregation.models import EntryModel, FeedModel
from spider_aggregation.models.entry import EntryCreate, EntryUpdate
from spider_aggregation.storage.repositories.base import BaseRepository
from spider_aggregation.storage.mixins import EntryCategoryQueryMixin, JSONFieldMixin


class EntryRepository(
    BaseRepository[EntryModel, EntryCreate, EntryUpdate],
    EntryCategoryQueryMixin[EntryModel],
    JSONFieldMixin[EntryModel],
):
    """Repository for Entry CRUD operations.

    Inherits common CRUD operations from BaseRepository.
    """

    def __init__(self, session: Session) -> None:
        """Initialize repository with a database session.

        Args:
            session: SQLAlchemy Session instance
        """
        super().__init__(session, EntryModel)

    def get_json_fields(self) -> set[str]:
        """Return JSON field names for EntryModel."""
        return {"tags"}

    def create(self, entry_data: EntryCreate) -> EntryModel:
        """Create a new entry.

        Args:
            entry_data: Entry creation data

        Returns:
            Created EntryModel instance
        """
        # Convert data dict and handle JSON fields
        data_dict = entry_data.model_dump()
        data_dict = self._serialize_json_fields(data_dict, self.get_json_fields())

        entry = EntryModel(**data_dict)
        self.session.add(entry)
        self.session.flush()
        self.session.refresh(entry)
        return entry

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
        filters = {}
        if feed_id is not None:
            filters["feed_id"] = feed_id
        return super().list(limit=limit, offset=offset, order_by=order_by, order_desc=order_desc, **filters)

    def count(self, feed_id: Optional[int] = None) -> int:
        """Count entries.

        Args:
            feed_id: Filter by feed ID

        Returns:
            Number of entries
        """
        filters = {}
        if feed_id is not None:
            filters["feed_id"] = feed_id
        return super().count(**filters)

    def update(self, entry: EntryModel, entry_data: EntryUpdate) -> EntryModel:
        """Update an entry.

        Args:
            entry: EntryModel instance to update
            entry_data: Entry update data

        Returns:
            Updated EntryModel instance
        """
        update_data = entry_data.model_dump(exclude_unset=True)

        # Handle JSON fields using mixin
        update_data = self._serialize_json_fields(update_data, self.get_json_fields())

        for field, value in update_data.items():
            setattr(entry, field, value)

        self.session.flush()
        self.session.refresh(entry)
        return entry

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
        cutoff = datetime.utcnow() - timedelta(days=days)

        q = self.session.query(EntryModel).filter(EntryModel.fetched_at < cutoff)

        if feed_id is not None:
            q = q.filter(EntryModel.feed_id == feed_id)

        count = q.delete()
        self.session.flush()
        return count

    # Category-related methods are now provided by EntryCategoryQueryMixin
