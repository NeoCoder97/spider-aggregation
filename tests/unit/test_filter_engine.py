"""Tests for FilterEngine."""

import pytest
from spider_aggregation.core.filter_engine import FilterEngine, FilterResult
from spider_aggregation.models.entry import FilterRuleModel


@pytest.fixture
def sample_rules(db_session):
    """Create sample filter rules."""
    rules = [
        FilterRuleModel(
            name="include_python",
            enabled=True,
            rule_type="keyword",
            match_type="include",
            pattern="python",
            priority=10,
        ),
        FilterRuleModel(
            name="exclude_ai",
            enabled=True,
            rule_type="keyword",
            match_type="exclude",
            pattern="advertisement",
            priority=5,
        ),
        FilterRuleModel(
            name="include_tag_tech",
            enabled=True,
            rule_type="tag",
            match_type="include",
            pattern="tech",
            priority=8,
        ),
    ]
    for rule in rules:
        db_session.add(rule)
    db_session.flush()
    return rules


@pytest.fixture
def sample_entries(db_session):
    """Create sample entries."""
    from spider_aggregation.models.entry import EntryModel
    from spider_aggregation.models.feed import FeedModel
    from datetime import datetime

    # First create a feed
    feed = FeedModel(
        name="Test Feed",
        url="https://example.com/feed",
        enabled=True,
        fetch_interval_minutes=60,
    )
    db_session.add(feed)
    db_session.flush()

    entries = [
        EntryModel(
            feed_id=feed.id,
            title="Python Programming Tutorial",
            link="https://example.com/python",
            title_hash="hash1",
            link_hash="linkhash1",
            content="Learn Python programming from scratch",
            tags='["python", "programming"]',
        ),
        EntryModel(
            feed_id=feed.id,
            title="Special Advertisement",
            link="https://example.com/ad",
            title_hash="hash2",
            link_hash="linkhash2",
            content="This is an advertisement post",
        ),
        EntryModel(
            feed_id=feed.id,
            title="JavaScript Guide",
            link="https://example.com/js",
            title_hash="hash3",
            link_hash="linkhash3",
            content="Complete JavaScript guide",
            tags='["javascript", "tech"]',
        ),
    ]
    for entry in entries:
        db_session.add(entry)
    db_session.flush()
    return entries


def test_filter_engine_creation(sample_rules):
    """Test FilterEngine creation."""
    engine = FilterEngine(sample_rules)
    assert len(engine.rules) == 3
    # Rules should be sorted by priority
    assert engine.rules[0].name == "include_python"
    assert engine.rules[0].priority == 10


def test_keyword_include_filter(sample_rules, sample_entries):
    """Test keyword include filter."""
    engine = FilterEngine(sample_rules)

    # Entry with "python" in title should pass include rule
    entry = sample_entries[0]
    result = engine.filter_entry(entry)
    assert result.passed is True
    assert "include_python" in result.matched_rules


def test_keyword_exclude_filter(sample_rules, sample_entries):
    """Test keyword exclude filter."""
    engine = FilterEngine(sample_rules)

    # Entry with "advertisement" should be excluded
    entry = sample_entries[1]
    result = engine.filter_entry(entry)
    assert result.passed is False
    assert result.excluded_by == "exclude_ai"


def test_tag_filter(sample_rules, sample_entries):
    """Test tag filter."""
    engine = FilterEngine(sample_rules)

    # Entry with "tech" tag should match tag filter
    entry = sample_entries[2]
    result = engine.filter_entry(entry)
    # Should pass because it has the "tech" tag
    assert "include_tag_tech" in result.matched_rules


def test_no_include_match(sample_rules, db_session):
    """Test entry that doesn't match any include rule."""
    from spider_aggregation.models.entry import EntryModel

    # Create engine with only include rules
    include_only_rules = [r for r in sample_rules if r.match_type == "include"]
    engine = FilterEngine(include_only_rules)

    entry = EntryModel(
        feed_id=1,
        title="Random Article",
        link="https://example.com/random",
        title_hash="hash_random",
        link_hash="linkhash_random",
        content="Random content that doesn't match anything",
    )

    result = engine.filter_entry(entry)
    # Should fail because no include rules matched
    assert result.passed is False


def test_disabled_rules(sample_rules, sample_entries):
    """Test that disabled rules are not applied."""
    # Disable the exclude rule
    sample_rules[1].enabled = False

    engine = FilterEngine(sample_rules)

    entry = sample_entries[1]  # The advertisement entry
    result = engine.filter_entry(entry)

    # Should pass because the exclude rule is disabled
    # (assuming there's an include rule it matches or no include rules)
    assert "exclude_ai" not in result.matched_rules


def test_filter_entries_batch(sample_rules, sample_entries):
    """Test filtering multiple entries."""
    engine = FilterEngine(sample_rules)

    passed, report = engine.filter_entries(sample_entries)

    # Should have at least one entry (the python one)
    assert len(passed) >= 1
    assert len(report) == len(sample_entries)


def test_regex_filter(db_session):
    """Test regex pattern filter."""
    from spider_aggregation.models.entry import EntryModel
    from spider_aggregation.models.feed import FeedModel

    # Create feed first
    feed = FeedModel(
        name="Test Feed",
        url="https://example.com/feed",
        enabled=True,
        fetch_interval_minutes=60,
    )
    db_session.add(feed)
    db_session.flush()

    rule = FilterRuleModel(
        name="regex_email",
        enabled=True,
        rule_type="regex",
        match_type="exclude",
        pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        priority=1,
    )
    db_session.add(rule)
    db_session.flush()

    engine = FilterEngine([rule])

    entry_with_email = EntryModel(
        feed_id=feed.id,
        title="Contact Me",
        link="https://example.com/contact",
        title_hash="hash_contact",
        link_hash="linkhash_contact",
        content="Email me at test@example.com for details",
    )

    result = engine.filter_entry(entry_with_email)
    assert result.passed is False
    assert result.excluded_by == "regex_email"


def test_language_filter(db_session):
    """Test language filter."""
    from spider_aggregation.models.entry import EntryModel
    from spider_aggregation.models.feed import FeedModel

    # Create feed first
    feed = FeedModel(
        name="Test Feed",
        url="https://example.com/feed",
        enabled=True,
        fetch_interval_minutes=60,
    )
    db_session.add(feed)
    db_session.flush()

    rule = FilterRuleModel(
        name="only_english",
        enabled=True,
        rule_type="language",
        match_type="include",
        pattern="en",
        priority=1,
    )
    db_session.add(rule)
    db_session.flush()

    engine = FilterEngine([rule])

    english_entry = EntryModel(
        feed_id=feed.id,
        title="English Article",
        link="https://example.com/en",
        title_hash="hash_en",
        link_hash="linkhash_en",
        content="This is English content",
        language="en",
    )

    chinese_entry = EntryModel(
        feed_id=feed.id,
        title="Chinese Article",
        link="https://example.com/zh",
        title_hash="hash_zh",
        link_hash="linkhash_zh",
        content="这是中文内容",
        language="zh",
    )

    # English should pass
    result_en = engine.filter_entry(english_entry)
    assert result_en.passed is True

    # Chinese should not pass (only include rule for English)
    result_zh = engine.filter_entry(chinese_entry)
    assert result_zh.passed is False
