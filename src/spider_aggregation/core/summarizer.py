"""
Summarizer for generating article summaries.

Supports extractive summarization (rule-based) and AI summarization (Zhipu AI).
"""

import re
from typing import Optional
from dataclasses import dataclass

from spider_aggregation.config import get_config
from spider_aggregation.logger import get_logger

logger = get_logger(__name__)

# Try to import Zhipu AI
try:
    from zhipuai import ZhipuAI
    ZHIPUAI_AVAILABLE = True
except ImportError:
    ZHIPUAI_AVAILABLE = False
    logger.warning("zhipuai not available, AI summarization disabled")


@dataclass
class SummaryResult:
    """Result of summarization."""

    success: bool
    summary: Optional[str] = None
    method: str = ""  # "extractive" or "ai"
    error: Optional[str] = None

    def __repr__(self) -> str:
        return f"<SummaryResult(success={self.success}, method={self.method})>"


class ExtractiveSummarizer:
    """Extractive summarization using sentence scoring."""

    def __init__(
        self,
        max_sentences: int = 3,
        min_sentence_length: int = 10,
    ) -> None:
        """Initialize the extractive summarizer.

        Args:
            max_sentences: Maximum sentences in summary
            min_sentence_length: Minimum sentence length
        """
        self.max_sentences = max_sentences
        self.min_sentence_length = min_sentence_length

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting using regex
        # This handles English and basic Chinese sentence boundaries

        # Chinese sentence boundaries
        sentences = re.split(r"([。！？\n]+)", text)

        # Rejoin punctuation with sentences
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
            sentence = sentence.strip()
            if sentence:
                result.append(sentence)

        # Handle remaining text
        if len(sentences) % 2 == 1:
            remaining = sentences[-1].strip()
            if remaining:
                result.append(remaining)

        # Also try English-style splitting
        if len(result) <= 1:
            result = re.split(r"[.!?]+\s+", text)
            result = [s.strip() for s in result if s.strip()]

        return result

    def _score_sentence(self, sentence: str, position: int, total: int) -> float:
        """Score a sentence for importance.

        Args:
            sentence: Sentence text
            position: Position in document (0-indexed)
            total: Total number of sentences

        Returns:
            Score (higher is more important)
        """
        if len(sentence) < self.min_sentence_length:
            return 0.0

        score = 0.0

        # Position score: first and last sentences are important
        if position == 0 or position == total - 1:
            score += 2.0
        elif position < total * 0.2:  # First 20%
            score += 1.5
        elif position > total * 0.8:  # Last 20%
            score += 1.0

        # Length score: prefer medium-length sentences
        word_count = len(re.findall(r"\S+", sentence))
        if 10 <= word_count <= 30:
            score += 1.0
        elif 5 <= word_count < 10 or 30 < word_count <= 50:
            score += 0.5

        # Content features
        # Numbers and dates suggest factual content
        if re.search(r"\d+", sentence):
            score += 0.3

        # Quotes suggest important statements
        if '"' in sentence or "'" in sentence or "\"" in sentence:
            score += 0.2

        # Question marks in first half suggest topic sentences
        if position < total * 0.5 and "?" in sentence:
            score += 0.2

        return score

    def summarize(self, text: Optional[str]) -> SummaryResult:
        """Generate extractive summary.

        Args:
            text: Input text

        Returns:
            SummaryResult with generated summary
        """
        if not text or len(text.strip()) < 100:
            return SummaryResult(
                success=False, error="Text too short for summarization"
            )

        # Split into sentences
        sentences = self._split_sentences(text)

        if len(sentences) <= self.max_sentences:
            # Return as-is if already short enough
            summary = " ".join(sentences)
            return SummaryResult(success=True, summary=summary, method="extractive")

        # Score sentences
        scored_sentences = [
            (s, self._score_sentence(s, i, len(sentences)))
            for i, s in enumerate(sentences)
        ]

        # Sort by score and select top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        selected = scored_sentences[: self.max_sentences]

        # Re-sort by original position
        selected_with_pos = [
            (s, sentences.index(s), score) for s, score in selected
        ]
        selected_with_pos.sort(key=lambda x: x[1])

        # Join sentences
        summary = " ".join(s for s, _, _ in selected_with_pos)

        return SummaryResult(success=True, summary=summary, method="extractive")


