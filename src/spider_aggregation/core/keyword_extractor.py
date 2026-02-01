"""
Keyword extractor for automatic keyword/tag extraction from article content.

Supports English (NLTK) and Chinese (jieba) text processing.
Uses TF-IDF for keyword scoring.
"""

import re
from collections import Counter
from typing import Optional

from spider_aggregation.config import get_config
from spider_aggregation.logger import get_logger

logger = get_logger(__name__)

# Try to import optional dependencies
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba not available, Chinese keyword extraction limited")

# NLTK imports - lazy loaded to avoid startup issues
NLTK_AVAILABLE = False
_nltk_modules = None

def _ensure_nltk():
    """Lazy-load NLTK modules only when needed."""
    global NLTK_AVAILABLE, _nltk_modules
    if _nltk_modules is not None:
        return _nltk_modules

    try:
        import nltk
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        from nltk.stem import WordNetLemmatizer

        # Download required NLTK data (silently ignore errors)
        try:
            nltk.data.find("tokenizers/punkt")
        except LookupError:
            try:
                nltk.download("punkt", quiet=True)
            except Exception:
                pass
        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:
            try:
                nltk.download("stopwords", quiet=True)
            except Exception:
                pass
        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            try:
                nltk.download("wordnet", quiet=True)
            except Exception:
                pass

        NLTK_AVAILABLE = True
        _nltk_modules = {
            "nltk": nltk,
            "stopwords": stopwords,
            "word_tokenize": word_tokenize,
            "WordNetLemmatizer": WordNetLemmatizer,
        }
        return _nltk_modules
    except ImportError:
        logger.warning("NLTK not available, English keyword extraction limited")
        return None
    except Exception as e:
        logger.warning(f"NLTK initialization failed: {e}")
        return None


