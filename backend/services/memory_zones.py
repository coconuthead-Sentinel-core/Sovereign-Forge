"""Three-Zone Memory Manager for Sentinel Forge.

Manages entropy-based routing of notes between cognitive zones:
- ACTIVE: High entropy (>0.7) - Real-time processing
- PATTERN: Mid entropy (0.3-0.7) - Pattern emergence
- ARCHIVED: Low entropy (<0.3) - Stable storage

Architecture:
    CognitiveOrchestrator → ThreeZoneMemory → ZonedNote → cosmos_repo
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict

from backend.domain.models import (
    Note,
    ZonedNote,
    MemoryZone,
    ZoneMetrics,
    CognitiveLens,
)

logger = logging.getLogger(__name__)


# --- Entropy Calculation ---

def calculate_entropy(text: str) -> float:
    """
    Calculate information entropy of text.
    
    Higher entropy = more diverse/novel content.
    Lower entropy = more repetitive/stable content.
    
    Algorithm: Unique token ratio (simple but effective).
    Future: Shannon entropy with character/n-gram distribution.
    
    Args:
        text: Input text to analyze
        
    Returns:
        float between 0.0 and 1.0
    """
    if not text or not text.strip():
        return 0.0
    
    # Token frequency analysis
    tokens = text.lower().split()
    if not tokens:
        return 0.0
    
    # Unique ratio: more unique = higher entropy
    unique_ratio = len(set(tokens)) / len(tokens)
    
    # Clamp to valid range
    return max(0.0, min(1.0, unique_ratio))


def classify_zone(entropy: float) -> MemoryZone:
    """
    Route content to appropriate memory zone based on entropy.
    
    Thresholds:
    - >0.7: ACTIVE (novel, high-information content)
    - 0.3-0.7: PATTERN (emerging patterns, semi-stable)
    - <0.3: ARCHIVED (stable, well-known patterns)
    
    Args:
        entropy: Entropy score (0.0-1.0)
        
    Returns:
        MemoryZone enum value
    """
    if entropy > 0.7:
        return MemoryZone.ACTIVE
    elif entropy > 0.3:
        return MemoryZone.PATTERN
    else:
        return MemoryZone.ARCHIVED


# --- Three-Zone Memory Manager ---

class ThreeZoneMemory:
    """
    Manages the three-zone memory system for cognitive processing.
    
    Responsibilities:
    1. Calculate entropy for incoming content
    2. Classify content into appropriate zone
    3. Track zone transitions and metrics
    4. Provide zone-aware querying (future)
    
    Thread-safe: Uses simple counters (future: add locks if needed).
    """
    
    # Zone entropy thresholds (configurable)
    ACTIVE_THRESHOLD = 0.7      # >0.7 = active
    PATTERN_THRESHOLD = 0.3     # >0.3 = pattern, else archived
    
    def __init__(self) -> None:
        """Initialize ThreeZoneMemory with empty zone counters."""
        self._zone_counts: Dict[MemoryZone, int] = defaultdict(int)
        self._total_entropy: float = 0.0
        self._total_items: int = 0
        self._last_transition: Optional[str] = None
        
        logger.info("ThreeZoneMemory initialized")
    
    def route_to_zone(self, text: str) -> tuple[MemoryZone, float]:
        """
        Calculate entropy and determine zone for given text.
        
        Args:
            text: Content to analyze and route
            
        Returns:
            Tuple of (MemoryZone, entropy_score)
        """
        entropy = calculate_entropy(text)
        zone = classify_zone(entropy)
        
        # Update metrics
        self._zone_counts[zone] += 1
        self._total_entropy += entropy
        self._total_items += 1
        
        logger.debug(f"Routed to {zone.value}: entropy={entropy:.3f}")
        
        return zone, entropy
    
    def create_zoned_note(
        self,
        text: str,
        tag: str,
        lens: Optional[CognitiveLens] = None,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ZonedNote:
        """
        Create a ZonedNote with automatic zone classification.
        
        Args:
            text: Note content
            tag: Categorization tag
            lens: Cognitive lens applied during creation
            vector: Optional embedding vector
            metadata: Optional additional metadata
            
        Returns:
            ZonedNote with zone and entropy populated
        """
        zone, entropy = self.route_to_zone(text)
        
        note = ZonedNote(
            text=text,
            tag=tag,
            zone=zone,
            entropy=entropy,
            lens_applied=lens,
            vector=vector,
            metadata=metadata or {},
        )
        
        return note
    
    def record_transition(self, from_zone: MemoryZone, to_zone: MemoryZone) -> None:
        """
        Record a zone transition event.
        
        Args:
            from_zone: Original zone
            to_zone: New zone after transition
        """
        self._last_transition = f"{from_zone.value}→{to_zone.value}"
        logger.info(f"Zone transition: {self._last_transition}")
    
    def get_metrics(self) -> ZoneMetrics:
        """
        Get current zone distribution metrics.
        
        Returns:
            ZoneMetrics with counts and averages
        """
        avg_entropy = (
            self._total_entropy / self._total_items 
            if self._total_items > 0 
            else 0.0
        )
        
        return ZoneMetrics(
            active_count=self._zone_counts[MemoryZone.ACTIVE],
            pattern_count=self._zone_counts[MemoryZone.PATTERN],
            archived_count=self._zone_counts[MemoryZone.ARCHIVED],
            avg_entropy=round(avg_entropy, 3),
            last_transition=self._last_transition,
        )
    
    def get_zone_distribution(self) -> Dict[str, float]:
        """
        Get percentage distribution across zones.
        
        Returns:
            Dict with zone names and percentages
        """
        total = sum(self._zone_counts.values()) or 1
        
        return {
            zone.value: round(count / total * 100, 1)
            for zone, count in self._zone_counts.items()
        }
    
    def reset_metrics(self) -> None:
        """Reset all zone counters and metrics."""
        self._zone_counts.clear()
        self._total_entropy = 0.0
        self._total_items = 0
        self._last_transition = None
        logger.info("ThreeZoneMemory metrics reset")


# --- Singleton Instance (Optional convenience) ---

_default_memory: Optional[ThreeZoneMemory] = None


def get_memory_manager() -> ThreeZoneMemory:
    """
    Get the default ThreeZoneMemory instance (lazy singleton).
    
    Returns:
        ThreeZoneMemory instance
    """
    global _default_memory
    if _default_memory is None:
        _default_memory = ThreeZoneMemory()
    return _default_memory
