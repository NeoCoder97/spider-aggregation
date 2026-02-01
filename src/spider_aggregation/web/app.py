"""
Flask application for mind-weaver web UI.
"""

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Any

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from markupsafe import Markup
from sqlalchemy import func

from spider_aggregation.config import get_config
from spider_aggregation.logger import get_logger
from spider_aggregation.storage.database import DatabaseManager

logger = get_logger(__name__)

# Global scheduler instance
_scheduler_instance = None
_scheduler_lock = threading.Lock()


# ============================================================================
# Helper Functions
# ============================================================================

def api_response(success=True, data=None, message=None, error=None, status=200):
    """Standard API response format.

    Args:
        success: Whether the request was successful
        data: Response data
        message: Success message
        error: Error message
        status: HTTP status code

    Returns:
        Flask response with JSON data
    """
    response_data = {
        "success": success,
        "data": data,
        "message": message,
        "error": error,
    }
    return jsonify(response_data), status


def feed_to_dict(feed) -> dict:
    """Convert Feed model to dictionary.

    Args:
        feed: FeedModel instance

    Returns:
        Dictionary representation
    """
    return {
        "id": feed.id,
        "url": feed.url,
        "name": feed.name,
        "description": feed.description,
        "enabled": feed.enabled,
        "fetch_interval_minutes": feed.fetch_interval_minutes,
        "max_entries_per_fetch": feed.max_entries_per_fetch,
        "fetch_only_recent": feed.fetch_only_recent,
        "created_at": feed.created_at.isoformat() if feed.created_at else None,
        "updated_at": feed.updated_at.isoformat() if feed.updated_at else None,
        "last_fetched_at": feed.last_fetched_at.isoformat() if feed.last_fetched_at else None,
        "fetch_error_count": feed.fetch_error_count,
        "last_error": feed.last_error,
        "last_error_at": feed.last_error_at.isoformat() if feed.last_error_at else None,
        "categories": [category_to_dict(c) for c in feed.categories] if feed.categories else [],
    }


def entry_to_dict(entry) -> dict:
    """Convert Entry model to dictionary.

    Args:
        entry: EntryModel instance

    Returns:
        Dictionary representation
    """
    return {
        "id": entry.id,
        "feed_id": entry.feed_id,
        "title": entry.title,
        "link": entry.link,
        "author": entry.author,
        "summary": entry.summary,
        "content": entry.content,
        "published_at": entry.published_at.isoformat() if entry.published_at else None,
        "fetched_at": entry.fetched_at.isoformat() if entry.fetched_at else None,
        "tags": json.loads(entry.tags) if entry.tags else [],
        "language": entry.language,
        "reading_time_seconds": entry.reading_time_seconds,
    }


def filter_rule_to_dict(rule) -> dict:
    """Convert FilterRule model to dictionary.

    Args:
        rule: FilterRuleModel instance

    Returns:
        Dictionary representation
    """
    return {
        "id": rule.id,
        "name": rule.name,
        "enabled": rule.enabled,
        "rule_type": rule.rule_type,
        "match_type": rule.match_type,
        "pattern": rule.pattern,
        "priority": rule.priority,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def category_to_dict(category, feed_count: int = None) -> dict:
    """Convert Category model to dictionary.

    Args:
        category: CategoryModel instance
        feed_count: Optional feed count (to avoid lazy loading)

    Returns:
        Dictionary representation
    """
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "icon": category.icon,
        "enabled": category.enabled,
        "created_at": category.created_at.isoformat() if category.created_at else None,
        "updated_at": category.updated_at.isoformat() if category.updated_at else None,
        "feed_count": feed_count if feed_count is not None else 0,
    }


