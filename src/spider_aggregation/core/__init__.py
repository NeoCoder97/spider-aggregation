"""Core business logic modules for spider aggregation.

IMPORTANT: Module Boundary Rules
=================================

External code (web layer, scripts, etc.) MUST ONLY use Service Facades.
Direct import of core module classes is FORBIDDEN.

✅ CORRECT - Use Service Facades:
    from spider_aggregation.core.services import (
        FetcherService,
        ParserService,
        DeduplicatorService,
        FilterService,
        SchedulerService,
    )

    fetcher = FetcherService()
    result = fetcher.fetch_feed(url)

❌ WRONG - Direct class import (FORBIDDEN):
    from spider_aggregation.core.fetcher import FeedFetcher  # VIOLATION
    from spider_aggregation.core.parser import ContentParser   # VIOLATION

Available Services:
    - FetcherService: HTTP feed fetching
    - ParserService: Content parsing
    - DeduplicatorService: Duplicate detection
    - FilterService: Content filtering
    - SchedulerService: Task scheduling
    - ContentService: Full content fetching
    - KeywordService: Keyword extraction
    - SummarizerService: Content summarization
"""

# Service Facades (ONLY public interface for external code)
from spider_aggregation.core.services import (
    ContentService,
    DeduplicatorService,
    FetcherService,
    FilterService,
    KeywordService,
    ParserService,
    SchedulerService,
    SummarizerService,
    create_content_service,
    create_deduplicator_service,
    create_fetcher_service,
    create_filter_service,
    create_keyword_service,
    create_parser_service,
    create_scheduler_service,
    create_summarizer_service,
)

# Result types (allowed for type hints and return values)
from spider_aggregation.core.fetcher import FetchResult, FetchStats
from spider_aggregation.core.deduplicator import DedupResult
from spider_aggregation.core.filter_engine import FilterResult
from spider_aggregation.core.content_fetcher import ContentFetchResult
from spider_aggregation.core.summarizer import SummaryResult

# Enum types (allowed for configuration)
from spider_aggregation.core.deduplicator import DedupStrategy
from spider_aggregation.core.scheduler import JobStatus

__all__ = [
    # Service Facades (USE THESE)
    "FetcherService",
    "ParserService",
    "DeduplicatorService",
    "FilterService",
    "SchedulerService",
    "ContentService",
    "KeywordService",
    "SummarizerService",
    # Service factory functions
    "create_fetcher_service",
    "create_parser_service",
    "create_deduplicator_service",
    "create_filter_service",
    "create_scheduler_service",
    "create_content_service",
    "create_keyword_service",
    "create_summarizer_service",
    # Result types (for type hints)
    "FetchResult",
    "FetchStats",
    "DedupResult",
    "FilterResult",
    "ContentFetchResult",
    "SummaryResult",
    # Enum types (for configuration)
    "DedupStrategy",
    "JobStatus",
]


# Module boundary enforcement
# This helps catch violations at development time
_forbidden_imports = {
    "FeedFetcher": "Use FetcherService instead",
    "ContentParser": "Use ParserService instead",
    "FeedMetadataParser": "Use ParserService instead",
    "Deduplicator": "Use DeduplicatorService instead",
    "FilterEngine": "Use FilterService instead",
    "FeedScheduler": "Use SchedulerService instead",
    "ContentFetcher": "Use ContentService instead",
    "KeywordExtractor": "Use KeywordService instead",
    "Summarizer": "Use SummarizerService instead",
}


def __getattr__(name: str):
    """Intercept forbidden imports and provide helpful error messages."""
    if name in _forbidden_imports:
        raise ImportError(
            f"Direct import of '{name}' is forbidden. "
            f"{_forbidden_imports[name]}. "
            f"Use Service Facades from spider_aggregation.core.services instead."
        )
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
