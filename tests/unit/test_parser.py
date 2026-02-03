"""Unit tests for content parser."""

import pytest
from datetime import datetime

from spider_aggregation.core.parser import ContentParser, FeedMetadataParser, create_parser


class TestContentParser:
    """Tests for ContentParser."""

    def test_init(self):
        """Test parser initialization."""
        parser = ContentParser()

        assert parser.max_content_length > 0
        assert parser.strip_html is True
        assert parser.preserve_paragraphs is True

    def test_init_with_custom_params(self):
        """Test parser with custom parameters."""
        parser = ContentParser(
            max_content_length=5000,
            strip_html=False,
            preserve_paragraphs=False,
        )

        assert parser.max_content_length == 5000
        assert parser.strip_html is False
        assert parser.preserve_paragraphs is False

    def test_parse_entry_basic(self):
        """Test basic entry parsing."""
        parser = ContentParser()

        raw_entry = {
            "title": "Test Entry",
            "link": "https://example.com/article",
            "author": "John Doe",
            "summary": "Test summary",
            "published": "2024-01-01T10:00:00Z",
        }

        result = parser.parse_entry(raw_entry)

        assert result["title"] == "Test Entry"
        assert result["link"] == "https://example.com/article"
        assert result["author"] == "John Doe"
        assert result["summary"] == "Test summary"

    def test_normalize_title(self):
        """Test title normalization."""
        parser = ContentParser()

        # Basic title
        assert parser._normalize_title("  Test Title  ") == "Test Title"

        # HTML entities
        assert parser._normalize_title("Test &quot;Title&quot;") == 'Test "Title"'

        # Long title truncation
        long_title = "A" * 600
        result = parser._normalize_title(long_title)
        assert len(result) == 500
        assert result.endswith("...")

        # None title
        assert parser._normalize_title(None) is None
        assert parser._normalize_title("") is None

    def test_normalize_link(self):
        """Test link normalization."""
        parser = ContentParser()

        # Valid links
        assert (
            parser._normalize_link("https://example.com/article")
            == "https://example.com/article"
        )
        assert (
            parser._normalize_link("http://example.com/article")
            == "http://example.com/article"
        )

        # Strip whitespace
        assert (
            parser._normalize_link("  https://example.com/article  ")
            == "https://example.com/article"
        )

        # Invalid links
        assert parser._normalize_link("not-a-url") is None
        assert parser._normalize_link(None) is None

    def test_normalize_author(self):
        """Test author normalization."""
        parser = ContentParser()

        # Basic author
        assert parser._normalize_author("  John Doe  ") == "John Doe"

        # Remove "by" prefix
        assert parser._normalize_author("By John Doe") == "John Doe"
        assert parser._normalize_author("Posted by Jane") == "Jane"

        # Dict format
        assert (
            parser._normalize_author({"name": "John", "email": "john@example.com"})
            == "John"
        )

        # None author
        assert parser._normalize_author(None) is None
        assert parser._normalize_author("") is None

    def test_strip_html(self):
        """Test HTML stripping."""
        parser = ContentParser()

        html = "<p>Hello <strong>World</strong>!</p>"

        # With paragraph preservation
        result = parser._strip_html(html, preserve_paragraphs=True)
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

        # Without paragraph preservation
        result = parser._strip_html(html, preserve_paragraphs=False)
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

        # Remove script/style
        html_with_script = "<script>alert('xss')</script><p>Content</p>"
        result = parser._strip_html(html_with_script)
        assert "alert" not in result
        assert "Content" in result

    def test_normalize_content(self):
        """Test content normalization."""
        parser = ContentParser(max_content_length=100)

        # HTML content
        html_content = "<p>This is <strong>HTML</strong> content.</p>"
        result = parser._normalize_content(html_content)
        assert "<" not in result
        assert "HTML" in result

        # Length truncation
        long_content = "A" * 200
        result = parser._normalize_content(long_content)
        assert len(result) <= 100
        assert "..." in result

        # None content
        assert parser._normalize_content(None) is None

    def test_parse_date(self):
        """Test date parsing."""
        parser = ContentParser()

        # ISO 8601 format
        result = parser._parse_date("2024-01-01T10:00:00Z")
        assert isinstance(result, datetime)
        assert result.year == 2024

        # Simple date format
        result = parser._parse_date("2024-01-01")
        assert isinstance(result, datetime)
        assert result.year == 2024

        # Invalid date
        assert parser._parse_date("invalid-date") is None
        assert parser._parse_date(None) is None

    def test_extract_tags(self):
        """Test tag extraction."""
        parser = ContentParser()

        # List format
        entry = {"tags": [{"term": "python"}, {"term": "programming"}]}
        result = parser._extract_tags(entry)
        assert result == ["python", "programming"]

        # Comma-separated string
        entry = {"tags": "python, programming, code"}
        result = parser._extract_tags(entry)
        assert result == ["python", "programming", "code"]

        # Categories
        entry = {"categories": ["tech", "AI"]}
        result = parser._extract_tags(entry)
        assert result == ["tech", "ai"]

        # No tags
        entry = {}
        result = parser._extract_tags(entry)
        assert result is None

    def test_detect_language(self):
        """Test language detection."""
        parser = ContentParser()

        # Chinese content
        entry = {"summary": "这是一篇中文文章"}
        assert parser._detect_language(entry) == "zh"

        # Japanese content
        entry = {"summary": "これは日本語の記事です"}
        assert parser._detect_language(entry) == "ja"

        # English content
        entry = {"summary": "This is an English article"}
        assert parser._detect_language(entry) == "en"

        # Explicit language field
        entry = {"language": "zh-CN"}
        assert parser._detect_language(entry) == "zh"

        # No detectable language
        entry = {}
        assert parser._detect_language(entry) is None

    def test_calculate_reading_time(self):
        """Test reading time calculation."""
        parser = ContentParser()

        # English content (~200 words per minute)
        english = "word " * 100  # ~500 chars
        result = parser._calculate_reading_time(english)
        assert result >= 10  # Minimum 10 seconds
        assert result <= 180  # Should be ~30 seconds

        # Chinese content (~400 chars per minute)
        chinese = "中" * 400
        result = parser._calculate_reading_time(chinese)
        assert result >= 10

        # Empty content
        assert parser._calculate_reading_time("") == 0
        assert parser._calculate_reading_time(None) == 0

    def test_full_entry_parsing(self):
        """Test full entry parsing workflow."""
        parser = ContentParser()

        raw_entry = {
            "title": "  Test Entry Title  ",
            "link": "https://example.com/article",
            "author": {"name": "John Doe"},
            "summary": "<p>This is a <strong>test</strong> summary.</p>",
            "content": "<div>Full content with <script>evil()</script>tags.</div>",
            "published": "2024-01-01T10:00:00Z",
            "tags": [{"term": "test"}, {"term": "example"}],
            "language": "en-US",
        }

        result = parser.parse_entry(raw_entry)

        assert result["title"] == "Test Entry Title"
        assert result["link"] == "https://example.com/article"
        assert result["author"] == "John Doe"
        assert "<strong>" not in result["summary"]
        assert "test" in result["summary"].lower()
        assert "evil" not in result["content"]
        assert isinstance(result["published_at"], datetime)
        assert result["tags"] == ["test", "example"]
        assert result["language"] == "en"
        assert result["reading_time_seconds"] is not None

    def test_edge_cases(self):
        """Test edge cases."""
        parser = ContentParser()

        # Empty entry
        result = parser.parse_entry({})
        assert result["title"] is None
        assert result["link"] is None
        assert result["content"] is None

        # Entry with only required fields
        entry = {"title": "Test", "link": "https://example.com"}
        result = parser.parse_entry(entry)
        assert result["title"] == "Test"
        assert result["link"] == "https://example.com"
        assert result["summary"] is None

        # Entry with weird whitespace
        entry = {"title": "  Test    Title  \n\n"}
        result = parser.parse_entry(entry)
        assert result["title"] == "Test Title"  # Whitespace is normalized

    def test_content_with_preserve_paragraphs(self):
        """Test paragraph preservation in HTML stripping."""
        parser = ContentParser(preserve_paragraphs=True)

        html = """
        <h1>Title</h1>
        <p>Paragraph 1</p>
        <p>Paragraph 2</p>
        """
        result = parser._strip_html(html, preserve_paragraphs=True)
        assert "\n\n" in result

        parser_no_preserve = ContentParser(preserve_paragraphs=False)
        result = parser_no_preserve._strip_html(html, preserve_paragraphs=False)
        assert "\n\n" not in result