class KeywordExtractor:
    """Extract keywords from text content."""

    def __init__(
        self,
        max_keywords: int = 10,
        min_keyword_length: int = 2,
        language: str = "auto",
    ) -> None:
        """Initialize the keyword extractor.

        Args:
            max_keywords: Maximum number of keywords to extract
            min_keyword_length: Minimum keyword length
            language: Language setting (auto, en, zh)
        """
        self.max_keywords = max_keywords
        self.min_keyword_length = min_keyword_length
        self.language = language

        # Initialize NLTK components for English (lazy load)
        self._lemmatizer = None
        self._stopwords = set()
        self._nltk_loaded = False

        logger.info(
            f"KeywordExtractor initialized (NLTK=lazy, jieba={JIEBA_AVAILABLE})"
        )

    def _load_nltk_if_needed(self):
        """Load NLTK modules on first use."""
        if self._nltk_loaded:
            return True

        nltk_modules = _ensure_nltk()
        if nltk_modules:
            try:
                self._lemmatizer = nltk_modules["WordNetLemmatizer"]()
                self._stopwords = set(nltk_modules["stopwords"].words("english"))
                self._nltk_loaded = True
                return True
            except Exception:
                self._nltk_loaded = True
                return False
        return False

    def _detect_language(self, text: str) -> str:
        """Detect the primary language of text.

        Args:
            text: Text to analyze

        Returns:
            Language code (zh, en, or other)
        """
        # Count Chinese characters
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_chars = len(text)

        if total_chars > 0 and chinese_chars / total_chars > 0.3:
            return "zh"

        return "en"

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for keyword extraction.

        Args:
            text: Raw text

        Returns:
            Preprocessed text
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Remove URLs
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)

        # Remove email addresses
        text = re.sub(r"\S+@\S+", " ", text)

        # Remove special characters but keep word characters
        text = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _extract_keywords_en(self, text: str) -> list[tuple[str, float]]:
        """Extract keywords from English text.

        Args:
            text: English text

        Returns:
            List of (keyword, score) tuples
        """
        # Try to load NLTK on first use
        if not self._load_nltk_if_needed():
            # Fallback: simple word frequency
            words = re.findall(r"\b[a-zA-Z]{" + str(self.min_keyword_length) + r",}\b", text.lower())
            word_freq = Counter(words)
            return [(word, freq) for word, freq in word_freq.most_common(self.max_keywords * 2)]

        nltk_modules = _ensure_nltk()
        if not nltk_modules:
            # Fallback if NLTK load failed
            words = re.findall(r"\b[a-zA-Z]{" + str(self.min_keyword_length) + r",}\b", text.lower())
            word_freq = Counter(words)
            return [(word, freq) for word, freq in word_freq.most_common(self.max_keywords * 2)]

        word_tokenize = nltk_modules["word_tokenize"]

        # Tokenize and preprocess
        tokens = word_tokenize(text.lower())

        # Filter stopwords and short words
        keywords = []
        for token in tokens:
            if (
                len(token) >= self.min_keyword_length
                and token not in self._stopwords
                and token.isalpha()
            ):
                # Lemmatize
                lemma = self._lemmatizer.lemmatize(token)
                keywords.append(lemma)

        # Calculate TF-IDF-like scores
        keyword_freq = Counter(keywords)

        # Normalize by max frequency
        if keyword_freq:
            max_freq = max(keyword_freq.values())
            keyword_scores = {
                word: freq / max_freq for word, freq in keyword_freq.items()
            }
        else:
            keyword_scores = {}

        # Sort by score
        sorted_keywords = sorted(
            keyword_scores.items(), key=lambda x: x[1], reverse=True
        )

        return sorted_keywords[: self.max_keywords * 2]

    def _extract_keywords_zh(self, text: str) -> list[tuple[str, float]]:
        """Extract keywords from Chinese text.

        Args:
            text: Chinese text

        Returns:
            List of (keyword, score) tuples
        """
        if JIEBA_AVAILABLE:
            # Use jieba's TF-IDF extractor
            keywords = jieba.analyse.extract_tags(
                text,
                topK=self.max_keywords * 2,
                withWeight=True,
                allowPOS=("n", "nr", "ns", "nt", "nz", "v", "vd", "vn"),
            )
            return [(kw, score) for kw, score in keywords]
        else:
            # Fallback: simple character/word frequency
            # Extract Chinese words (2+ characters)
            words = re.findall(r"[\u4e00-\u9fff]{2,}", text)
            word_freq = Counter(words)
            return [(word, freq) for word, freq in word_freq.most_common(self.max_keywords * 2)]

    def _extract_keywords_mixed(self, text: str) -> list[tuple[str, float]]:
        """Extract keywords from mixed language text.

        Args:
            text: Mixed language text

        Returns:
            List of (keyword, score) tuples
        """
        # Split into Chinese and English parts
        chinese_parts = re.findall(r"[\u4e00-\u9fff\s]+", text)
        english_parts = re.findall(r"[a-zA-Z\s]+", text)

        keywords_en = []
        keywords_zh = []

        if english_parts:
            en_text = " ".join(english_parts)
            keywords_en = self._extract_keywords_en(en_text)

        if chinese_parts:
            zh_text = " ".join(chinese_parts)
            keywords_zh = self._extract_keywords_zh(zh_text)

        # Combine and re-score
        all_keywords = {}

        for word, score in keywords_en:
            all_keywords[word] = all_keywords.get(word, 0) + score

        for word, score in keywords_zh:
            all_keywords[word] = all_keywords.get(word, 0) + score

        # Sort by score
        sorted_keywords = sorted(
            all_keywords.items(), key=lambda x: x[1], reverse=True
        )

        return sorted_keywords[: self.max_keywords * 2]

    def extract(self, text: Optional[str], language: Optional[str] = None) -> list[str]:
        """Extract keywords from text.

        Args:
            text: Text to extract keywords from
            language: Override detected language (en, zh, auto)

        Returns:
            List of keywords (no scores)
        """
        if not text:
            return []

        # Preprocess
        text = self._preprocess_text(text)

        if len(text) < 50:
            return []

        # Determine language
        lang = language or self.language
        if lang == "auto":
            lang = self._detect_language(text)

        # Extract keywords
        if lang == "zh":
            keywords_with_scores = self._extract_keywords_zh(text)
        elif lang == "en":
            keywords_with_scores = self._extract_keywords_en(text)
        else:
            keywords_with_scores = self._extract_keywords_mixed(text)

        # Return just the keywords
        return [kw for kw, _ in keywords_with_scores[: self.max_keywords]]

    def extract_with_scores(
        self, text: Optional[str], language: Optional[str] = None
    ) -> list[tuple[str, float]]:
        """Extract keywords with scores.

        Args:
            text: Text to extract keywords from
            language: Override detected language

        Returns:
            List of (keyword, score) tuples
        """
        if not text:
            return []

        # Preprocess
        text = self._preprocess_text(text)

        if len(text) < 50:
            return []

        # Determine language
        lang = language or self.language
        if lang == "auto":
            lang = self._detect_language(text)

        # Extract keywords
        if lang == "zh":
            return self._extract_keywords_zh(text)[: self.max_keywords]
        elif lang == "en":
            return self._extract_keywords_en(text)[: self.max_keywords]
        else:
            return self._extract_keywords_mixed(text)[: self.max_keywords]

    def extract_from_entry(self, title: str, content: Optional[str] = None) -> list[str]:
        """Extract keywords from an entry (title + content).

        Args:
            title: Entry title
            content: Entry content/summary

        Returns:
            List of keywords
        """
        # Combine title and content (title has more weight)
        combined = f"{title}\n\n{content or ''}"

        keywords = self.extract(combined)

        # Ensure title words are prioritized
        title_words = set(self.extract(title))
        other_keywords = [kw for kw in keywords if kw not in title_words]

        return list(title_words) + other_keywords[: self.max_keywords - len(title_words)]


def create_keyword_extractor(
    max_keywords: Optional[int] = None,
    min_keyword_length: Optional[int] = None,
    language: Optional[str] = None,
) -> KeywordExtractor:
    """Factory function to create a KeywordExtractor.

    Args:
        max_keywords: Maximum number of keywords
        min_keyword_length: Minimum keyword length
        language: Language setting

    Returns:
        Configured KeywordExtractor instance
    """
    config = get_config()

    return KeywordExtractor(
        max_keywords=max_keywords or config.keyword_extractor.max_keywords,
        min_keyword_length=min_keyword_length or config.keyword_extractor.min_keyword_length,
        language=language or config.keyword_extractor.language,
    )