class AISummarizer:
    """AI-based summarization using Zhipu AI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "glm-4-flash",
        max_tokens: int = 150,
    ) -> None:
        """Initialize the AI summarizer.

        Args:
            api_key: Zhipu AI API key
            model: Model name to use
            max_tokens: Maximum tokens in summary
        """
        if not ZHIPUAI_AVAILABLE:
            raise ImportError("zhipuai package is required for AI summarization")

        self.model = model
        self.max_tokens = max_tokens

        # Get API key from parameter or environment
        if not api_key:
            import os
            api_key = os.getenv("ZHIPUAI_API_KEY")

        if not api_key:
            logger.warning("ZHIPUAI_API_KEY not set, AI summarization unavailable")
            self._client = None
        else:
            self._client = ZhipuAI(api_key=api_key)
            logger.info(f"AI Summarizer initialized with model: {model}")

    def _build_prompt(self, text: str) -> str:
        """Build prompt for AI summarization.

        Args:
            text: Input text

        Returns:
            Prompt string
        """
        # Truncate if too long (approximate token limit)
        max_chars = 3000
        truncated = text[:max_chars]

        return f"""请用简洁的语言总结以下文章的主要内容（3句话以内）：

{truncated}

摘要："""

    def summarize(self, text: Optional[str]) -> SummaryResult:
        """Generate AI summary.

        Args:
            text: Input text

        Returns:
            SummaryResult with generated summary
        """
        if not self._client:
            return SummaryResult(
                success=False,
                error="Zhipu AI client not initialized (check API key)"
            )

        if not text or len(text.strip()) < 100:
            return SummaryResult(
                success=False, error="Text too short for summarization"
            )

        try:
            prompt = self._build_prompt(text)

            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.7,
            )

            summary = response.choices[0].message.content.strip()

            if not summary:
                return SummaryResult(success=False, error="AI returned empty summary")

            return SummaryResult(success=True, summary=summary, method="ai")

        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return SummaryResult(success=False, error=f"AI error: {e}")


class Summarizer:
    """Main summarizer that supports both extractive and AI methods."""

    def __init__(
        self,
        method: str = "extractive",
        max_sentences: int = 3,
        min_sentence_length: int = 10,
        ai_api_key: Optional[str] = None,
        ai_model: str = "glm-4-flash",
        ai_max_tokens: int = 150,
    ) -> None:
        """Initialize the summarizer.

        Args:
            method: Summarization method (extractive or ai)
            max_sentences: Max sentences for extractive
            min_sentence_length: Min sentence length for extractive
            ai_api_key: API key for AI summarization
            ai_model: AI model to use
            ai_max_tokens: Max tokens for AI summary
        """
        self.method = method

        self._extractive = ExtractiveSummarizer(
            max_sentences=max_sentences,
            min_sentence_length=min_sentence_length,
        )

        if method == "ai":
            try:
                self._ai = AISummarizer(
                    api_key=ai_api_key,
                    model=ai_model,
                    max_tokens=ai_max_tokens,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize AI summarizer: {e}, falling back to extractive")
                self.method = "extractive"
                self._ai = None
        else:
            self._ai = None

        logger.info(f"Summarizer initialized with method: {self.method}")

    def summarize(self, text: Optional[str], method: Optional[str] = None) -> SummaryResult:
        """Generate summary.

        Args:
            text: Input text
            method: Override default method

        Returns:
            SummaryResult with generated summary
        """
        if not text:
            return SummaryResult(success=False, error="No text provided")

        effective_method = method or self.method

        if effective_method == "ai" and self._ai:
            result = self._ai.summarize(text)
            # Fallback to extractive on AI failure
            if not result.success and result.error:
                logger.warning(f"AI summarization failed, falling back to extractive: {result.error}")
                return self._extractive.summarize(text)
            return result
        else:
            return self._extractive.summarize(text)

    def summarize_entry(
        self,
        title: str,
        content: Optional[str] = None,
        method: Optional[str] = None,
    ) -> SummaryResult:
        """Summarize an entry (title + content).

        Args:
            title: Entry title
            content: Entry content
            method: Override default method

        Returns:
            SummaryResult with generated summary
        """
        # Prioritize content, use title if content not available
        text = content or title

        # If content is very short, combine with title
        if content and len(content) < 200:
            text = f"{title}\n\n{content}"

        return self.summarize(text, method)


def create_summarizer(
    method: Optional[str] = None,
    max_sentences: Optional[int] = None,
    min_sentence_length: Optional[int] = None,
    ai_api_key: Optional[str] = None,
) -> Summarizer:
    """Factory function to create a Summarizer.

    Args:
        method: Summarization method
        max_sentences: Max sentences for extractive
        min_sentence_length: Min sentence length
        ai_api_key: API key for AI

    Returns:
        Configured Summarizer instance
    """
    config = get_config()

    return Summarizer(
        method=method or config.summarizer.method,
        max_sentences=max_sentences or config.summarizer.max_sentences,
        min_sentence_length=min_sentence_length or config.summarizer.min_sentence_length,
        ai_api_key=ai_api_key,
        ai_model=config.summarizer.ai_model,
        ai_max_tokens=config.summarizer.ai_max_tokens,
    )
