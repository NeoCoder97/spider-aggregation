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

# Phase 2 exports
from spider_aggregation.core.filter_engine import (
    FilterEngine,
    FilterResult,
    create_filter_engine,
)
from spider_aggregation.core.content_fetcher import (
    ContentFetcher,
    ContentFetchResult,
    create_content_fetcher,
)
from spider_aggregation.core.keyword_extractor import (
    KeywordExtractor,
    create_keyword_extractor,
)
from spider_aggregation.core.summarizer import (
    Summarizer,
    ExtractiveSummarizer,
    AISummarizer,
    SummaryResult,
    create_summarizer,
)

__all__ += [
    "FilterEngine",
    "FilterResult",
    "create_filter_engine",
    "ContentFetcher",
    "ContentFetchResult",
    "create_content_fetcher",
    "KeywordExtractor",
    "create_keyword_extractor",
    "Summarizer",
    "ExtractiveSummarizer",
    "AISummarizer",
    "SummaryResult",
    "create_summarizer",
]
