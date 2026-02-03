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
from spider_aggregation.web.serializers import (
    api_response,
    feed_to_dict,
    entry_to_dict,
    filter_rule_to_dict,
    category_to_dict,
)

logger = get_logger(__name__)

# Global scheduler instance
_scheduler_instance = None
_scheduler_lock = threading.Lock()


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
    # Register API Blueprints
    # ========================================================================

    from spider_aggregation.web.blueprints import (
        FeedBlueprint,
        CategoryBlueprint,
        FilterRuleBlueprint,
        EntryBlueprint,
        SchedulerBlueprint,
        SystemBlueprint,
        set_scheduler,
    )

    # Create blueprints
    feed_bp = FeedBlueprint(db_path).blueprint
    category_bp = CategoryBlueprint(db_path).blueprint
    filter_rule_bp = FilterRuleBlueprint(db_path).blueprint
    entry_bp = EntryBlueprint(db_path).blueprint
    scheduler_bp = SchedulerBlueprint(db_path).blueprint
    system_bp = SystemBlueprint(db_path).blueprint

    # Register blueprints
    app.register_blueprint(feed_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(filter_rule_bp)
    app.register_blueprint(entry_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(system_bp)

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
            feeds = feed_repo.list(limit=1000)
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
    # Additional Entry API Endpoints (not in blueprints)
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
                return api_response(success=False, error="未找到条目", status=404)

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
                return api_response(success=False, error="未找到条目", status=404)

            entry_repo.delete(entry)

        return api_response(success=True, message="条目删除成功")

    # ========================================================================
    # Scheduler Management - Set scheduler instance for blueprints
    # ========================================================================

    @app.before_request
    def initialize_scheduler():
        """Initialize scheduler before first request if needed."""
        global _scheduler_instance

        if _scheduler_instance is None:
            from spider_aggregation.core.scheduler import create_scheduler

            with _scheduler_lock:
                if _scheduler_instance is None:
                    db_manager = DatabaseManager(db_path)
                    try:
                        _scheduler_instance = create_scheduler(
                            session=None, max_workers=3, db_manager=db_manager
                        )
                        # Set scheduler reference for blueprints
                        set_scheduler(_scheduler_instance)
                    except Exception as e:
                        logger.error(f"Failed to initialize scheduler: {e}")

    def get_scheduler_instance():
        """Get the global scheduler instance.

        Returns:
            FeedScheduler instance or None
        """
        return _scheduler_instance

    # Store scheduler getter in app config for blueprints to access
    app.config["get_scheduler"] = get_scheduler_instance

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
