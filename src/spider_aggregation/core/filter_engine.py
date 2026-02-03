"""
Filter engine for applying filter rules to entries.

Supports keyword, regex, tag, and language filtering with include/exclude logic.
"""

import json
import re
from functools import lru_cache
from typing import Optional

from spider_aggregation.logger import get_logger
from spider_aggregation.models.filter_rule import FilterRuleModel
from spider_aggregation.models.entry import EntryModel

logger = get_logger(__name__)


class FilterResult:
    """Result of filtering an entry."""

    def __init__(
        self,
        passed: bool,
        matched_rules: list[str],
        excluded_by: Optional[str] = None,
    ) -> None:
        """Initialize filter result.

        Args:
            passed: Whether the entry passed all filters
            matched_rules: List of rule names that matched
            excluded_by: Name of the rule that excluded the entry
        """
        self.passed = passed
        self.allowed = passed  # Alias for compatibility
        self.matched_rules = matched_rules
        self.excluded_by = excluded_by

    def __repr__(self) -> str:
        return f"<FilterResult(passed={self.passed}, excluded_by={self.excluded_by})>"


class FilterEngine:
    """Engine for applying filter rules to entries.

    Supports both EntryModel objects and any object with the required attributes
    (title, content, summary, link, tags, language).
    """

    def __init__(self, rules: list[FilterRuleModel], cache_size: int = 100) -> None:
        """Initialize filter engine with rules.

        Args:
            rules: List of filter rules to apply
            cache_size: Size of the LRU cache for compiled patterns
        """
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        self.cache_size = cache_size

        # Pre-compile regex patterns
        self._compile_regex_patterns()

        logger.info(f"FilterEngine initialized with {len(self.rules)} rules")

    def _compile_regex_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        self._regex_cache = {}

        for rule in self.rules:
            if rule.rule_type == "regex":
                try:
                    self._regex_cache[rule.id] = re.compile(rule.pattern, re.IGNORECASE)
                except re.error as e:
                    logger.warning(f"Invalid regex pattern in rule '{rule.name}': {e}")

    def _match_regex(self, pattern: re.Pattern, text: Optional[str]) -> bool:
        """Match a regex pattern against text.

        Args:
            pattern: Compiled regex pattern
            text: Text to match against

        Returns:
            True if pattern matches
        """
        if not text:
            return False
        return pattern.search(text) is not None

    @lru_cache(maxsize=100)
    def _match_keyword_cached(self, pattern: str, text_lower: str) -> bool:
        """Match a keyword pattern (cached version).

        Args:
            pattern: Keyword pattern to match
            text_lower: Lowercase text to search in

        Returns:
            True if keyword is found
        """
        return pattern.lower() in text_lower

    def _match_keyword(self, pattern: str, text: Optional[str]) -> bool:
        """Match a keyword pattern against text.

        Args:
            pattern: Keyword pattern to match
            text: Text to search in

        Returns:
            True if keyword is found
        """
        if not text:
            return False
        return self._match_keyword_cached(pattern, text.lower())

    def _match_tag(self, pattern: str, tags_json: Optional[str]) -> bool:
        """Match a tag pattern against entry tags.

        Args:
            pattern: Tag pattern to match
            tags_json: JSON string of tags

        Returns:
            True if tag matches
        """
        if not tags_json:
            return False

        try:
            tags = json.loads(tags_json)
            if not isinstance(tags, list):
                return False

            pattern_lower = pattern.lower()
            return any(pattern_lower in tag.lower() for tag in tags)
        except (json.JSONDecodeError, TypeError):
            return False

    def _match_language(self, pattern: str, language: Optional[str]) -> bool:
        """Match a language pattern.

        Args:
            pattern: Language code pattern
            language: Entry language code

        Returns:
            True if language matches
        """
        if not language:
            return False
        return pattern.lower() == language.lower()

    def _rule_matches(self, rule: FilterRuleModel, entry: EntryModel) -> bool:
        """Check if a rule matches an entry.

        Args:
            rule: Filter rule to check
            entry: Entry to check against

        Returns:
            True if the rule matches the entry
        """
        if rule.rule_type == "keyword":
            # Check in title and content
            title_match = self._match_keyword(rule.pattern, entry.title)
            content_match = self._match_keyword(rule.pattern, entry.content) or self._match_keyword(
                rule.pattern, entry.summary
            )
            return title_match or content_match

        elif rule.rule_type == "regex":
            # Check in title and content
            pattern = self._regex_cache.get(rule.id)
            if not pattern:
                return False

            title_match = self._match_regex(pattern, entry.title)
            content_match = self._match_regex(pattern, entry.content) or self._match_regex(
                pattern, entry.summary
            )
            return title_match or content_match

        elif rule.rule_type == "tag":
            return self._match_tag(rule.pattern, entry.tags)

        elif rule.rule_type == "language":
            return self._match_language(rule.pattern, entry.language)

        return False

    def filter_entry(self, entry: EntryModel) -> FilterResult:
        """Filter an entry against all rules.

        Rules are processed in priority order (highest first).
        - Exclude rules take precedence
        - First matching exclude rule excludes the entry
        - Entry must match at least one include rule (if any exist)

        Args:
            entry: Entry to filter

        Returns:
            FilterResult with pass/fail status
        """
        matched_rules = []
        has_include_rules = any(r.match_type == "include" for r in self.rules)
        matched_include = False

        for rule in self.rules:
            if not rule.enabled:
                continue

            if self._rule_matches(rule, entry):
                matched_rules.append(rule.name)

                if rule.match_type == "exclude":
                    # Exclude rules take immediate precedence
                    return FilterResult(
                        passed=False,
                        matched_rules=matched_rules,
                        excluded_by=rule.name,
                    )
                elif rule.match_type == "include":
                    matched_include = True

        # If there are include rules, entry must match at least one
        if has_include_rules and not matched_include:
            return FilterResult(
                passed=False,
                matched_rules=matched_rules,
                excluded_by="no_include_match",
            )

        return FilterResult(passed=True, matched_rules=matched_rules)

    def filter_entries(
        self, entries: list[EntryModel]
    ) -> tuple[list[EntryModel], dict[str, list[int]]]:
        """Filter multiple entries.

        Args:
            entries: List of entries to filter

        Returns:
            Tuple of (passed_entries, filter_report)
            filter_report maps entry_id to list of matched rule names
        """
        passed = []
        filter_report = {}

        for entry in entries:
            result = self.filter_entry(entry)
            filter_report[str(entry.id)] = result.matched_rules

            if result.passed:
                passed.append(entry)

        logger.info(
            f"Filtered {len(entries)} entries: {len(passed)} passed, "
            f"{len(entries) - len(passed)} excluded"
        )

        return passed, filter_report

    def clear_cache(self) -> None:
        """Clear the keyword matching cache."""
        self._match_keyword_cached.cache_clear()
        logger.debug("Filter engine cache cleared")


def create_filter_engine(
    rules: list[FilterRuleModel], cache_size: int = 100
) -> FilterEngine:
    """Factory function to create a FilterEngine.

    Args:
        rules: List of filter rules
        cache_size: Size of the LRU cache

    Returns:
        Configured FilterEngine instance
    """
    return FilterEngine(rules, cache_size)
