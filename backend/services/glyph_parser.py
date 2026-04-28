"""Symbol sequence parser for cognitive concept extraction.

Parses symbolic sequences and converts them to structured metadata
for the Cognitive Orchestrator. Provides mapping from visual symbols to
cognitive concepts and actions.

Architecture:
    glyph_parser.py -> CognitiveOrchestrator -> EventBus
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# --- Symbol Map ---

SYMBOL_MAP = {
    # Meta-context symbols
    "\U0001f310": "meta_context",
    "\U0001f52d": "observation_mode",
    "\U0001f300": "cognitive_flow",

    # Action pulse symbols
    "\U0001f702": "action_pulse",
    "\u2699\ufe0f": "processing_gear",
    "\U0001f53a": "initiation_triangle",

    # Memory zone symbols
    "\U0001f7e2": "active_zone",
    "\U0001f7e1": "pattern_zone",
    "\U0001f534": "archived_zone",

    # Cognitive lens symbols
    "\U0001f9e0": "neurotypical_mode",
    "\u26a1": "adhd_burst",
    "\U0001f3af": "autism_precision",
    "\U0001f30a": "dyslexia_spatial",
}


def parse_symbol_sequence(sequence: str) -> Dict[str, Any]:
    """
    Parse a sequence of symbols into structured metadata.

    Args:
        sequence: String containing symbol characters

    Returns:
        Dict with parsed symbol information
    """
    if not sequence or not sequence.strip():
        return {"parsed": False, "symbols": [], "concepts": []}

    parsed_symbols = []
    concepts = []

    for char in sequence:
        if char in SYMBOL_MAP:
            concept = SYMBOL_MAP[char]
            parsed_symbols.append({"symbol": char, "concept": concept})
            concepts.append(concept)
            logger.debug(f"Parsed symbol: {char} -> {concept}")

    return {
        "parsed": len(parsed_symbols) > 0,
        "symbols": parsed_symbols,
        "concepts": concepts,
        "sequence_length": len(sequence),
        "parsed_count": len(parsed_symbols)
    }


def get_available_symbols() -> Dict[str, str]:
    """Get the complete symbol map."""
    return SYMBOL_MAP.copy()


def add_symbol_mapping(symbol: str, concept: str) -> None:
    """
    Add a new symbol mapping dynamically.

    Args:
        symbol: The symbol character
        concept: The cognitive concept it represents
    """
    SYMBOL_MAP[symbol] = concept
    logger.info(f"Added symbol mapping: {symbol} -> {concept}")


def get_concept_for_symbol(symbol: str) -> Optional[str]:
    """Get the concept for a specific symbol character."""
    return SYMBOL_MAP.get(symbol)
