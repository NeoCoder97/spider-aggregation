"""Core business logic modules for spider aggregation."""

from spider_aggregation.core.fetcher import (
    FeedFetcher,
    FetchResult,
    FetchStats,
    create_fetcher,
)

__all__ = [
    "FeedFetcher",
    "FetchResult",
    "FetchStats",
    "create_fetcher",
]
