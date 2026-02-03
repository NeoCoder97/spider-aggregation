"""
Facade services for core modules.

This module provides unified entry points (Facade pattern) for all core business logic modules.
External code (web layer, etc.) should ONLY interact with these services, not direct module classes.

Architecture Rules:
    - Web layer MUST use these services, never import from fetcher/parser/deduplicator directly
    - Each service encapsulates one functional domain
    - Services use factory functions for component creation
    - Services provide simple, high-level interfaces

Example:
    # Correct - Use service facade
    from spider_aggregation.core.services import FetcherService, ParserService

    fetcher = FetcherService()
    result = fetcher.fetch_feed(url)

    parser = ParserService()
    parsed = parser.parse_entry(entry_data)

    # Wrong - Direct import (forbidden)
    from spider_aggregation.core.fetcher import FeedFetcher  # VIOLATION
"""

from spider_aggregation.core.services.fetcher_service import FetcherService, create_fetcher_service
from spider_aggregation.core.services.parser_service import ParserService, create_parser_service
from spider_aggregation.core.services.deduplicator_service import (
    DeduplicatorService,
    create_deduplicator_service,
)
from spider_aggregation.core.services.filter_service import FilterService, create_filter_service
from spider_aggregation.core.services.scheduler_service import (
    SchedulerService,
    create_scheduler_service,
)
from spider_aggregation.core.services.content_service import ContentService, create_content_service
from spider_aggregation.core.services.keyword_service import KeywordService, create_keyword_service
from spider_aggregation.core.services.summarizer_service import (
    SummarizerService,
    create_summarizer_service,
)

__all__ = [
    # Services
    "FetcherService",
    "ParserService",
    "DeduplicatorService",
    "FilterService",
    "SchedulerService",
    "ContentService",
    "KeywordService",
    "SummarizerService",
    # Factory functions
    "create_fetcher_service",
    "create_parser_service",
    "create_deduplicator_service",
    "create_filter_service",
    "create_scheduler_service",
    "create_content_service",
    "create_keyword_service",
    "create_summarizer_service",
]
