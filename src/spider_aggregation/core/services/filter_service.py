"""
Facade for content filtering operations.

Provides unified interface for filtering entries based on rules.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from spider_aggregation.logger import get_logger

if TYPE_CHECKING:
    from spider_aggregation.core.filter_engine import FilterResult


@dataclass
class EntryData:
    """Data class for entry filtering.

    This class provides a standardized interface for entry data
    to be used with the FilterEngine, replacing the previous MockEntry.
    """

    title: str = ""
    content: str = ""
    summary: str = ""
    link: str = ""
    tags: list[str] = None
    language: str = ""

    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []

    @classmethod
    def from_dict(cls, data: dict) -> "EntryData":
        """Create EntryData from a dictionary.

        Args:
            data: Dictionary containing entry data

        Returns:
            EntryData instance
        """
        tags = data.get("tags_list", [])
        if isinstance(tags, str):
            import json

            try:
                tags = json.loads(tags)
            except (json.JSONDecodeError, TypeError):
                tags = []

        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
            summary=data.get("summary", ""),
            link=data.get("link", ""),
            tags=tags if tags else [],
            language=data.get("language", ""),
        )

    @classmethod
    def from_model(cls, entry) -> "EntryData":
        """Create EntryData from an EntryModel or similar object.

        Args:
            entry: Entry model instance

        Returns:
            EntryData instance
        """
        tags = getattr(entry, "tags", [])
        if isinstance(tags, str):
            import json

            try:
                tags = json.loads(tags)
            except (json.JSONDecodeError, TypeError):
                tags = []

        return cls(
            title=getattr(entry, "title", ""),
            content=getattr(entry, "content", ""),
            summary=getattr(entry, "summary", ""),
            link=getattr(entry, "link", ""),
            tags=tags if tags else [],
            language=getattr(entry, "language", ""),
        )


class FilterService:
    """Facade for content filtering operations.

    Provides unified interface for filtering entries based on rules.
    """

    def __init__(self, rules: Optional[list] = None):
        """Initialize filter service.

        Args:
            rules: Optional list of FilterRuleModel instances
        """
        from spider_aggregation.core.factories import create_filter_engine

        self._engine = create_filter_engine(rules=rules)
        self._logger = get_logger(__name__)

    def apply(self, parsed_entry: dict, filter_rule_repo) -> "FilterResult":
        """Apply filter rules to an entry.

        Args:
            parsed_entry: Parsed entry data
            filter_rule_repo: FilterRuleRepository instance

        Returns:
            FilterResult indicating if entry is allowed
        """
        from spider_aggregation.core.filter_engine import FilterResult

        # Load rules from repository
        rules = filter_rule_repo.list(enabled_only=True)
        if not rules:
            return FilterResult(passed=True, matched_rules=[])

        # Reload engine with current rules
        self._engine = self._engine.__class__(rules=rules)

        # Create EntryData from parsed entry dictionary
        entry_data = EntryData.from_dict(parsed_entry)
        return self._engine.filter_entry(entry_data)

    def apply_to_model(self, entry, filter_rule_repo) -> "FilterResult":
        """Apply filter rules to an EntryModel instance.

        Args:
            entry: EntryModel instance
            filter_rule_repo: FilterRuleRepository instance

        Returns:
            FilterResult indicating if entry is allowed
        """
        from spider_aggregation.core.filter_engine import FilterResult

        # Load rules from repository
        rules = filter_rule_repo.list(enabled_only=True)
        if not rules:
            return FilterResult(passed=True, matched_rules=[])

        # Reload engine with current rules
        self._engine = self._engine.__class__(rules=rules)

        # Create EntryData from EntryModel
        entry_data = EntryData.from_model(entry)
        return self._engine.filter_entry(entry_data)

    def reload_rules(self, rules: list) -> None:
        """Reload filter rules.

        Args:
            rules: New list of FilterRuleModel instances
        """
        self._engine.reload_rules(rules)


def create_filter_service(rules: Optional[list] = None) -> FilterService:
    """Create a FilterService instance.

    Args:
        rules: Optional list of filter rules

    Returns:
        Configured FilterService
    """
    return FilterService(rules=rules)
