"""Repository pattern implementations for data access."""

from spider_aggregation.storage.repositories.entry_repo import EntryRepository
from spider_aggregation.storage.repositories.feed_repo import FeedRepository
from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository

__all__ = [
    "EntryRepository",
    "FeedRepository",
    "FilterRuleRepository",
]
