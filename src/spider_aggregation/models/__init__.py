"""Data models for spider aggregation."""

from spider_aggregation.models.entry import (
    EntryCreate,
    EntryListResponse,
    EntryModel,
    EntryResponse,
    EntryUpdate,
    FilterRuleModel,
)
from spider_aggregation.models.feed import (
    Base,
    FeedCreate,
    FeedListResponse,
    FeedModel,
    FeedResponse,
    FeedUpdate,
)

__all__ = [
    "Base",
    "FeedModel",
    "FeedCreate",
    "FeedUpdate",
    "FeedResponse",
    "FeedListResponse",
    "EntryModel",
    "EntryCreate",
    "EntryUpdate",
    "EntryResponse",
    "EntryListResponse",
    "FilterRuleModel",
]
