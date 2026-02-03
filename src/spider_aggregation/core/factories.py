"""
Factory functions for creating core components with proper dependency injection.

This module provides a centralized location for creating all core components
with consistent configuration from the config system. This enables:

1. Consistent dependency injection pattern across all core modules
2. Easier mocking in tests
3. Single place for component configuration
4. Support for future AOP/middleware (logging, metrics)

Usage:
    from spider_aggregation.core.factories import (
        create_fetcher,
        create_parser,
        create_deduplicator,
        create_filter_engine,
        create_keyword_extractor,
        create_content_fetcher,
        create_summarizer,
        create_scheduler,
    )

    # Create with default configuration
    fetcher = create_fetcher()

    # Create with overrides
    parser = create_parser(max_content_length=50000)
"""

from typing import Optional

from sqlalchemy.orm import Session

from spider_aggregation.config import get_config
from spider_aggregation.core.fetcher import FeedFetcher
from spider_aggregation.core.parser import ContentParser
from spider_aggregation.core.deduplicator import Deduplicator, DedupStrategy
from spider_aggregation.core.filter_engine import FilterEngine
from spider_aggregation.core.keyword_extractor import KeywordExtractor
from spider_aggregation.core.content_fetcher import ContentFetcher
from spider_aggregation.core.summarizer import Summarizer


def create_fetcher(
    session: Optional[Session] = None,
    timeout_seconds: Optional[int] = None,
    max_retries: Optional[int] = None,
) -> FeedFetcher:
    """Create a configured FeedFetcher instance.

    Args:
        session: Optional database session
        timeout_seconds: Override default timeout
        max_retries: Override default retry count

    Returns:
        Configured FeedFetcher instance
    """
    config = get_config()
    return FeedFetcher(
        session=session,
        timeout_seconds=timeout_seconds or config.fetcher.timeout_seconds,
        max_retries=max_retries or config.fetcher.max_retries,
    )


def create_parser(
    max_content_length: Optional[int] = None,
    strip_html: bool = True,
    preserve_paragraphs: bool = True,
) -> ContentParser:
    """Create a configured ContentParser instance.

    Args:
        max_content_length: Override default max content length
        strip_html: Whether to strip HTML tags
        preserve_paragraphs: Whether to preserve paragraph structure

    Returns:
        Configured ContentParser instance
    """
    config = get_config()
    return ContentParser(
        max_content_length=max_content_length or config.fetcher.max_content_length,
        strip_html=strip_html,
        preserve_paragraphs=preserve_paragraphs,
    )


def create_deduplicator(
    session: Optional[Session] = None,
    strategy: Optional[str] = None,
) -> Deduplicator:
    """Create a configured Deduplicator instance.

    Args:
        session: Optional database session
        strategy: Override deduplication strategy ("strict", "medium", "relaxed")

    Returns:
        Configured Deduplicator instance
    """
    # Map string to enum (default to MEDIUM)
    strategy_value = strategy or "medium"
    strategy_enum = DedupStrategy(strategy_value) if strategy_value else DedupStrategy.MEDIUM

    return Deduplicator(
        session=session,
        strategy=strategy_enum,
    )


def create_filter_engine(
    rules: Optional[list] = None,
    cache_size: Optional[int] = None,
) -> FilterEngine:
    """Create a configured FilterEngine instance.

    Args:
        rules: Optional list of FilterRuleModel instances
        cache_size: Override default LRU cache size

    Returns:
        Configured FilterEngine instance
    """
    config = get_config()
    rules = rules or []

    return FilterEngine(
        rules=rules,
        cache_size=cache_size or config.filter.cache_size,
    )


def create_keyword_extractor(
    max_keywords: Optional[int] = None,
    language: Optional[str] = None,
) -> KeywordExtractor:
    """Create a configured KeywordExtractor instance.

    Args:
        max_keywords: Override maximum number of keywords
        language: Override default language

    Returns:
        Configured KeywordExtractor instance
    """
    config = get_config()
    return KeywordExtractor(
        max_keywords=max_keywords or config.content.max_keywords,
        language=language or config.content.language,
    )


def create_content_fetcher(
    timeout_seconds: Optional[int] = None,
    max_content_length: Optional[int] = None,
) -> ContentFetcher:
    """Create a configured ContentFetcher instance.

    Args:
        timeout_seconds: Override request timeout
        max_content_length: Override max content length

    Returns:
        Configured ContentFetcher instance
    """
    config = get_config()
    return ContentFetcher(
        timeout_seconds=timeout_seconds or config.content.fetch_timeout,
        max_content_length=max_content_length or config.content.max_content_length,
    )


def create_summarizer(
    max_summary_length: Optional[int] = None,
    extractive_sentences: Optional[int] = None,
    ai_enabled: Optional[bool] = None,
) -> Summarizer:
    """Create a configured Summarizer instance.

    Args:
        max_summary_length: Override max summary length
        extractive_sentences: Override number of sentences for extractive summary
        ai_enabled: Override AI summarization flag

    Returns:
        Configured Summarizer instance
    """
    config = get_config()
    return Summarizer(
        max_summary_length=max_summary_length or config.content.max_summary_length,
        extractive_sentences=extractive_sentences or config.content.extractive_sentences,
        ai_enabled=ai_enabled if ai_enabled is not None else config.content.ai_summary_enabled,
    )


def create_scheduler(
    session: Optional[Session] = None,
    max_workers: Optional[int] = None,
    db_manager=None,
) -> "FeedScheduler":
    """Create a configured FeedScheduler instance.

    Args:
        session: Optional database session
        max_workers: Override maximum worker threads
        db_manager: Optional DatabaseManager instance

    Returns:
        Configured FeedScheduler instance
    """
    from spider_aggregation.core.scheduler import FeedScheduler

    config = get_config()
    return FeedScheduler(
        session=session,
        max_workers=max_workers or config.scheduler.max_workers,
        db_manager=db_manager,
    )
