"""Symbol event router for symbolic processing pipeline output.

Routes SymbolPatternMatcher output to EventBus with lattice coordinates.
Each symbol shape maps to a cell in the lattice, enabling symbolic event routing.

Architecture:
    SymbolPatternMatcher -> SymbolEventRouter -> EventBus[topic=symbol.*] -> WebSocket/Dashboard

Lattice Mapping:
    APEX  -> A1 (Node 1: Technical Arsenal) - Initiation/Query start
    CORE  -> H1 (Node 2: Core Frameworks)   - Processing/Logic
    EMIT  -> O1 (Node 3: Skill Forge)       - Action/Output
    ROOT  -> V1 (Node 4: Meta Research)     - Ethics/Memory binding
    CUBE  -> Z1 (Node 5: Career)            - Stability/Grounding
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from backend.eventbus import bus
from backend.domain.models import SymbolicMetadata

logger = logging.getLogger(__name__)

# Symbol -> Lattice Cell mapping (coordinate binding)
SYMBOL_ROUTING_MAP: Dict[str, Dict[str, Any]] = {
    "APEX": {
        "cell": "A1",
        "node": 1,
        "topic": "symbol.initiation",
        "r": 1, "c": 1,
        "label": "Initiation Point (Prime Truth)",
    },
    "CORE": {
        "cell": "H1",
        "node": 2,
        "topic": "symbol.process",
        "r": 2, "c": 2,
        "label": "Processing Core (Diagonal Node 2)",
    },
    "EMIT": {
        "cell": "O1",
        "node": 3,
        "topic": "symbol.action",
        "r": 3, "c": 3,
        "label": "Action Emitter (Diagonal Node 3)",
    },
    "ROOT": {
        "cell": "V1",
        "node": 4,
        "topic": "symbol.ethics",
        "r": 4, "c": 4,
        "label": "Ethics Root (Meta Research focal)",
    },
    "CUBE": {
        "cell": "Z1",
        "node": 5,
        "topic": "symbol.stability",
        "r": 5, "c": 2,
        "label": "Stability Terminus (Career)",
    },
}


@dataclass
class SymbolEvent:
    """Event payload for symbol processing results."""

    symbol: str
    cell: str
    node: int
    topic: str
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    matched_seeds: List[str] = field(default_factory=list)
    applied_rules: Dict[str, str] = field(default_factory=dict)
    source_text_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "cell": self.cell,
            "node": self.node,
            "topic": self.topic,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "matched_seeds": self.matched_seeds,
            "applied_rules": self.applied_rules,
            "source_text_hash": self.source_text_hash,
        }


class SymbolEventRouter:
    """
    Routes symbol processing results to EventBus with lattice coordinates.

    Responsibilities:
    1. Accept SymbolicMetadata from SymbolPatternMatcher
    2. Map matched symbols to lattice cells
    3. Emit events to topic-specific channels (symbol.initiation, symbol.process, etc.)
    4. Track event flow metrics for dashboard
    """

    def __init__(self, bus_instance=None):
        """
        Initialize router with optional custom EventBus.

        Args:
            bus_instance: Custom EventBus, defaults to global singleton
        """
        self._bus = bus_instance or bus
        self._metrics = {
            "events_emitted": 0,
            "symbols_mapped": 0,
            "unmapped_symbols": 0,
            "topics_used": set(),
        }
        logger.info("SymbolEventRouter initialized")

    def emit_from_metadata(
        self,
        metadata: SymbolicMetadata,
        source_text_hash: Optional[str] = None
    ) -> List[SymbolEvent]:
        """
        Emit events for all matched symbols in metadata.

        Args:
            metadata: SymbolicMetadata from SymbolPatternMatcher
            source_text_hash: Optional hash of source text for correlation

        Returns:
            List of SymbolEvent objects that were emitted
        """
        events: List[SymbolEvent] = []

        for match in metadata.matched_symbols:
            symbol_name = match.get("shape", "").upper()
            event = self.emit_symbol(
                symbol_name=symbol_name,
                confidence=match.get("confidence", 0.0),
                matched_seeds=match.get("matched_seeds", []),
                applied_rules=match.get("applied_rules", {}),
                source_text_hash=source_text_hash,
            )
            if event:
                events.append(event)

        return events

    def emit_symbol(
        self,
        symbol_name: str,
        confidence: float = 1.0,
        matched_seeds: Optional[List[str]] = None,
        applied_rules: Optional[Dict[str, str]] = None,
        source_text_hash: Optional[str] = None,
    ) -> Optional[SymbolEvent]:
        """
        Emit a single symbol event to EventBus.

        Args:
            symbol_name: Name of symbol (APEX, CORE, EMIT, ROOT, CUBE)
            confidence: Match confidence 0.0-1.0
            matched_seeds: List of matched seed words
            applied_rules: Dict of applied transformation rules
            source_text_hash: Optional correlation hash

        Returns:
            SymbolEvent if mapped successfully, None otherwise
        """
        symbol_upper = symbol_name.upper()
        mapping = SYMBOL_ROUTING_MAP.get(symbol_upper)

        if not mapping:
            self._metrics["unmapped_symbols"] += 1
            logger.warning(f"Unmapped symbol: {symbol_name}")
            return None

        event = SymbolEvent(
            symbol=symbol_upper,
            cell=mapping["cell"],
            node=mapping["node"],
            topic=mapping["topic"],
            confidence=confidence,
            matched_seeds=matched_seeds or [],
            applied_rules=applied_rules or {},
            source_text_hash=source_text_hash,
        )

        # Publish to topic-specific channel
        self._bus.publish(event.to_dict(), topic=event.topic)

        # Also publish to catch-all symbol channel
        self._bus.publish(event.to_dict(), topic="symbol")

        # Update metrics
        self._metrics["events_emitted"] += 1
        self._metrics["symbols_mapped"] += 1
        self._metrics["topics_used"].add(event.topic)

        logger.debug(f"Emitted {symbol_upper} -> {event.cell} (Node {event.node})")

        return event

    def emit_diagonal_trace(self, confidence: float = 1.0) -> List[SymbolEvent]:
        """
        Emit events along the diagonal dependency path (A1 -> H1 -> O1 -> V1).

        This represents the dep_A1_to_V1 flow from Prime Truth to Meta Research.
        Useful for full-pipeline symbolic activation.

        Returns:
            List of emitted SymbolEvents along diagonal
        """
        diagonal_symbols = ["APEX", "CORE", "EMIT", "ROOT"]
        events = []

        for symbol in diagonal_symbols:
            event = self.emit_symbol(symbol, confidence=confidence)
            if event:
                events.append(event)

        logger.info(f"Diagonal trace emitted: {len(events)} events")
        return events

    def get_cell_for_symbol(self, symbol_name: str) -> Optional[str]:
        """Get lattice cell for a symbol name."""
        mapping = SYMBOL_ROUTING_MAP.get(symbol_name.upper())
        return mapping["cell"] if mapping else None

    def get_topic_for_symbol(self, symbol_name: str) -> Optional[str]:
        """Get EventBus topic for a symbol name."""
        mapping = SYMBOL_ROUTING_MAP.get(symbol_name.upper())
        return mapping["topic"] if mapping else None

    def metrics(self) -> Dict[str, Any]:
        """Get router metrics for dashboard."""
        return {
            "events_emitted": self._metrics["events_emitted"],
            "symbols_mapped": self._metrics["symbols_mapped"],
            "unmapped_symbols": self._metrics["unmapped_symbols"],
            "topics_used": list(self._metrics["topics_used"]),
            "bus_status": self._bus.status(),
        }


# Singleton instance for app-wide use
symbol_event_router = SymbolEventRouter()


# ── Backward-compat aliases (for legacy test suite — pre-Symbol-rename naming) ──
GLYPH_LATTICE_MAP = SYMBOL_ROUTING_MAP
GlyphEvent = SymbolEvent
GlyphEventBridge = SymbolEventRouter
glyph_bridge = SymbolEventRouter()
