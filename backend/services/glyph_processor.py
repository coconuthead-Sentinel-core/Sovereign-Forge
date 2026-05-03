"""Symbol pattern matching engine for text analysis.

Loads and processes symbol patterns from JSON configuration for symbolic
processing in the Cognitive Orchestrator. Provides fuzzy matching against
text to identify symbolic patterns and generate metadata.

Architecture:
    SymbolPatternMatcher -> symbols_pack.json -> SymbolicMetadata -> CognitiveOrchestrator
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import asdict, dataclass, is_dataclass

logger = logging.getLogger(__name__)

# Import from domain models to avoid circular imports
from backend.domain.models import SymbolMatch, SymbolicMetadata


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Serialize either a Pydantic BaseModel (model_dump) or a dataclass
    (asdict). Falls back to ``vars(obj)`` for plain instances.
    """
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump()
    if is_dataclass(obj):
        return asdict(obj)
    return dict(vars(obj))


class SymbolPatternMatcher:
    """
    Processes text against symbol patterns for symbolic recognition.

    Responsibilities:
    1. Load symbol definitions from JSON
    2. Perform fuzzy pattern matching against text
    3. Generate symbolic metadata with confidence scores
    4. Apply transformation rules based on matches
    """

    def __init__(self, symbols_path: Optional[str] = None):
        """
        Initialize SymbolPatternMatcher.

        Args:
            symbols_path: Path to symbols JSON file. Defaults to data/symbols_pack.json
        """
        self.symbols_path = symbols_path or self._default_symbols_path()
        self.symbols: Dict[str, Dict[str, Any]] = {}
        self._load_symbols()
        logger.info(f"SymbolPatternMatcher initialized with {len(self.symbols)} shapes")

    def _default_symbols_path(self) -> str:
        """Get default path to symbols file."""
        # Assume we're in backend/services/, go up two levels to project root
        backend_dir = Path(__file__).parent.parent.parent
        return str(backend_dir / "data" / "symbols_pack.json")

    def _load_symbols(self) -> None:
        """Load symbol definitions from JSON file."""
        try:
            with open(self.symbols_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.symbols = data.get('shapes', {})
                logger.info(f"Loaded {len(self.symbols)} symbol shapes")
        except FileNotFoundError:
            logger.warning(f"Symbols file not found: {self.symbols_path}")
            # Create sample symbols if file doesn't exist
            self._create_sample_symbols()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in symbols file: {e}")
            raise

    def _create_sample_symbols(self) -> None:
        """Create sample symbols for development."""
        logger.info("Creating sample symbols for development")
        self.symbols = {
            "APEX": {
                "topic": "initiation",
                "seeds": ["apex", "ignite", "ai_infer", "start", "init", "query"],
                "rules": {"apex": "tag:initiation"}
            },
            "CORE": {
                "topic": "process",
                "seeds": ["core", "resolve", "process", "logic", "reason"],
                "rules": {"process": "tag:process.core"}
            },
            "EMIT": {
                "topic": "action",
                "seeds": ["emit", "launch", "trigger", "output", "send"],
                "rules": {"launch": "tag:action.emit"}
            },
            "ROOT": {
                "topic": "ethics",
                "seeds": ["root", "link", "thread", "memory", "ethics", "bind"],
                "rules": {"ethics": "tag:ethics.guard"}
            },
            "CUBE": {
                "topic": "stability",
                "seeds": ["cube", "resonate", "stabilize", "harmonize", "ground"],
                "rules": {"cube": "tag:stability.struct"}
            }
        }

    def process_text(self, text: str) -> SymbolicMetadata:
        """
        Process text for symbolic patterns.

        Args:
            text: Input text to analyze

        Returns:
            SymbolicMetadata with matches and derived information
        """
        if not text or not text.strip():
            return SymbolicMetadata(
                matched_symbols=[],
                dominant_topic=None,
                symbolic_tags=set(),
                processing_confidence=0.0,
            )

        # Find all symbol matches
        matches = []
        for shape_name, shape_data in self.symbols.items():
            match = self._match_symbol(text, shape_name, shape_data)
            if match:
                matches.append(match)

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)

        # Derive metadata
        dominant_topic = matches[0].topic if matches else None
        symbolic_tags = set()
        total_confidence = 0.0

        for match in matches:
            symbolic_tags.update(match.applied_rules.values())
            total_confidence += match.confidence

        avg_confidence = total_confidence / len(matches) if matches else 0.0

        # Pass SymbolMatch dataclasses through directly so callers can
        # read attributes (.shape, .confidence). For JSON callers there is
        # the helper _to_dict() and serialize_match() below.
        return SymbolicMetadata(
            matched_symbols=list(matches),
            dominant_topic=dominant_topic,
            symbolic_tags=symbolic_tags,
            processing_confidence=avg_confidence
        )

    @staticmethod
    def serialize_match(match: Any) -> Dict[str, Any]:
        """Serialize a SymbolMatch (dataclass or dict) into a JSON-safe dict."""
        return _to_dict(match)

    # ── Confidence model constants ─────────────────────────────────
    EXACT_SCORE          = 1.0   # \bseed\b in text
    SUBSTRING_SCORE      = 0.7   # seed contained as substring in text
    STEM_SCORE           = 0.7   # seed and a text word share a strong prefix
    SECONDARY_DECAY      = 0.9   # each match after the first contributes
                                 # SECONDARY_DECAY ** i of its raw score
    STEM_MIN_PREFIX      = 4     # minimum shared-prefix length to count
    STEM_MIN_PREFIX_RATIO = 0.5  # AND >= this fraction of seed length

    def _stem_match(self, seed_lower: str, text_lower: str) -> bool:
        """Return True if any word in `text_lower` shares a strong prefix
        with `seed_lower`. Used as the third matching tier so words like
        ``initialize`` partially match a seed of ``initiate`` (shared
        prefix ``initia`` of length 6).
        """
        threshold = max(self.STEM_MIN_PREFIX,
                        int(len(seed_lower) * self.STEM_MIN_PREFIX_RATIO))
        for word in re.findall(r"[A-Za-z]+", text_lower):
            if word == seed_lower or seed_lower in word or word in seed_lower:
                # Already covered by exact / substring tiers
                continue
            common = 0
            for a, b in zip(seed_lower, word):
                if a != b:
                    break
                common += 1
            if common >= threshold:
                return True
        return False

    def _match_symbol(self, text: str, shape_name: str, shape_data: Dict[str, Any]) -> Optional[SymbolMatch]:
        """Match a single symbol pattern against text.

        Tiered matching, highest-confidence wins per seed:
          1. Exact word     (\\bseed\\b)               -> EXACT_SCORE
          2. Substring      (seed in text)             -> SUBSTRING_SCORE
          3. Stem/prefix    (shared prefix >= cutoff)  -> STEM_SCORE

        Final symbol confidence uses a *diminishing-returns average*: the
        highest-scoring seed contributes its full score, each subsequent
        seed contributes ``SECONDARY_DECAY ** rank`` of its score, then
        the result is averaged over the matched-seed count. This preserves
        the canonical contract:

          * 1 exact match  -> 1.0 confidence
          * 1 partial      -> 0.7 confidence
          * N>=2 matches   -> < 1.0 (additional matches imply ambiguity
                              about the dominant topic)
        """
        text_lower = text.lower()
        seeds = shape_data.get('seeds', [])
        rules = shape_data.get('rules', {})
        topic = shape_data.get('topic', 'unknown')

        matched_seeds: List[str] = []
        applied_rules: Dict[str, str] = {}
        per_seed_scores: List[float] = []

        for seed in seeds:
            seed_lower = seed.lower()
            score: Optional[float] = None

            # Tier 1: exact word
            if re.search(r'\b' + re.escape(seed_lower) + r'\b', text_lower):
                score = self.EXACT_SCORE
            # Tier 2: substring
            elif seed_lower in text_lower:
                score = self.SUBSTRING_SCORE
            # Tier 3: stem (shared prefix)
            elif self._stem_match(seed_lower, text_lower):
                score = self.STEM_SCORE

            if score is None:
                continue

            matched_seeds.append(seed)
            per_seed_scores.append(score)
            if seed in rules:
                applied_rules[seed] = rules[seed]

        if not per_seed_scores:
            return None

        # Diminishing-returns average. Sort descending so the strongest
        # match anchors the confidence; subsequent matches discount.
        sorted_scores = sorted(per_seed_scores, reverse=True)
        weighted_total = sum(
            s * (self.SECONDARY_DECAY ** i)
            for i, s in enumerate(sorted_scores)
        )
        confidence = weighted_total / len(sorted_scores)

        return SymbolMatch(
            shape=shape_name,
            topic=topic,
            confidence=min(confidence, 1.0),
            matched_seeds=matched_seeds,
            applied_rules=applied_rules,
        )

    def get_available_shapes(self) -> List[str]:
        """Get list of available symbol shapes."""
        return list(self.symbols.keys())

    def get_shape_info(self, shape: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific symbol shape."""
        return self.symbols.get(shape)

    def reload_symbols(self) -> None:
        """Reload symbols from file."""
        self._load_symbols()


# --- Singleton Instance (Optional convenience) ---

_symbol_pattern_matcher: Optional[SymbolPatternMatcher] = None


def get_symbol_pattern_matcher() -> SymbolPatternMatcher:
    """
    Get the default SymbolPatternMatcher instance (lazy singleton).

    Returns:
        SymbolPatternMatcher instance
    """
    global _symbol_pattern_matcher
    if _symbol_pattern_matcher is None:
        _symbol_pattern_matcher = SymbolPatternMatcher()
    return _symbol_pattern_matcher
