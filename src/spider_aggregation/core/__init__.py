"""Core business logic modules for spider aggregation."""

from spider_aggregation.core.deduplicator import (
    DedupResult,
    DedupStrategy,
    Deduplicator,
    create_deduplicator,
)
from spider_aggregation.core.fetcher import (
    FeedFetcher,
    FetchResult,
    FetchStats,
    create_fetcher,
)
from spider_aggregation.core.parser import (
    ContentParser,
    FeedMetadataParser,
    create_parser,
)
from spider_aggregation.core.scheduler import (
    FeedScheduler,
    JobStatus,
    SchedulerStats,
    create_scheduler,
)

__all__ = [
    "FeedFetcher",
    "FetchResult",
    "FetchStats",
    "create_fetcher",
    "ContentParser",
    "FeedMetadataParser",
    "create_parser",
    "Deduplicator",
    "DedupStrategy",
    "DedupResult",
    "create_deduplicator",
    "FeedScheduler",
    "JobStatus",
    "SchedulerStats",
    "create_scheduler",
]
