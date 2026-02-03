"""
Entry API blueprint.

This module contains all entry-related API endpoints.
"""

from flask import request
from spider_aggregation.web.blueprints.base import CRUDBlueprint
from spider_aggregation.web.serializers import api_response
from spider_aggregation.logger import get_logger
from spider_aggregation.storage.repositories.entry_repo import EntryRepository
from spider_aggregation.storage.repositories.feed_repo import FeedRepository
from spider_aggregation.storage.repositories.category_repo import CategoryRepository
from spider_aggregation.models.entry import EntryCreate, EntryUpdate
from sqlalchemy import func


class EntryBlueprint(CRUDBlueprint):
    """Blueprint for entry CRUD operations.

    Note: Entries are typically created automatically during feed fetching,
    so the create endpoint is not exposed via API.
    """

    def __init__(self, db_path: str):
        """Initialize the entry blueprint.

        Args:
            db_path: Path to the database file
        """
        super().__init__(db_path, url_prefix="/api/entries")
        self._register_custom_routes()

    def _register_custom_routes(self):
        """Register custom entry-specific routes."""
        # Batch delete entries
        self.blueprint.add_url_rule(
            "/batch/delete",
            view_func=self._batch_delete,
            methods=["POST"]
        )
        # Batch fetch content
        self.blueprint.add_url_rule(
            "/batch/fetch-content",
            view_func=self._batch_fetch_content,
            methods=["POST"]
        )
        # Batch extract keywords
        self.blueprint.add_url_rule(
            "/batch/extract-keywords",
            view_func=self._batch_extract_keywords,
            methods=["POST"]
        )
        # Batch summarize
        self.blueprint.add_url_rule(
            "/batch/summarize",
            view_func=self._batch_summarize,
            methods=["POST"]
        )
        # Get entries by category
        self.blueprint.add_url_rule(
            "/by-category/<int:category_id>",
            view_func=self._by_category,
            methods=["GET"]
        )
        # Get entries by category name
        self.blueprint.add_url_rule(
            "/by-category-name/<category_name>",
            view_func=self._by_category_name,
            methods=["GET"]
        )
        # Search within category
        self.blueprint.add_url_rule(
            "/search-by-category/<int:category_id>",
            view_func=self._search_by_category,
            methods=["GET"]
        )
        # Get entry statistics by category
        self.blueprint.add_url_rule(
            "/by-category/<int:category_id>/stats",
            view_func=self._stats_by_category,
            methods=["GET"]
        )

    def get_repository_class(self):
        """Get the EntryRepository class."""
        return EntryRepository

    def get_create_schema_class(self):
        """Get the EntryCreate schema class."""
        return EntryCreate

    def get_update_schema_class(self):
        """Get the EntryUpdate schema class."""
        return EntryUpdate

    def get_model_type(self) -> str:
        """Get the model type for SerializerRegistry."""
        return "entry"

    def get_resource_name(self) -> str:
        """Get the resource name for messages."""
        return "条目"

    def validate_create_data(self, data: dict) -> tuple[bool, str]:
        """Validate entry creation data.

        Note: Entry creation is typically done internally.

        Args:
            data: Request data

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not data.get("feed_id"):
            return False, "feed_id为必填项"
        if not data.get("title"):
            return False, "title为必填项"
        if not data.get("link"):
            return False, "link为必填项"
        return True, ""

    def check_exists(self, repository, data: dict) -> bool:
        """Check if an entry with the same link already exists.

        Args:
            repository: EntryRepository instance
            data: Request data

        Returns:
            True if entry exists, False otherwise
        """
        # For entries, we typically don't check existence before creation
        # as deduplication happens during fetch
        return False

    def _create(self):
        """Override create - entries should not be created via API."""
        return api_response(
            success=False,
            error="条目应通过订阅源获取自动创建",
            status=403
        )

    def _batch_delete(self):
        """Batch delete entries by IDs.

        Request body:
            {"entry_ids": [1, 2, 3, ...]}

        Returns:
            API response with number of deleted entries
        """
        from spider_aggregation.storage.database import DatabaseManager

        data = request.get_json()
        entry_ids = data.get("entry_ids", [])

        if not entry_ids:
            return api_response(success=False, error="entry_ids为必填项", status=400)

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            count = repo.delete_by_ids(entry_ids)

        return api_response(
            success=True,
            data={"deleted_count": count},
            message=f"成功删除 {count} 条条目"
        )

    def _batch_fetch_content(self):
        """Batch fetch full content for entries.

        Request body:
            {"entry_ids": [1, 2, 3, ...]}

        Returns:
            API response with number of entries updated
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.core.services import ContentService

        data = request.get_json()
        entry_ids = data.get("entry_ids", [])

        if not entry_ids:
            return api_response(success=False, error="entry_ids为必填项", status=400)

        db_manager = DatabaseManager(self.db_path)
        content_service = ContentService()
        logger = get_logger(__name__)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            updated_count = 0

            for entry_id in entry_ids:
                try:
                    entry = repo.get_by_id(entry_id)
                    if entry and entry.link:
                        result = content_service.fetch_content(entry.link)
                        if result.success and result.content:
                            # Update entry with fetched content
                            from spider_aggregation.models.entry import EntryUpdate
                            update_data = EntryUpdate(content=result.content)
                            repo.update(entry, update_data)
                            updated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch content for entry {entry_id}: {e}")

        return api_response(
            success=True,
            data={"success": updated_count, "failed": len(entry_ids) - updated_count},
            message=f"成功获取 {updated_count} 条条目的完整内容"
        )

    def _batch_extract_keywords(self):
        """Batch extract keywords for entries.

        Request body:
            {"entry_ids": [1, 2, 3, ...]}

        Returns:
            API response with number of entries updated
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.core.services import KeywordService

        data = request.get_json()
        entry_ids = data.get("entry_ids", [])

        if not entry_ids:
            return api_response(success=False, error="entry_ids为必填项", status=400)

        db_manager = DatabaseManager(self.db_path)
        keyword_service = KeywordService()

        with db_manager.session() as session:
            repo = self._get_repository(session)
            updated_count = 0

            for entry_id in entry_ids:
                entry = repo.get_by_id(entry_id)
                if entry:
                    # Extract keywords from title and content
                    text = f"{entry.title or ''} {entry.content or ''}"
                    keywords = keyword_service.extract(text)

                    if keywords:
                        # Update entry with keywords (store in tags for now)
                        import json
                        from spider_aggregation.models.entry import EntryUpdate
                        update_data = EntryUpdate(tags=keywords)
                        repo.update(entry, update_data)
                        updated_count += 1

        return api_response(
            success=True,
            data={"success": updated_count, "failed": len(entry_ids) - updated_count},
            message=f"成功为 {updated_count} 条条目提取关键词"
        )

    def _batch_summarize(self):
        """Batch summarize entries.

        Request body:
            {"entry_ids": [1, 2, 3, ...]}

        Returns:
            API response with number of entries updated
        """
        from spider_aggregation.storage.database import DatabaseManager
        from spider_aggregation.core.services import SummarizerService

        data = request.get_json()
        entry_ids = data.get("entry_ids", [])

        if not entry_ids:
            return api_response(success=False, error="entry_ids为必填项", status=400)

        db_manager = DatabaseManager(self.db_path)
        summarizer_service = SummarizerService()

        with db_manager.session() as session:
            repo = self._get_repository(session)
            updated_count = 0

            for entry_id in entry_ids:
                entry = repo.get_by_id(entry_id)
                if entry and (entry.content or entry.summary):
                    # Generate summary
                    text = entry.content or entry.summary
                    summary = summarizer_service.summarize(text)

                    if summary:
                        from spider_aggregation.models.entry import EntryUpdate
                        update_data = EntryUpdate(summary=summary)
                        repo.update(entry, update_data)
                        updated_count += 1

        return api_response(
            success=True,
            data={"success": updated_count, "failed": len(entry_ids) - updated_count},
            message=f"成功为 {updated_count} 条条目生成摘要"
        )

    def _by_category(self, category_id: int):
        """Get entries by category ID.

        Args:
            category_id: Category ID

        Query params:
            page: Page number (default: 1)
            page_size: Items per page (default: 20)

        Returns:
            API response with list of entries
        """
        from spider_aggregation.storage.database import DatabaseManager

        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            entries = repo.list_by_category(
                category_id,
                limit=page_size,
                offset=(page - 1) * page_size,
                order_by="published_at",
                order_desc=True,
            )
            total = repo.count_by_category(category_id)
            data = [self.serialize(e) for e in entries]

        return api_response(
            success=True,
            data={
                "entries": data,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )

    def _by_category_name(self, category_name: str):
        """Get entries by category name.

        Args:
            category_name: Category name

        Query params:
            page: Page number (default: 1)
            page_size: Items per page (default: 20)

        Returns:
            API response with list of entries
        """
        from spider_aggregation.storage.database import DatabaseManager

        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            entries = repo.list_by_category_name(
                category_name,
                limit=page_size,
                offset=(page - 1) * page_size,
                order_by="published_at",
                order_desc=True,
            )
            # Note: total count by category name would require a separate query
            data = [self.serialize(e) for e in entries]

        return api_response(
            success=True,
            data={
                "entries": data,
                "page": page,
                "page_size": page_size,
            }
        )

    def _search_by_category(self, category_id: int):
        """Search entries within a category.

        Args:
            category_id: Category ID

        Query params:
            q: Search query
            page: Page number (default: 1)
            page_size: Items per page (default: 20)

        Returns:
            API response with list of matching entries
        """
        from spider_aggregation.storage.database import DatabaseManager

        query = request.args.get("q", "")
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)

        if not query:
            return api_response(success=False, error="搜索关键词为必填项", status=400)

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            repo = self._get_repository(session)
            entries = repo.search_by_category(
                query,
                category_id,
                limit=page_size,
                offset=(page - 1) * page_size,
            )
            data = [self.serialize(e) for e in entries]

        return api_response(
            success=True,
            data={
                "entries": data,
                "query": query,
                "page": page,
                "page_size": page_size,
            }
        )

    def _stats_by_category(self, category_id: int):
        """Get entry statistics for a category.

        Args:
            category_id: Category ID

        Returns:
            API response with category entry statistics
        """
        from spider_aggregation.storage.database import DatabaseManager

        db_manager = DatabaseManager(self.db_path)

        with db_manager.session() as session:
            entry_repo = self._get_repository(session)
            category_repo = CategoryRepository(session)

            # Verify category exists
            category = category_repo.get_by_id(category_id)
            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            stats = entry_repo.get_stats_by_category(category_id)

        return api_response(
            success=True,
            data={
                "category_id": category_id,
                "category_name": category.name,
                **stats
            }
        )
