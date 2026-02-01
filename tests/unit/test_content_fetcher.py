"""Tests for ContentFetcher."""

import pytest
from spider_aggregation.core.content_fetcher import ContentFetcher, ContentFetchResult


def test_content_fetcher_creation():
    """Test ContentFetcher creation."""
    fetcher = ContentFetcher(
        timeout_seconds=10,
        max_retries=2,
        max_content_length=100_000,
    )
    assert fetcher.timeout_seconds == 10
    assert fetcher.max_retries == 2
    assert fetcher.max_content_length == 100_000
    fetcher.close()


def test_invalid_url():
    """Test handling of invalid URLs."""
    fetcher = ContentFetcher()
    result = fetcher.fetch("not-a-valid-url")
    assert result.success is False
    assert "Invalid URL" in result.error
    fetcher.close()


def test_url_validation():
    """Test URL validation."""
    fetcher = ContentFetcher()

    # Valid URLs
    assert fetcher._is_valid_url("https://example.com")
    assert fetcher._is_valid_url("http://example.com/path")
    assert fetcher._is_valid_url("https://example.com:8080/path?query=value")

    # Invalid URLs
    assert not fetcher._is_valid_url("ftp://example.com")
    assert not fetcher._is_valid_url("not-a-url")
    assert not fetcher._is_valid_url("")

    fetcher.close()


def test_content_fetch_result():
    """Test ContentFetchResult dataclass."""
    result = ContentFetchResult(
        success=True,
        content="Sample content",
        title="Sample Title",
        source="trafilatura",
    )
    assert result.success is True
    assert result.content == "Sample content"
    assert result.title == "Sample Title"
    assert result.source == "trafilatura"
    assert "ContentFetchResult" in repr(result)


def test_extractive_summarizer():
    """Test extractive summarizer."""
    from spider_aggregation.core.summarizer import ExtractiveSummarizer

    summarizer = ExtractiveSummarizer(max_sentences=3)

    # Test with short text (should fail due to length check)
    short_text = "This is a short text."
    result = summarizer.summarize(short_text)
    assert result.success is False  # Too short

    # Test with longer text
    long_text = """
    Python is a high-level programming language. It is widely used for web development,
    data science, and artificial intelligence. Python code is known for its readability.
    Many developers choose Python for their projects. The language has a large community
    and extensive libraries. Python's syntax is clean and easy to learn.
    """
    result = summarizer.summarize(long_text)
    assert result.success is True
    assert result.method == "extractive"
    assert result.summary is not None


def test_keyword_extractor():
    """Test keyword extractor."""
    from spider_aggregation.core.keyword_extractor import KeywordExtractor

    extractor = KeywordExtractor(max_keywords=5)

    # Test with short text (should return empty)
    short_text = "Hi"
    keywords = extractor.extract(short_text)
    assert len(keywords) == 0

    # Test with longer text
    long_text = """
    Python is a high-level programming language. Python is widely used for web development,
    data science, and artificial intelligence. Python code is known for its readability.
    Many developers choose Python for their projects.
    """
    keywords = extractor.extract(long_text, language="en")
    # Should extract some keywords
    assert len(keywords) > 0
    # Python should be a top keyword
    assert any("python" in kw.lower() for kw in keywords)


def test_keyword_extractor_chinese():
    """Test keyword extractor with Chinese text."""
    from spider_aggregation.core.keyword_extractor import KeywordExtractor

    extractor = KeywordExtractor(max_keywords=5)

    chinese_text = """
    人工智能是计算机科学的一个分支。人工智能技术正在快速发展。
    机器学习是人工智能的核心技术之一。深度学习算法在图像识别中表现优异。
    """

    keywords = extractor.extract(chinese_text, language="zh")
    # Should extract some keywords
    assert len(keywords) > 0


def test_filter_rule_repository(db_session):
    """Test FilterRuleRepository."""
    from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository
    from spider_aggregation.models.entry import FilterRuleCreate

    repo = FilterRuleRepository(db_session)

    # Create rule
    rule_data = FilterRuleCreate(
        name="test_rule",
        enabled=True,
        rule_type="keyword",
        match_type="include",
        pattern="test",
        priority=5,
    )

    rule = repo.create(rule_data)
    assert rule.id is not None
    assert rule.name == "test_rule"

    # Get by ID
    fetched = repo.get_by_id(rule.id)
    assert fetched is not None
    assert fetched.name == "test_rule"

    # Get by name
    by_name = repo.get_by_name("test_rule")
    assert by_name is not None
    assert by_name.id == rule.id

    # List rules
    rules = repo.list()
    assert len(rules) >= 1

    # Count
    count = repo.count()
    assert count >= 1

    # Update
    from spider_aggregation.models.entry import FilterRuleUpdate

    update_data = FilterRuleUpdate(priority=10)
    updated = repo.update(rule, update_data)
    assert updated.priority == 10

    # Delete
    repo.delete(rule)
    assert repo.get_by_id(rule.id) is None


def test_filter_rule_get_enabled(db_session):
    """Test getting enabled rules ordered by priority."""
    from spider_aggregation.storage.repositories.filter_rule_repo import FilterRuleRepository
    from spider_aggregation.models.entry import FilterRuleCreate

    repo = FilterRuleRepository(db_session)

    # Create multiple rules with different priorities
    for i in range(3):
        rule_data = FilterRuleCreate(
            name=f"rule_{i}",
            enabled=True,
            rule_type="keyword",
            match_type="include",
            pattern=f"pattern_{i}",
            priority=i,
        )
        repo.create(rule_data)

    # Create one disabled rule
    disabled_data = FilterRuleCreate(
        name="disabled_rule",
        enabled=False,
        rule_type="keyword",
        match_type="include",
        pattern="disabled",
        priority=100,
    )
    repo.create(disabled_data)

    # Get enabled rules
    enabled = repo.get_enabled_rules()

    # Should have 3 enabled rules (plus any created in other tests)
    assert len(enabled) >= 3

    # Should be ordered by priority (descending)
    priorities = [r.priority for r in enabled]
    assert priorities == sorted(priorities, reverse=True)
