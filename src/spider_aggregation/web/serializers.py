"""
Serializer functions for converting models to dictionaries.

This module provides helper functions for converting SQLAlchemy models
to dictionaries for JSON serialization in API responses.
"""

import json
from datetime import datetime
from typing import Optional, Any


def serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO format string.

    Args:
        dt: Datetime object or None

    Returns:
        ISO format string or None
    """
    return dt.isoformat() if dt else None


def parse_json_tags(tags: Optional[str]) -> list:
    """Parse JSON tags string to list.

    Args:
        tags: JSON string or None

    Returns:
        List of tags
    """
    if tags:
        try:
            return json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


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
        "created_at": serialize_datetime(feed.created_at),
        "updated_at": serialize_datetime(feed.updated_at),
        "last_fetched_at": serialize_datetime(feed.last_fetched_at),
        "fetch_error_count": feed.fetch_error_count,
        "last_error": feed.last_error,
        "last_error_at": serialize_datetime(feed.last_error_at),
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
        "published_at": serialize_datetime(entry.published_at),
        "fetched_at": serialize_datetime(entry.fetched_at),
        "tags": parse_json_tags(entry.tags),
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
        "created_at": serialize_datetime(rule.created_at),
        "updated_at": serialize_datetime(rule.updated_at),
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
        "created_at": serialize_datetime(category.created_at),
        "updated_at": serialize_datetime(category.updated_at),
        "feed_count": feed_count if feed_count is not None else 0,
    }


def api_response(
    success: bool = True,
    data: Any = None,
    message: str = None,
    error: str = None,
    status: int = 200
) -> tuple:
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
    from flask import jsonify

    response_data = {
        "success": success,
        "data": data,
        "message": message,
        "error": error,
    }
    return jsonify(response_data), status


class SerializerRegistry:
    """Centralized registry for model serializers.

    This class provides a single point of control for all model-to-dictionary
    serialization, enabling consistent error handling, logging, and easier
    extension for new serialization formats.

    Usage:
        # Register serializers (typically done at module load)
        SerializerRegistry.register("feed", feed_to_dict)

        # Serialize a model
        data = SerializerRegistry.serialize("feed", feed_model)

        # With additional context
        data = SerializerRegistry.serialize("category", category, feed_count=5)
    """

    _serializers: dict[str, Callable] = {
        "feed": feed_to_dict,
        "entry": entry_to_dict,
        "category": category_to_dict,
        "filter_rule": filter_rule_to_dict,
    }

    @classmethod
    def register(cls, model_type: str, serializer_func: Callable) -> None:
        """Register a new serializer.

        Args:
            model_type: The model type identifier (e.g., "feed", "entry")
            serializer_func: The serialization function

        Raises:
            ValueError: If model_type is already registered

        Example:
            def custom_to_dict(model):
                return {"custom": "data"}

            SerializerRegistry.register("custom", custom_to_dict)
        """
        if model_type in cls._serializers:
            import warnings
            warnings.warn(
                f"Serializer for '{model_type}' is being overwritten. "
                f"Previous serializer: {cls._serializers[model_type].__name__}",
                RuntimeWarning,
                stacklevel=2,
            )
        cls._serializers[model_type] = serializer_func

    @classmethod
    def unregister(cls, model_type: str) -> None:
        """Unregister a serializer.

        Args:
            model_type: The model type identifier to remove
        """
        cls._serializers.pop(model_type, None)

    @classmethod
    def serialize(cls, model_type: str, model: Any, **kwargs) -> dict:
        """Serialize a model using the registered serializer.

        Args:
            model_type: The model type identifier
            model: The model instance to serialize
            **kwargs: Additional arguments to pass to the serializer

        Returns:
            Dictionary representation of the model

        Raises:
            ValueError: If no serializer is registered for the model type

        Example:
            feed_data = SerializerRegistry.serialize("feed", feed_model)
            category_data = SerializerRegistry.serialize(
                "category", category, feed_count=10
            )
        """
        serializer = cls._serializers.get(model_type)
        if not serializer:
            raise ValueError(f"No serializer registered for model type: '{model_type}'")

        try:
            return serializer(model, **kwargs)
        except Exception as e:
            from spider_aggregation.logger import get_logger
            logger = get_logger(__name__)
            logger.error(f"Serialization error for {model_type}: {e}")

            # Return a minimal safe representation on error
            return {
                "id": getattr(model, "id", None),
                "_serialization_error": str(e),
            }

    @classmethod
    def serialize_list(
        cls, model_type: str, models: list[Any], **kwargs
    ) -> list[dict]:
        """Serialize a list of models.

        Args:
            model_type: The model type identifier
            models: List of model instances to serialize
            **kwargs: Additional arguments to pass to each serializer

        Returns:
            List of dictionary representations

        Example:
            feeds_data = SerializerRegistry.serialize_list(
                "feed", [feed1, feed2, feed3]
            )
        """
        return [cls.serialize(model_type, model, **kwargs) for model in models]

    @classmethod
    def get_registered_types(cls) -> set[str]:
        """Get all registered model types.

        Returns:
            Set of registered model type identifiers
        """
        return set(cls._serializers.keys())

    @classmethod
    def has_serializer(cls, model_type: str) -> bool:
        """Check if a serializer is registered for a model type.

        Args:
            model_type: The model type identifier

        Returns:
            True if a serializer is registered, False otherwise
        """
        return model_type in cls._serializers
