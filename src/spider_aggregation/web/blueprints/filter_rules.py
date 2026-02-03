"""
Filter Rule API blueprint.

This module contains all filter rule related API endpoints.
"""

from spider_aggregation.web.blueprints.base import CRUDBlueprint
from spider_aggregation.web.serializers import api_response
from spider_aggregation.logger import get_logger
from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository
from spider_aggregation.models.filter_rule import FilterRuleCreate, FilterRuleUpdate


class FilterRuleBlueprint(CRUDBlueprint):
    """Blueprint for filter rule CRUD operations."""

    def __init__(self, db_path: str):
        """Initialize the filter rule blueprint.

        Args:
            db_path: Path to the database file
        """
        super().__init__(db_path, url_prefix="/api/filter-rules")

    def get_repository_class(self):
        """Get the FilterRuleRepository class."""
        return FilterRuleRepository

    def get_create_schema_class(self):
        """Get the FilterRuleCreate schema class."""
        return FilterRuleCreate

    def get_update_schema_class(self):
        """Get the FilterRuleUpdate schema class."""
        return FilterRuleUpdate

    def get_model_type(self) -> str:
        """Get the model type for SerializerRegistry."""
        return "filter_rule"

    def get_resource_name(self) -> str:
        """Get the resource name for messages."""
        return "过滤规则"

    def validate_create_data(self, data: dict) -> tuple[bool, str]:
        """Validate filter rule creation data.

        Args:
            data: Request data

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not data.get("name"):
            return False, "规则名称为必填项"
        if not data.get("rule_type"):
            return False, "规则类型为必填项"
        if not data.get("match_type"):
            return False, "匹配类型为必填项"
        if not data.get("pattern"):
            return False, "匹配模式为必填项"
        return True, ""

    def check_exists(self, repository, data: dict) -> bool:
        """Check if a rule with the same name already exists.

        Args:
            repository: FilterRuleRepository instance
            data: Request data

        Returns:
            True if rule exists, False otherwise
        """
        return repository.get_by_name(data["name"]) is not None
