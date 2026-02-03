"""
Filter rule repository for database operations.
"""

from typing import Optional, TYPE_CHECKING

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from sqlalchemy.orm import Query

from spider_aggregation.models.filter_rule import FilterRuleModel, FilterRuleCreate, FilterRuleUpdate
from spider_aggregation.storage.repositories.base import BaseRepository
from spider_aggregation.storage.mixins import FilterQueryMixin


class FilterRuleRepository(
    BaseRepository[FilterRuleModel, FilterRuleCreate, FilterRuleUpdate],
    FilterQueryMixin[FilterRuleModel],
):
    """Repository for FilterRule CRUD operations.

    Inherits common CRUD operations from BaseRepository.
    """

    def __init__(self, session: Session) -> None:
        """Initialize repository with a database session.

        Args:
            session: SQLAlchemy Session instance
        """
        super().__init__(session, FilterRuleModel)

    def get_by_name(self, name: str) -> Optional[FilterRuleModel]:
        """Get a filter rule by name.

        Args:
            name: Filter rule name

        Returns:
            FilterRuleModel instance or None
        """
        return self.session.query(FilterRuleModel).filter(
            FilterRuleModel.name == name
        ).first()

    def _get_complex_filter_keys(self) -> set[str]:
        """Return filter keys that require complex handling."""
        return {"rule_type", "match_type"}

    def _apply_complex_filters(
        self, query, filters: dict
    ) -> "Query[FilterRuleModel]":
        """Apply rule_type and match_type filters."""
        if "rule_type" in filters and filters["rule_type"] is not None:
            query = query.filter(FilterRuleModel.rule_type == filters["rule_type"])
        if "match_type" in filters and filters["match_type"] is not None:
            query = query.filter(FilterRuleModel.match_type == filters["match_type"])
        return query

    def list(
        self,
        enabled_only: bool = False,
        rule_type: Optional[str] = None,
        match_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "priority",
        order_desc: bool = True,
    ) -> list[FilterRuleModel]:
        """List filter rules with optional filtering.

        Args:
            enabled_only: Only return enabled rules
            rule_type: Filter by rule type
            match_type: Filter by match type
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Field to order by
            order_desc: Sort in descending order

        Returns:
            List of FilterRuleModel instances
        """
        # Build filters dict for mixin
        filters = {}
        if enabled_only:
            filters["enabled"] = True
        if rule_type is not None:
            filters["rule_type"] = rule_type
        if match_type is not None:
            filters["match_type"] = match_type

        # Use mixin's list method
        return super().list(
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_desc=order_desc,
            **filters,
        )

    def count(
        self,
        enabled_only: bool = False,
        rule_type: Optional[str] = None,
        match_type: Optional[str] = None,
    ) -> int:
        """Count filter rules.

        Args:
            enabled_only: Only count enabled rules
            rule_type: Filter by rule type
            match_type: Filter by match type

        Returns:
            Number of filter rules
        """
        # Build filters dict for mixin
        filters = {}
        if enabled_only:
            filters["enabled"] = True
        if rule_type is not None:
            filters["rule_type"] = rule_type
        if match_type is not None:
            filters["match_type"] = match_type

        # Use mixin's count method
        return super().count(**filters)

    def get_enabled_rules(self) -> list[FilterRuleModel]:
        """Get all enabled rules ordered by priority (descending).

        Returns:
            List of enabled FilterRuleModel instances
        """
        return (
            self.session.query(FilterRuleModel)
            .filter(FilterRuleModel.enabled == True)
            .order_by(desc(FilterRuleModel.priority))
            .all()
        )

    def delete_by_id(self, rule_id: int) -> bool:
        """Delete a filter rule by ID.

        Args:
            rule_id: Filter rule ID

        Returns:
            True if deleted, False if not found
        """
        rule = self.get_by_id(rule_id)
        if rule:
            self.delete(rule)
            return True
        return False

    def toggle_enabled(self, rule_id: int) -> Optional[FilterRuleModel]:
        """Toggle the enabled status of a filter rule.

        Args:
            rule_id: Filter rule ID

        Returns:
            Updated FilterRuleModel instance or None if not found
        """
        rule = self.get_by_id(rule_id)
        if rule:
            rule.enabled = not rule.enabled
            self.session.flush()
            self.session.refresh(rule)
            return rule
        return None