class TestFeedMetadataParser:
    """Tests for FeedMetadataParser."""

    def test_parse_feed_info(self):
        """Test feed metadata parsing."""
        parser = FeedMetadataParser()

        # Mock feedparser structure properly
        class MockFeed:
            def __init__(self):
                self.feed = {
                    "title": "  Test Feed  ",
                    "link": "https://example.com",
                    "description": "<p>A test <strong>feed</strong></p>",
                    "language": "en-US",
                    "updated": "2024-01-01T10:00:00Z",
                }
                self.entries = [
                    {"title": "Entry 1"},
                    {"title": "Entry 2"},
                ]

        raw_feed = MockFeed()
        result = parser.parse_feed_info(raw_feed)

        assert result["title"] == "Test Feed"
        assert result["link"] == "https://example.com"
        assert "test feed" in result["description"].lower()
        assert result["language"] == "en-US"
        assert isinstance(result["updated_at"], datetime)
        assert result["entry_count"] == 2

    def test_parse_feed_info_minimal(self):
        """Test parsing minimal feed info."""
        parser = FeedMetadataParser()

        raw_feed = {"feed": {}, "entries": []}

        result = parser.parse_feed_info(raw_feed)

        assert result["title"] is None
        assert result["link"] is None
        assert result["description"] is None
        assert result["entry_count"] == 0


class TestCreateParser:
    """Tests for create_parser factory function."""

    def test_create_parser_default(self):
        """Test creating parser with defaults."""
        parser = create_parser()

        assert isinstance(parser, ContentParser)
        assert parser.strip_html is True
        assert parser.preserve_paragraphs is True

    def test_create_parser_custom(self):
        """Test creating parser with custom settings."""
        parser = create_parser(
            max_content_length=5000,
            strip_html=False,
            preserve_paragraphs=False,
        )

        assert parser.max_content_length == 5000
        assert parser.strip_html is False
        assert parser.preserve_paragraphs is False
