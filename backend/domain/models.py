from typing import Optional, List, Dict, Any, Set
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from datetime import datetime, timezone
from enum import Enum
import uuid
from dataclasses import dataclass


# --- Cognitive Zone Enums (Three-Zone Memory System) ---

class MemoryZone(str, Enum):
    """
    Three-zone memory classification based on entropy thresholds.
    
    ACTIVE: High entropy (>0.7) - Real-time processing, novel content
    PATTERN: Mid entropy (0.3-0.7) - Pattern emergence, semi-stable
    ARCHIVED: Low entropy (<0.3) - Stable storage, well-known patterns
    """
    ACTIVE = "active"           # High entropy - real-time
    PATTERN = "pattern"         # Mid entropy - emerging patterns
    ARCHIVED = "archived"       # Low entropy - stable memory


class CognitiveLens(str, Enum):
    """
    Neurodivergent processing modes for adaptive AI responses.
    
    Each lens adjusts how information is processed and presented.
    """
    NEUROTYPICAL = "neurotypical"   # Baseline processing
    ADHD_BURST = "adhd"             # Rapid context-switching, shorter chunks
    AUTISM_PRECISION = "autism"     # Detail focus, explicit structure
    DYSLEXIA_SPATIAL = "dyslexia"   # Multi-dimensional, symbol-rich


@dataclass
class SymbolMatch:
    """Represents a matched symbol pattern."""
    shape: str
    topic: str
    confidence: float
    matched_seeds: List[str]
    applied_rules: Dict[str, str]


@dataclass
class SymbolicMetadata:
    """Metadata generated from symbolic processing."""
    matched_symbols: List[SymbolMatch]
    dominant_topic: Optional[str]
    symbolic_tags: Set[str]
    processing_confidence: float


class Entity(BaseModel):
    """Base class for all domain entities."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Strict mode: ignore extra fields passed during initialization
    model_config = ConfigDict(extra="ignore")

class Note(Entity):
    """
    A discrete unit of information stored in the Memory Lattice.
    Pure domain model: No database aliases here.
    """
    text: str
    tag: str
    vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ZonedNote(Note):
    """
    A Note enhanced with three-zone memory classification.
    
    Extends Note with:
    - zone: Which memory zone this note belongs to (active/pattern/archived)
    - entropy: Information entropy score (0.0-1.0)
    - lens_applied: Which cognitive lens was used during processing
    - symbolic_metadata: Results from symbol pattern matching
    
    Pure domain model: No database aliases. ConfigDict inherited from Entity.
    """
    zone: MemoryZone = MemoryZone.ACTIVE
    entropy: float = Field(default=0.5, ge=0.0, le=1.0)
    lens_applied: Optional[CognitiveLens] = None
    symbolic_metadata: Optional[SymbolicMetadata] = None
    
    # Inherits model_config = ConfigDict(extra="ignore") from Entity


class ZoneMetrics(BaseModel):
    """
    Aggregated metrics for memory zone distribution.
    Used for real-time dashboard updates.
    """
    active_count: int = 0
    pattern_count: int = 0
    archived_count: int = 0
    avg_entropy: float = 0.0
    last_transition: Optional[str] = None
    
    model_config = ConfigDict(extra="ignore")


class SymbolicMetadata(BaseModel):
    """
    Metadata generated from symbolic processing of text.

    Contains symbol matches, dominant topics, and symbolic tags
    derived from pattern recognition.

    ``matched_symbols`` accepts either SymbolMatch dataclasses (so
    consumers can read ``.shape``, ``.confidence`` directly) or
    plain dicts (for JSON serialization). The model is permissive
    via ``arbitrary_types_allowed`` so the dataclass passes through.

    Backward-compat: legacy callers may pass ``matched_glyphs=`` —
    accepted as an alias via ``populate_by_name``.
    """
    matched_symbols: List[Any] = Field(
        default_factory=list,
        validation_alias=AliasChoices("matched_symbols", "matched_glyphs"),
    )
    dominant_topic: Optional[str] = None
    symbolic_tags: Set[str] = Field(default_factory=set)
    processing_confidence: float = 0.0

    model_config = ConfigDict(
        extra="ignore",
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    @property
    def matched_glyphs(self) -> List[Any]:
        """Legacy alias for ``matched_symbols``."""
        return self.matched_symbols


class MemorySnapshot(Entity):
    """A snapshot of the system's cognitive state."""
    summary: str
    active_nodes: int
    entropy_level: float
