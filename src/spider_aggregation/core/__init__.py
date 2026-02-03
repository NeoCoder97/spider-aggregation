"""Core business logic modules for spider aggregation."""

# Centralized factory functions for consistent dependency injection
from spider_aggregation.core.factories import (
    create_content_fetcher,
    create_deduplicator,
    create_fetcher,
    create_filter_engine,
    create_keyword_extractor,
    create_parser,
    create_scheduler,
    create_summarizer,
)

# Legacy individual factory functions (still available for backward compatibility)
from spider_aggregation.core.deduplicator import (
    DedupResult,
    DedupStrategy,
    Deduplicator,
    create_deduplicator as _legacy_create_deduplicator,
)
from spider_aggregation.core.fetcher import (
    FeedFetcher,
    FetchResult,
    FetchStats,
    create_fetcher as _legacy_create_fetcher,
)
from spider_aggregation.core.parser import (
    ContentParser,
    FeedMetadataParser,
    create_parser as _legacy_create_parser,
)
from spider_aggregation.core.scheduler import (
    FeedScheduler,
    JobStatus,
    SchedulerStats,
    create_scheduler as _legacy_create_scheduler,
)

__all__ = [
    # Factory functions (recommended for creating components)
    "create_fetcher",
    "create_parser",
    "create_deduplicator",
    "create_filter_engine",
    "create_keyword_extractor",
    "create_content_fetcher",
    "create_summarizer",
    "create_scheduler",
    # Core classes
    "FeedFetcher",
    "FetchResult",
    "FetchStats",
    "ContentParser",
    "FeedMetadataParser",
    "Deduplicator",
    "DedupStrategy",
    "DedupResult",
    "FeedScheduler",
    "JobStatus",
    "SchedulerStats",
]

# Phase 2 exports
from spider_aggregation.core.filter_engine import (
    FilterEngine,
    FilterResult,
    create_filter_engine as _legacy_create_filter_engine,
)
from spider_aggregation.core.content_fetcher import (
    ContentFetcher,
    ContentFetchResult,
    create_content_fetcher as _legacy_create_content_fetcher,
)
from spider_aggregation.core.keyword_extractor import (
    KeywordExtractor,
    create_keyword_extractor as _legacy_create_keyword_extractor,
)
from spider_aggregation.core.summarizer import (
    Summarizer,
    ExtractiveSummarizer,
    AISummarizer,
    SummaryResult,
    create_summarizer as _legacy_create_summarizer,
)

__all__ += [
    "FilterEngine",
    "FilterResult",
    "ContentFetcher",
    "ContentFetchResult",
    "KeywordExtractor",
    "Summarizer",
    "ExtractiveSummarizer",
    "AISummarizer",
    "SummaryResult",
]
