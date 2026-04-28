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
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import from domain models to avoid circular imports
from backend.domain.models import SymbolMatch, SymbolicMetadata


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
            return SymbolicMetadata([], None, set(), 0.0)

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

        return SymbolicMetadata(
            matched_symbols=[match.model_dump() for match in matches],
            dominant_topic=dominant_topic,
            symbolic_tags=symbolic_tags,
            processing_confidence=avg_confidence
        )

    def _match_symbol(self, text: str, shape_name: str, shape_data: Dict[str, Any]) -> Optional[SymbolMatch]:
        """
        Match a single symbol pattern against text.

        Uses fuzzy matching with:
        - Exact word matches (highest confidence)
        - Partial substring matches (medium confidence)
        - Stem/root similarity (lower confidence)
        """
        text_lower = text.lower()
        seeds = shape_data.get('seeds', [])
        rules = shape_data.get('rules', {})
        topic = shape_data.get('topic', 'unknown')

        matched_seeds = []
        applied_rules = {}
        total_score = 0.0
        match_count = 0

        for seed in seeds:
            seed_lower = seed.lower()

            # Exact word match (highest confidence)
            if re.search(r'\b' + re.escape(seed_lower) + r'\b', text_lower):
                matched_seeds.append(seed)
                total_score += 1.0
                match_count += 1

                # Apply rules if seed matches
                if seed in rules:
                    applied_rules[seed] = rules[seed]

            # Partial substring match (medium confidence)
            elif seed_lower in text_lower:
                matched_seeds.append(seed)
                total_score += 0.7
                match_count += 1

                # Apply rules for partial matches too
                if seed in rules:
                    applied_rules[seed] = rules[seed]

        if match_count == 0:
            return None

        # Calculate average confidence
        confidence = total_score / match_count

        return SymbolMatch(
            shape=shape_name,
            topic=topic,
            confidence=min(confidence, 1.0),  # Cap at 1.0
            matched_seeds=matched_seeds,
            applied_rules=applied_rules
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