def create_app(
    db_path: Optional[str] = None,
    debug: bool = False,
) -> Flask:
    """Create and configure Flask application.

    Args:
        db_path: Path to database file
        debug: Enable debug mode

    Returns:
        Configured Flask application
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    config = get_config()
    app.config["SECRET_KEY"] = config.web.secret_key
    app.config["DEBUG"] = debug or config.web.debug

    # Custom Jinja2 filters
    def format_datetime(value: Optional[Any], format_str: str = "%Y-%m-%d %H:%M") -> str:
        """Format datetime object or ISO datetime string to China timezone.

        Args:
            value: datetime object, ISO format datetime string, or None
            format_str: strftime format string

        Returns:
            Formatted datetime string in China timezone (UTC+8) or '从未' if None
        """
        if not value:
            return "从未"
        try:
            from datetime import datetime, timezone
            # If already a datetime object, convert to China timezone
            if hasattr(value, 'strftime'):
                dt = value
                # If naive (no timezone), assume UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                # Convert to China timezone (UTC+8)
                china_tz = timezone(timedelta(hours=8))
                dt_china = dt.astimezone(china_tz)
                return dt_china.strftime(format_str)
            # Otherwise parse as ISO string
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            # If naive, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # Convert to China timezone (UTC+8)
            china_tz = timezone(timedelta(hours=8))
            dt_china = dt.astimezone(china_tz)
            return dt_china.strftime(format_str)
        except (ValueError, AttributeError):
            return str(value)

    app.jinja_env.filters["format_datetime"] = format_datetime

    # nl2br filter for converting newlines to <br> tags
    def nl2br(value):
        """Convert newlines to <br> tags.

        Args:
            value: String with newlines

        Returns:
            String with newlines converted to <br> tags
        """
        if value is None:
            return ""
        return Markup(str(value).replace('\n', '<br>\n'))

    app.jinja_env.filters["nl2br"] = nl2br

    # Database path
    if db_path is None:
        db_path = config.database.path

    app.config["DB_PATH"] = db_path

    # Auto-initialize database if it doesn't exist
    db_file = Path(db_path)
    if not db_file.exists():
        logger.info(f"Database not found at {db_path}, initializing...")
        db_file.parent.mkdir(parents=True, exist_ok=True)
        db_manager = DatabaseManager(db_path)
        db_manager.init_db()
        logger.info("Database initialized successfully")

    # ========================================================================
    # Page Routes
    # ========================================================================

    @app.route("/")
    def index():
        """Home page with entry list."""
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)
        feed_id = request.args.get("feed_id", type=int)
        search_query = request.args.get("q", "")

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            entry_repo = EntryRepository(session)
            feed_repo = FeedRepository(session)

            # Get entries
            if search_query:
                entries = entry_repo.search(
                    search_query,
                    feed_id=feed_id,
                    limit=page_size,
                    offset=(page - 1) * page_size,
                )
                total = len(entries)  # Approximate
            else:
                entries = entry_repo.list(
                    feed_id=feed_id,
                    limit=page_size,
                    offset=(page - 1) * page_size,
                    order_by="published_at",
                    order_desc=True,
                )
                total = entry_repo.count(feed_id=feed_id)

            # Get feeds for filter dropdown
            feeds = feed_repo.list(limit=1000)
            # Convert to dicts to avoid DetachedInstanceError
            feeds_data = [feed_to_dict(f) for f in feeds]

            # Parse tags for display and expunge entries from session
            for entry in entries:
                if entry.tags:
                    try:
                        entry.tags_list = json.loads(entry.tags)
                    except (json.JSONDecodeError, TypeError):
                        entry.tags_list = []
                else:
                    entry.tags_list = []
                # Expunge from session so data is preserved after session closes
                session.expunge(entry)

        return render_template(
            "index.html",
            entries=entries,
            feeds=feeds_data,
            page=page,
            page_size=page_size,
            total=total,
            feed_id=feed_id,
            search_query=search_query,
        )

    @app.route("/dashboard")
    def dashboard():
        """Dashboard page with statistics and overview."""
        return render_template("dashboard.html")

    @app.route("/feeds")
    def feeds():
        """Feeds management page."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feeds = feed_repo.list(limit=1000)  # Use list() method, not list(limit=1000)
            # Convert to dicts for JSON serialization in template
            feeds_data = [feed_to_dict(f) for f in feeds]

        return render_template("feeds.html", feeds=feeds_data)

    @app.route("/filter-rules")
    def filter_rules():
        """Filter rules management page."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

            rule_repo = FilterRuleRepository(session)
            rules = rule_repo.list()
            # Convert to dicts for JSON serialization in template
            rules_data = [filter_rule_to_dict(r) for r in rules]

        return render_template("filter_rules.html", rules=rules_data)

    @app.route("/categories")
    def categories():
        """Categories management page."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)
            categories = cat_repo.list()
            # Convert to dicts for JSON serialization in template
            categories_data = [category_to_dict(c) for c in categories]

        return render_template("categories.html", categories=categories_data)

    @app.route("/settings")
    def settings():
        """Settings page."""
        return render_template("settings.html")

    @app.route("/entry/<int:entry_id>")
    def entry_detail(entry_id: int):
        """Entry detail page."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            entry = entry_repo.get_by_id(entry_id)

            if not entry:
                return "Entry not found", 404

            # Parse tags
            if entry.tags:
                try:
                    entry.tags_list = json.loads(entry.tags)
                except (json.JSONDecodeError, TypeError):
                    entry.tags_list = []
            else:
                entry.tags_list = []

            # Expunge from session so it can be accessed after session closes
            session.expunge(entry)

        return render_template("entry.html", entry=entry)

    # ========================================================================
    # Feed Management APIs
    # ========================================================================

    @app.route("/api/feeds", methods=["GET"])
    def api_feeds_list():
        """Get list of all feeds."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feeds = feed_repo.list(limit=1000)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = [feed_to_dict(f) for f in feeds]

        return api_response(
            success=True,
            data=data,
        )

    @app.route("/api/feeds/<int:feed_id>", methods=["GET"])
    def api_feed_detail(feed_id: int):
        """Get feed details."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feed = feed_repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = feed_to_dict(feed)

        return api_response(success=True, data=data)

    @app.route("/api/feeds", methods=["POST"])
    def api_feed_create():
        """Create a new feed."""
        data = request.get_json()

        if not data or not data.get("url"):
            return api_response(success=False, error="订阅源链接为必填项", status=400)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository
            from spider_aggregation.models import FeedCreate

            feed_repo = FeedRepository(session)

            # Check if URL already exists
            if feed_repo.get_by_url(data["url"]):
                return api_response(success=False, error="订阅源链接已存在", status=400)

            try:
                feed_data = FeedCreate(**data)
                feed = feed_repo.create(feed_data)
                return api_response(
                    success=True,
                    data=feed_to_dict(feed),
                    message="Feed created successfully",
                )
            except Exception as e:
                logger.error(f"Error creating feed: {e}")
                return api_response(success=False, error=str(e), status=400)

    @app.route("/api/feeds/<int:feed_id>", methods=["PUT", "POST"])
    def api_feed_update(feed_id: int):
        """Update a feed."""
        data = request.get_json()

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository
            from spider_aggregation.models import FeedUpdate

            feed_repo = FeedRepository(session)
            feed = feed_repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            try:
                feed_data = FeedUpdate(**data)
                updated_feed = feed_repo.update(feed, feed_data)
                return api_response(
                    success=True,
                    data=feed_to_dict(updated_feed),
                    message="订阅源更新成功",
                )
            except Exception as e:
                logger.error(f"Error updating feed: {e}")
                return api_response(success=False, error=str(e), status=400)

    @app.route("/api/feeds/<int:feed_id>", methods=["DELETE"])
    def api_feed_delete(feed_id: int):
        """Delete a feed."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feed = feed_repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            feed_repo.delete(feed)

        return api_response(success=True, message="订阅源删除成功")

    @app.route("/api/feeds/<int:feed_id>/toggle", methods=["PATCH", "POST"])
    def api_feed_toggle(feed_id: int):
        """Toggle feed enabled status."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feed = feed_repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            if feed.enabled:
                feed_repo.disable_feed(feed)
                message = "订阅源已禁用"
            else:
                feed_repo.enable_feed(feed)
                message = "订阅源已启用"

            # Refresh to get updated state
            session.refresh(feed)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = feed_to_dict(feed)

        return api_response(success=True, data=data, message=message)

    @app.route("/api/feeds/<int:feed_id>/fetch", methods=["POST"])
    def api_feed_fetch(feed_id: int):
        """Manually trigger feed fetch."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feed = feed_repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = feed_to_dict(feed)

        # This is a placeholder - actual fetch would be triggered by scheduler
        # For now, just mark as attempted
        return api_response(
            success=True,
            message="已将抓取任务加入队列（请使用调度器或手动抓取）",
            data=data,
        )

    # ========================================================================
    # Entry Management APIs
    # ========================================================================

    @app.route("/api/entries/<int:entry_id>", methods=["GET"])
    def api_entry_detail(entry_id: int):
        """Get entry details."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            entry = entry_repo.get_by_id(entry_id)

            if not entry:
                return api_response(success=False, error="未找到文章", status=404)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = entry_to_dict(entry)

        return api_response(success=True, data=data)

    @app.route("/api/entries/<int:entry_id>", methods=["DELETE"])
    def api_entry_delete(entry_id: int):
        """Delete an entry."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            entry = entry_repo.get_by_id(entry_id)

            if not entry:
                return api_response(success=False, error="未找到文章", status=404)

            entry_repo.delete(entry)

        return api_response(success=True, message="文章删除成功")

    @app.route("/api/entries/batch/delete", methods=["POST", "DELETE"])
    def api_entries_batch_delete():
        """Batch delete entries."""
        data = request.get_json()
        entry_ids = data.get("entry_ids", [])

        if not entry_ids:
            return api_response(success=False, error="未提供文章ID", status=400)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository
            from spider_aggregation.models.entry import EntryModel

            entry_repo = EntryRepository(session)

            # Use bulk delete for better performance
            deleted_count = entry_repo.delete_by_ids(entry_ids)

        return api_response(
            success=True,
            data={"deleted_count": deleted_count},
            message=f"成功删除 {deleted_count} 篇文章",
        )

    @app.route("/api/entries/batch/fetch-content", methods=["POST"])
    def api_entries_batch_fetch_content():
        """Batch fetch content for entries."""
        from spider_aggregation.core import create_content_fetcher
        from spider_aggregation.models import EntryUpdate

        data = request.get_json()
        entry_ids = data.get("entry_ids", [])

        if not entry_ids:
            return api_response(success=False, error="未提供文章ID", status=400)

        fetcher = create_content_fetcher()
        results = {"success": 0, "failed": 0, "errors": []}

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)

            for entry_id in entry_ids:
                entry = entry_repo.get_by_id(entry_id)
                if not entry:
                    results["errors"].append({"entry_id": entry_id, "error": "Not found"})
                    results["failed"] += 1
                    continue

                fetch_result = fetcher.fetch(entry.link)
                if fetch_result.success and fetch_result.content:
                    entry_repo.update(entry, EntryUpdate(content=fetch_result.content))
                    results["success"] += 1
                else:
                    results["errors"].append({
                        "entry_id": entry_id,
                        "error": fetch_result.error or "Failed to fetch"
                    })
                    results["failed"] += 1

        fetcher.close()
        return api_response(
            success=True,
            data=results,
            message=f"已为 {results['success']} 篇文章提取了内容",
        )

    @app.route("/api/entries/batch/extract-keywords", methods=["POST"])
    def api_entries_batch_extract_keywords():
        """Batch extract keywords for entries."""
        from spider_aggregation.core import create_keyword_extractor
        from spider_aggregation.models import EntryUpdate

        data = request.get_json()
        entry_ids = data.get("entry_ids", [])

        if not entry_ids:
            return api_response(success=False, error="未提供文章ID", status=400)

        extractor = create_keyword_extractor()
        results = {"success": 0, "failed": 0, "errors": []}

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)

            for entry_id in entry_ids:
                entry = entry_repo.get_by_id(entry_id)
                if not entry:
                    results["errors"].append({"entry_id": entry_id, "error": "Not found"})
                    results["failed"] += 1
                    continue

                # Use content if available, otherwise summary
                text = entry.content or entry.summary or ""
                keywords = extractor.extract_from_entry(entry.title, text)

                if keywords:
                    entry_repo.update(entry, EntryUpdate(tags=keywords))
                    results["success"] += 1
                else:
                    results["errors"].append({
                        "entry_id": entry_id,
                        "error": "No keywords extracted"
                    })
                    results["failed"] += 1

        return api_response(
            success=True,
            data=results,
            message=f"已为 {results['success']} 篇文章提取了关键词",
        )

    @app.route("/api/entries/batch/summarize", methods=["POST"])
    def api_entries_batch_summarize():
        """Batch generate summaries for entries."""
        from spider_aggregation.core import create_summarizer
        from spider_aggregation.models import EntryUpdate

        data = request.get_json()
        entry_ids = data.get("entry_ids", [])
        method = data.get("method", "extractive")  # extractive or ai

        if not entry_ids:
            return api_response(success=False, error="未提供文章ID", status=400)

        summarizer = create_summarizer(method=method)
        results = {"success": 0, "failed": 0, "errors": []}

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)

            for entry_id in entry_ids:
                entry = entry_repo.get_by_id(entry_id)
                if not entry:
                    results["errors"].append({"entry_id": entry_id, "error": "Not found"})
                    results["failed"] += 1
                    continue

                summary_result = summarizer.summarize_entry(
                    entry.title,
                    entry.content or entry.summary,
                )

                if summary_result.success and summary_result.summary:
                    entry_repo.update(entry, EntryUpdate(summary=summary_result.summary))
                    results["success"] += 1
                else:
                    results["errors"].append({
                        "entry_id": entry_id,
                        "error": summary_result.error or "Failed to summarize"
                    })
                    results["failed"] += 1

        return api_response(
            success=True,
            data=results,
            message=f"已为 {results['success']} 篇文章生成了摘要",
        )

    # ========================================================================
    # Filter Rule Management APIs
    # ========================================================================

    @app.route("/api/filter-rules", methods=["GET"])
    def api_filter_rules_list():
        """Get list of filter rules."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

            rule_repo = FilterRuleRepository(session)
            rules = rule_repo.list()

        return api_response(
            success=True,
            data=[filter_rule_to_dict(r) for r in rules],
        )

    @app.route("/api/filter-rules/<int:rule_id>", methods=["GET"])
    def api_filter_rule_detail(rule_id: int):
        """Get filter rule details."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

            rule_repo = FilterRuleRepository(session)
            rule = rule_repo.get_by_id(rule_id)

            if not rule:
                return api_response(success=False, error="未找到过滤规则", status=404)

        return api_response(success=True, data=filter_rule_to_dict(rule))

    @app.route("/api/filter-rules", methods=["POST"])
    def api_filter_rule_create():
        """Create a new filter rule."""
        data = request.get_json()

        if not data or not data.get("name"):
            return api_response(success=False, error="规则名称为必填项", status=400)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository
            from spider_aggregation.models.entry import FilterRuleCreate

            rule_repo = FilterRuleRepository(session)

            # Check if name already exists
            if rule_repo.get_by_name(data["name"]):
                return api_response(success=False, error="规则名称已存在", status=400)

            try:
                rule_data = FilterRuleCreate(**data)
                rule = rule_repo.create(rule_data)
                return api_response(
                    success=True,
                    data=filter_rule_to_dict(rule),
                    message="过滤规则创建成功",
                )
            except Exception as e:
                logger.error(f"Error creating filter rule: {e}")
                return api_response(success=False, error=str(e), status=400)

    @app.route("/api/filter-rules/<int:rule_id>", methods=["PUT", "POST"])
    def api_filter_rule_update(rule_id: int):
        """Update a filter rule."""
        data = request.get_json()

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository
            from spider_aggregation.models.entry import FilterRuleUpdate

            rule_repo = FilterRuleRepository(session)
            rule = rule_repo.get_by_id(rule_id)

            if not rule:
                return api_response(success=False, error="未找到过滤规则", status=404)

            try:
                rule_data = FilterRuleUpdate(**data)
                updated_rule = rule_repo.update(rule, rule_data)
                return api_response(
                    success=True,
                    data=filter_rule_to_dict(updated_rule),
                    message="过滤规则更新成功",
                )
            except Exception as e:
                logger.error(f"Error updating filter rule: {e}")
                return api_response(success=False, error=str(e), status=400)

    @app.route("/api/filter-rules/<int:rule_id>", methods=["DELETE"])
    def api_filter_rule_delete(rule_id: int):
        """Delete a filter rule."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

            rule_repo = FilterRuleRepository(session)
            rule = rule_repo.get_by_id(rule_id)

            if not rule:
                return api_response(success=False, error="未找到过滤规则", status=404)

            rule_repo.delete(rule)

        return api_response(success=True, message="过滤规则删除成功")

    @app.route("/api/filter-rules/<int:rule_id>/toggle", methods=["PATCH", "POST"])
    def api_filter_rule_toggle(rule_id: int):
        """Toggle filter rule enabled status."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

            rule_repo = FilterRuleRepository(session)
            rule = rule_repo.toggle_enabled(rule_id)

            if not rule:
                return api_response(success=False, error="未找到过滤规则", status=404)

            message = "规则已启用" if rule.enabled else "规则已禁用"

        return api_response(success=True, data=filter_rule_to_dict(rule), message=message)

    # ========================================================================
    # Category Management APIs
    # ========================================================================

    @app.route("/api/categories", methods=["GET"])
    def api_categories_list():
        """Get list of all categories."""
        enabled_only = request.args.get("enabled_only", False, type=bool)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)
            categories = cat_repo.list(enabled_only=enabled_only)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = [category_to_dict(c) for c in categories]

        return api_response(success=True, data=data)

    @app.route("/api/categories/<int:category_id>", methods=["GET"])
    def api_category_detail(category_id: int):
        """Get category details."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)
            category = cat_repo.get_by_id(category_id)

            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = category_to_dict(category)

        return api_response(success=True, data=data)

    @app.route("/api/categories", methods=["POST"])
    def api_category_create():
        """Create a new category."""
        data = request.get_json()

        if not data or not data.get("name"):
            return api_response(success=False, error="分类名称为必填项", status=400)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)

            # Check if name already exists
            if cat_repo.get_by_name(data["name"]):
                return api_response(success=False, error="分类名称已存在", status=400)

            try:
                category = cat_repo.create(
                    name=data["name"],
                    description=data.get("description"),
                    color=data.get("color"),
                    icon=data.get("icon"),
                    enabled=data.get("enabled", True),
                )
                return api_response(
                    success=True,
                    data=category_to_dict(category),
                    message="分类创建成功",
                )
            except Exception as e:
                logger.error(f"Error creating category: {e}")
                return api_response(success=False, error=str(e), status=400)

    @app.route("/api/categories/<int:category_id>", methods=["PUT", "POST"])
    def api_category_update(category_id: int):
        """Update a category."""
        data = request.get_json()

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)
            category = cat_repo.get_by_id(category_id)

            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            try:
                # Build update kwargs from provided fields
                update_kwargs = {}
                if "name" in data:
                    update_kwargs["name"] = data["name"]
                if "description" in data:
                    update_kwargs["description"] = data["description"]
                if "color" in data:
                    update_kwargs["color"] = data["color"]
                if "icon" in data:
                    update_kwargs["icon"] = data["icon"]
                if "enabled" in data:
                    update_kwargs["enabled"] = data["enabled"]

                updated_category = cat_repo.update(category, **update_kwargs)
                return api_response(
                    success=True,
                    data=category_to_dict(updated_category),
                    message="分类更新成功",
                )
            except Exception as e:
                logger.error(f"Error updating category: {e}")
                return api_response(success=False, error=str(e), status=400)

    @app.route("/api/categories/<int:category_id>", methods=["DELETE"])
    def api_category_delete(category_id: int):
        """Delete a category."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)
            category = cat_repo.get_by_id(category_id)

            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            cat_repo.delete(category)

        return api_response(success=True, message="分类删除成功")

    @app.route("/api/categories/<int:category_id>/toggle", methods=["PATCH", "POST"])
    def api_category_toggle(category_id: int):
        """Toggle category enabled status."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)
            category = cat_repo.get_by_id(category_id)

            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            # Toggle enabled status
            new_status = not category.enabled
            cat_repo.update(category, enabled=new_status)

            # Refresh to get updated state
            session.refresh(category)

            message = "分类已启用" if new_status else "分类已禁用"

            # Convert to dict inside session to avoid DetachedInstanceError
            data = category_to_dict(category)

        return api_response(success=True, data=data, message=message)

    @app.route("/api/categories/<int:category_id>/feeds", methods=["GET"])
    def api_category_feeds(category_id: int):
        """Get feeds in a category."""
        enabled_only = request.args.get("enabled_only", False, type=bool)
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)
            category = cat_repo.get_by_id(category_id)

            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            feeds = cat_repo.get_feeds_by_category(
                category_id, enabled_only=enabled_only, limit=limit, offset=offset
            )
            total = cat_repo.get_feed_count_by_category(category_id, enabled_only=enabled_only)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = [feed_to_dict(f) for f in feeds]

        return api_response(
            success=True,
            data={"feeds": data, "total": total, "limit": limit, "offset": offset},
        )

    @app.route("/api/categories/stats", methods=["GET"])
    def api_categories_stats():
        """Get category statistics."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            cat_repo = CategoryRepository(session)

            stats = {
                "total": cat_repo.count(),
                "enabled": cat_repo.count(enabled_only=True),
            }

        return api_response(success=True, data=stats)

    # ========================================================================
    # Feed-Category Relationship APIs
    # ========================================================================

    @app.route("/api/feeds/<int:feed_id>/categories", methods=["GET"])
    def api_feed_categories(feed_id: int):
        """Get categories for a feed."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feed = feed_repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            categories = feed_repo.get_categories(feed)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = [category_to_dict(c) for c in categories]

        return api_response(success=True, data=data)

    @app.route("/api/feeds/<int:feed_id>/categories", methods=["PUT", "POST"])
    def api_feed_set_categories(feed_id: int):
        """Set categories for a feed (replaces existing categories)."""
        data = request.get_json()
        category_ids = data.get("category_ids", [])

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository
            from spider_aggregation.models import CategoryModel, feed_categories

            feed_repo = FeedRepository(session)
            cat_repo = CategoryRepository(session)
            feed = feed_repo.get_by_id(feed_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)

            try:
                feed_repo.set_categories(feed, category_ids)

                # Query individual columns instead of ORM objects to avoid DetachedInstanceError
                category_rows = (
                    session.query(
                        CategoryModel.id,
                        CategoryModel.name,
                        CategoryModel.description,
                        CategoryModel.color,
                        CategoryModel.icon,
                        CategoryModel.enabled,
                        CategoryModel.created_at,
                        CategoryModel.updated_at,
                        func.count(feed_categories.c.feed_id).label('feed_count')
                    )
                    .join(feed_categories, CategoryModel.id == feed_categories.c.category_id)
                    .filter(feed_categories.c.feed_id == feed_id)
                    .group_by(
                        CategoryModel.id,
                        CategoryModel.name,
                        CategoryModel.description,
                        CategoryModel.color,
                        CategoryModel.icon,
                        CategoryModel.enabled,
                        CategoryModel.created_at,
                        CategoryModel.updated_at,
                    )
                    .all()
                )

                # Convert raw row data to dict
                data = []
                for row in category_rows:
                    data.append({
                        "id": row.id,
                        "name": row.name,
                        "description": row.description,
                        "color": row.color,
                        "icon": row.icon,
                        "enabled": row.enabled,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                        "feed_count": row.feed_count,
                    })

                return api_response(
                    success=True,
                    data=data,
                    message=f"已设置 {len(data)} 个分类",
                )
            except Exception as e:
                logger.error(f"Error setting feed categories: {e}")
                import traceback
                traceback.print_exc()
                return api_response(success=False, error=str(e), status=400)

    @app.route("/api/feeds/<int:feed_id>/categories/<int:category_id>", methods=["PUT", "POST"])
    def api_feed_add_category(feed_id: int, category_id: int):
        """Add a category to a feed."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            feed_repo = FeedRepository(session)
            cat_repo = CategoryRepository(session)

            feed = feed_repo.get_by_id(feed_id)
            category = cat_repo.get_by_id(category_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)
            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            try:
                feed_repo.add_category(feed, category)
                categories = feed_repo.get_categories(feed)

                # Convert to dict inside session to avoid DetachedInstanceError
                data = [category_to_dict(c) for c in categories]

                return api_response(
                    success=True,
                    data=data,
                    message="分类添加成功",
                )
            except Exception as e:
                logger.error(f"Error adding category to feed: {e}")
                return api_response(success=False, error=str(e), status=400)

    @app.route("/api/feeds/<int:feed_id>/categories/<int:category_id>", methods=["DELETE"])
    def api_feed_remove_category(feed_id: int, category_id: int):
        """Remove a category from a feed."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository
            from spider_aggregation.storage.repositories.category_repo import CategoryRepository

            feed_repo = FeedRepository(session)
            cat_repo = CategoryRepository(session)

            feed = feed_repo.get_by_id(feed_id)
            category = cat_repo.get_by_id(category_id)

            if not feed:
                return api_response(success=False, error="未找到订阅源", status=404)
            if not category:
                return api_response(success=False, error="未找到分类", status=404)

            try:
                feed_repo.remove_category(feed, category)
                categories = feed_repo.get_categories(feed)

                # Convert to dict inside session to avoid DetachedInstanceError
                data = [category_to_dict(c) for c in categories]

                return api_response(
                    success=True,
                    data=data,
                    message="分类移除成功",
                )
            except Exception as e:
                logger.error(f"Error removing category from feed: {e}")
                return api_response(success=False, error=str(e), status=400)

    # ========================================================================
    # Entry-Category Filtering APIs
    # ========================================================================

    @app.route("/api/entries/by-category/<int:category_id>", methods=["GET"])
    def api_entries_by_category(category_id: int):
        """Get entries by category ID."""
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        order_by = request.args.get("order_by", "published_at", type=str)
        order_desc = request.args.get("order_desc", True, type=bool)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            entries = entry_repo.list_by_category(
                category_id=category_id,
                limit=limit,
                offset=offset,
                order_by=order_by,
                order_desc=order_desc,
            )
            total = entry_repo.count_by_category(category_id)

            # Parse tags and expunge entries from session
            for entry in entries:
                if entry.tags:
                    try:
                        entry.tags_list = json.loads(entry.tags)
                    except (json.JSONDecodeError, TypeError):
                        entry.tags_list = []
                else:
                    entry.tags_list = []
                session.expunge(entry)

        return api_response(
            success=True,
            data={"entries": [entry_to_dict(e) for e in entries], "total": total},
        )

    @app.route("/api/entries/by-category-name/<category_name>", methods=["GET"])
    def api_entries_by_category_name(category_name: str):
        """Get entries by category name."""
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            entries = entry_repo.list_by_category_name(
                category_name=category_name,
                limit=limit,
                offset=offset,
            )

            # Parse tags and expunge entries from session
            for entry in entries:
                if entry.tags:
                    try:
                        entry.tags_list = json.loads(entry.tags)
                    except (json.JSONDecodeError, TypeError):
                        entry.tags_list = []
                else:
                    entry.tags_list = []
                session.expunge(entry)

        return api_response(
            success=True,
            data={"entries": [entry_to_dict(e) for e in entries]},
        )

    @app.route("/api/entries/search-by-category/<int:category_id>", methods=["GET"])
    def api_entries_search_by_category(category_id: int):
        """Search entries within a category."""
        query = request.args.get("q", "")
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)

        if not query:
            return api_response(success=False, error="请提供搜索关键词", status=400)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            entries = entry_repo.search_by_category(
                query=query,
                category_id=category_id,
                limit=limit,
                offset=offset,
            )

            # Parse tags and expunge entries from session
            for entry in entries:
                if entry.tags:
                    try:
                        entry.tags_list = json.loads(entry.tags)
                    except (json.JSONDecodeError, TypeError):
                        entry.tags_list = []
                else:
                    entry.tags_list = []
                session.expunge(entry)

        return api_response(
            success=True,
            data={"entries": [entry_to_dict(e) for e in entries], "query": query},
        )

    @app.route("/api/categories/<int:category_id>/entries/stats", methods=["GET"])
    def api_category_entries_stats(category_id: int):
        """Get entry statistics for a category."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            stats = entry_repo.get_stats_by_category(category_id)

        return api_response(success=True, data=stats)

    # ========================================================================
    # Dashboard & Statistics APIs
    # ========================================================================

    @app.route("/api/stats")
    def api_stats():
        """API endpoint for statistics."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository
            from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

            entry_repo = EntryRepository(session)
            feed_repo = FeedRepository(session)
            rule_repo = FilterRuleRepository(session)

            entry_stats = entry_repo.get_stats()
            feed_count = feed_repo.count()
            rule_count = rule_repo.count()

            stats = {
                "total_entries": entry_stats["total"],
                "total_feeds": feed_count,
                "total_rules": rule_count,
                "language_counts": entry_stats["language_counts"],
                "most_recent": entry_stats["most_recent"].isoformat()
                if entry_stats["most_recent"]
                else None,
            }

        return jsonify(stats)

    @app.route("/api/dashboard/activity", methods=["GET"])
    def api_dashboard_activity():
        """Get recent activity for dashboard."""
        limit = request.args.get("limit", 10, type=int)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            entries = entry_repo.list(
                limit=limit,
                order_by="fetched_at",
                order_desc=True,
            )

            # Convert to dict inside session to avoid DetachedInstanceError
            data = [entry_to_dict(e) for e in entries]

        return api_response(
            success=True,
            data=data,
        )

    @app.route("/api/dashboard/feed-health", methods=["GET"])
    def api_dashboard_feed_health():
        """Get feed health status for dashboard."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feeds = feed_repo.list(limit=1000)

            health_data = []
            for feed in feeds:
                health_data.append({
                    "id": feed.id,
                    "name": feed.name or feed.url,
                    "enabled": feed.enabled,
                    "error_count": feed.fetch_error_count,
                    "last_fetched": feed.last_fetched_at.isoformat() if feed.last_fetched_at else None,
                    "has_error": bool(feed.last_error),
                })

        return api_response(success=True, data=health_data)

    # ========================================================================
    # Scheduler Management APIs
    # ========================================================================

    @app.route("/api/scheduler/status", methods=["GET"])
    def api_scheduler_status():
        """Get scheduler status."""
        global _scheduler_instance

        with _scheduler_lock:
            is_running = _scheduler_instance is not None and _scheduler_instance.is_running()

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feeds = [f for f in feed_repo.list() if f.enabled]

            # Convert to dict inside session to avoid DetachedInstanceError
            status = {
                "is_running": is_running,
                "enabled_feeds_count": len(feeds),
                "feeds": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "interval_minutes": f.fetch_interval_minutes,
                    }
                    for f in feeds
                ],
            }

        return api_response(success=True, data=status)

    @app.route("/api/scheduler/start", methods=["POST"])
    def api_scheduler_start():
        """Start the scheduler."""
        global _scheduler_instance

        with _scheduler_lock:
            if _scheduler_instance is not None and _scheduler_instance.is_running():
                return api_response(success=False, error="调度器正在运行", status=400)

            try:
                from spider_aggregation.core import create_scheduler

                db_manager = DatabaseManager(db_path)
                _scheduler_instance = create_scheduler(
                    session=None, max_workers=3, db_manager=db_manager
                )
                _scheduler_instance.start()

                # Add jobs for all enabled feeds
                with db_manager.session() as session:
                    from spider_aggregation.storage.repositories.feed_repo import FeedRepository

                    feed_repo = FeedRepository(session)
                    feeds = [f for f in feed_repo.list() if f.enabled]

                    for feed in feeds:
                        _scheduler_instance.add_feed_job(
                            feed_id=feed.id,
                            interval_minutes=feed.fetch_interval_minutes,
                        )

                logger.info("Scheduler started via Web UI")
                return api_response(success=True, message="调度器已启动")

            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
                return api_response(success=False, error=str(e), status=500)

    @app.route("/api/scheduler/stop", methods=["POST"])
    def api_scheduler_stop():
        """Stop the scheduler."""
        global _scheduler_instance

        with _scheduler_lock:
            if _scheduler_instance is None or not _scheduler_instance.is_running():
                return api_response(success=False, error="调度器未运行", status=400)

            try:
                _scheduler_instance.stop(wait=True)
                _scheduler_instance = None

                logger.info("Scheduler stopped via Web UI")
                return api_response(success=True, message="调度器已停止")

            except Exception as e:
                logger.error(f"Failed to stop scheduler: {e}")
                return api_response(success=False, error=str(e), status=500)

    @app.route("/api/scheduler/fetch-all", methods=["POST"])
    def api_scheduler_fetch_all():
        """Manually trigger fetch for all enabled feeds."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository
            from spider_aggregation.core import create_fetcher, create_parser, create_deduplicator
            from spider_aggregation.models.entry import EntryCreate

            feed_repo = FeedRepository(session)
            entry_repo = EntryRepository(session)

            feeds_to_fetch = [f for f in feed_repo.list() if f.enabled]

            if not feeds_to_fetch:
                return api_response(success=False, error="未找到启用的订阅源", status=400)

            fetcher = create_fetcher(session=session)
            parser = create_parser()
            dedup = create_deduplicator(session=session, strategy="medium")

            total_created = 0
            total_skipped = 0
            results = []

            for feed in feeds_to_fetch:
                result = fetcher.fetch_feed(feed)

                if not result.success:
                    results.append({
                        "feed_id": feed.id,
                        "feed_name": feed.name,
                        "success": False,
                        "error": result.error,
                    })
                    continue

                created = 0
                skipped = 0

                for raw_entry in result.entries:
                    parsed = parser.parse_entry(raw_entry)

                    dup_result = dedup.check_duplicate(parsed, feed_id=feed.id)
                    if dup_result.is_duplicate:
                        skipped += 1
                        continue

                    hashes = dedup.compute_hashes(parsed)

                    entry_data = EntryCreate(
                        feed_id=feed.id,
                        title=parsed["title"] or "",
                        link=parsed["link"] or "",
                        author=parsed.get("author"),
                        summary=parsed.get("summary"),
                        content=parsed.get("content"),
                        published_at=parsed.get("published_at"),
                        title_hash=hashes["title_hash"],
                        link_hash=hashes["link_hash"],
                        content_hash=hashes["content_hash"],
                        tags=parsed.get("tags"),
                        language=parsed.get("language"),
                        reading_time_seconds=parsed.get("reading_time_seconds"),
                    )

                    entry_repo.create(entry_data)
                    created += 1

                total_created += created
                total_skipped += skipped

                results.append({
                    "feed_id": feed.id,
                    "feed_name": feed.name,
                    "success": True,
                    "entries_count": result.entries_count,
                    "created": created,
                    "skipped": skipped,
                })

        return api_response(
            success=True,
            data={
                "total_created": total_created,
                "total_skipped": total_skipped,
                "results": results,
            },
            message=f"Fetched {len(feeds_to_fetch)} feeds: {total_created} new, {total_skipped} skipped",
        )

    # ========================================================================
    # System Management APIs
    # ========================================================================

    @app.route("/api/system/cleanup", methods=["POST"])
    def api_system_cleanup():
        """Clean up old entries."""
        data = request.get_json()
        days = data.get("days", 90)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            deleted_count = entry_repo.cleanup_old_entries(days=days)

        return api_response(
            success=True,
            data={"deleted_count": deleted_count},
            message=f"已清理 {deleted_count} 篇旧文章",
        )

    @app.route("/api/system/export/entries", methods=["GET"])
    def api_export_entries():
        """Export entries as JSON."""
        feed_id = request.args.get("feed_id", type=int)
        limit = request.args.get("limit", 1000, type=int)

        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.entry_repo import EntryRepository

            entry_repo = EntryRepository(session)
            entries = entry_repo.list(
                feed_id=feed_id,
                limit=limit,
                order_by="published_at",
                order_desc=True,
            )

            # Convert to dict inside session to avoid DetachedInstanceError
            data = [entry_to_dict(e) for e in entries]

        response = jsonify(data)
        response.headers["Content-Disposition"] = "attachment; filename=entries.json"
        response.headers["Content-Type"] = "application/json"
        return response

    @app.route("/api/system/export/feeds", methods=["GET"])
    def api_export_feeds():
        """Export feeds as JSON."""
        db_manager = DatabaseManager(db_path)

        with db_manager.session() as session:
            from spider_aggregation.storage.repositories.feed_repo import FeedRepository

            feed_repo = FeedRepository(session)
            feeds = feed_repo.list(limit=1000)

            # Convert to dict inside session to avoid DetachedInstanceError
            data = [feed_to_dict(f) for f in feeds]

        response = jsonify(data)
        response.headers["Content-Disposition"] = "attachment; filename=feeds.json"
        response.headers["Content-Type"] = "application/json"
        return response

    # ========================================================================
    # Error Handlers
    # ========================================================================

    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors."""
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 errors."""
        logger.error(f"Server error: {e}")
        return render_template("500.html"), 500

    logger.info(f"Web app created with database: {db_path}")

    return app
