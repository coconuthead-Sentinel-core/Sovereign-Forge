"""
symbol_processor.py — shim module re-exporting from glyph_processor.

Preserves the older import path `backend.services.symbol_processor` for
legacy test compatibility after the Symbol* rename. New code should import
directly from `backend.services.glyph_processor`.
"""
from .glyph_processor import (
    SymbolPatternMatcher,
    SymbolicMetadata,
    get_symbol_pattern_matcher,
)

__all__ = ["SymbolPatternMatcher", "SymbolicMetadata", "get_symbol_pattern_matcher"]
