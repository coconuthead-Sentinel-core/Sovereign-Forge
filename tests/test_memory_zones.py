"""Tests for Three-Zone Memory System (Phase 3).

Validates:
1. MemoryZone and CognitiveLens enums exist in domain
2. ZonedNote serializes correctly with zone/entropy
3. ZonedNote ignores extra fields (no DB leakage)
4. ThreeZoneMemory manager routes correctly
5. ZoneMetrics aggregates properly
"""

import pytest
from unittest.mock import MagicMock

from backend.domain.models import (
    Note,
    ZonedNote,
    MemoryZone,
    CognitiveLens,
    ZoneMetrics,
)
from backend.services.memory_zones import (
    ThreeZoneMemory,
    calculate_entropy,
    classify_zone,
    get_memory_manager,
)


# --- Domain Model Tests ---

def test_memory_zone_enum_values():
    """MemoryZone enum has correct values."""
    assert MemoryZone.ACTIVE.value == "active"
    assert MemoryZone.PATTERN.value == "pattern"
    assert MemoryZone.ARCHIVED.value == "archived"


def test_cognitive_lens_enum_values():
    """CognitiveLens enum has correct values."""
    assert CognitiveLens.NEUROTYPICAL.value == "neurotypical"
    assert CognitiveLens.ADHD_BURST.value == "adhd"
    assert CognitiveLens.AUTISM_PRECISION.value == "autism"
    assert CognitiveLens.DYSLEXIA_SPATIAL.value == "dyslexia"


def test_zoned_note_creation():
    """ZonedNote creates with default zone and entropy."""
    note = ZonedNote(text="Test content", tag="test")
    
    assert note.text == "Test content"
    assert note.tag == "test"
    assert note.zone == MemoryZone.ACTIVE  # default
    assert note.entropy == 0.5  # default
    assert note.lens_applied is None


def test_zoned_note_custom_zone():
    """ZonedNote accepts custom zone and entropy."""
    note = ZonedNote(
        text="Stable pattern",
        tag="memory",
        zone=MemoryZone.ARCHIVED,
        entropy=0.15,
        lens_applied=CognitiveLens.AUTISM_PRECISION,
    )
    
    assert note.zone == MemoryZone.ARCHIVED
    assert note.entropy == 0.15
    assert note.lens_applied == CognitiveLens.AUTISM_PRECISION


def test_zoned_note_inherits_from_note():
    """ZonedNote inherits from Note."""
    assert issubclass(ZonedNote, Note)


def test_zoned_note_serializes_correctly():
    """ZonedNote.model_dump() includes zone fields."""
    note = ZonedNote(
        text="Test",
        tag="test",
        zone=MemoryZone.PATTERN,
        entropy=0.55,
    )
    
    data = note.model_dump()
    
    assert data["text"] == "Test"
    assert data["tag"] == "test"
    assert data["zone"] == "pattern"  # Enum serializes to value
    assert data["entropy"] == 0.55
    assert "id" in data
    assert "created_at" in data


def test_zoned_note_ignores_extra_fields():
    """ZonedNote ignores unknown fields (no DB leakage)."""
    note = ZonedNote(
        text="Test",
        tag="test",
        partitionKey="should_be_ignored",
        _etag="also_ignored",
        unknown_field="dropped",
    )
    
    data = note.model_dump()
    
    assert "partitionKey" not in data
    assert "_etag" not in data
    assert "unknown_field" not in data


def test_zoned_note_entropy_validation():
    """ZonedNote entropy must be between 0.0 and 1.0."""
    # Valid values
    note1 = ZonedNote(text="T", tag="t", entropy=0.0)
    note2 = ZonedNote(text="T", tag="t", entropy=1.0)
    assert note1.entropy == 0.0
    assert note2.entropy == 1.0
    
    # Invalid values should raise validation error
    with pytest.raises(ValueError):
        ZonedNote(text="T", tag="t", entropy=-0.1)
    
    with pytest.raises(ValueError):
        ZonedNote(text="T", tag="t", entropy=1.5)


def test_zone_metrics_creation():
    """ZoneMetrics creates with defaults."""
    metrics = ZoneMetrics()
    
    assert metrics.active_count == 0
    assert metrics.pattern_count == 0
    assert metrics.archived_count == 0
    assert metrics.avg_entropy == 0.0
    assert metrics.last_transition is None


def test_zone_metrics_serializes():
    """ZoneMetrics serializes correctly."""
    metrics = ZoneMetrics(
        active_count=5,
        pattern_count=10,
        archived_count=20,
        avg_entropy=0.45,
        last_transition="active→pattern",
    )
    
    data = metrics.model_dump()
    
    assert data["active_count"] == 5
    assert data["pattern_count"] == 10
    assert data["archived_count"] == 20
    assert data["avg_entropy"] == 0.45
    assert data["last_transition"] == "active→pattern"


# --- Memory Zones Service Tests ---

def test_calculate_entropy_empty():
    """Empty text has zero entropy."""
    assert calculate_entropy("") == 0.0
    assert calculate_entropy("   ") == 0.0


def test_calculate_entropy_single_word():
    """Single word has max entropy."""
    assert calculate_entropy("hello") == 1.0


def test_calculate_entropy_repeated():
    """Repeated words have lower entropy."""
    entropy = calculate_entropy("hello hello hello")
    assert 0.3 <= entropy <= 0.4


def test_classify_zone_high():
    """High entropy routes to ACTIVE."""
    assert classify_zone(0.8) == MemoryZone.ACTIVE
    assert classify_zone(0.71) == MemoryZone.ACTIVE


def test_classify_zone_mid():
    """Mid entropy routes to PATTERN."""
    assert classify_zone(0.5) == MemoryZone.PATTERN
    assert classify_zone(0.31) == MemoryZone.PATTERN


def test_classify_zone_low():
    """Low entropy routes to ARCHIVED."""
    assert classify_zone(0.2) == MemoryZone.ARCHIVED
    assert classify_zone(0.3) == MemoryZone.ARCHIVED


# --- ThreeZoneMemory Manager Tests ---

def test_three_zone_memory_init():
    """ThreeZoneMemory initializes with empty counters."""
    mem = ThreeZoneMemory()
    metrics = mem.get_metrics()
    
    assert metrics.active_count == 0
    assert metrics.pattern_count == 0
    assert metrics.archived_count == 0


def test_three_zone_memory_route():
    """ThreeZoneMemory routes text to correct zone."""
    mem = ThreeZoneMemory()
    
    # High entropy text (all unique words)
    zone, entropy = mem.route_to_zone("the quick brown fox jumps")
    assert zone == MemoryZone.ACTIVE
    assert entropy == 1.0
    
    # Low entropy text (repeated)
    zone, entropy = mem.route_to_zone("yes yes yes yes")
    assert zone == MemoryZone.ARCHIVED
    assert entropy == 0.25


def test_three_zone_memory_create_zoned_note():
    """ThreeZoneMemory creates ZonedNote with correct classification."""
    mem = ThreeZoneMemory()
    
    note = mem.create_zoned_note(
        text="unique diverse content here today",
        tag="test",
        lens=CognitiveLens.ADHD_BURST,
    )
    
    assert isinstance(note, ZonedNote)
    assert note.zone == MemoryZone.ACTIVE  # All unique words
    assert note.entropy == 1.0
    assert note.lens_applied == CognitiveLens.ADHD_BURST


def test_three_zone_memory_metrics_update():
    """ThreeZoneMemory updates metrics after routing."""
    mem = ThreeZoneMemory()
    
    # Route some content
    mem.route_to_zone("unique words here")  # ACTIVE
    mem.route_to_zone("same same same same")  # ARCHIVED
    mem.route_to_zone("mixed mixed unique")  # PATTERN
    
    metrics = mem.get_metrics()
    
    assert metrics.active_count == 1
    assert metrics.archived_count == 1
    assert metrics.pattern_count == 1


def test_three_zone_memory_distribution():
    """ThreeZoneMemory calculates percentage distribution."""
    mem = ThreeZoneMemory()
    
    # Add content to different zones
    mem.route_to_zone("one two three four five")  # ACTIVE (all unique)
    mem.route_to_zone("same same same same")  # ARCHIVED (low entropy)
    
    dist = mem.get_zone_distribution()
    
    assert "active" in dist
    assert "archived" in dist
    # Both zones should have entries
    assert dist["active"] > 0
    assert dist["archived"] > 0


def test_three_zone_memory_reset():
    """ThreeZoneMemory reset clears all metrics."""
    mem = ThreeZoneMemory()
    
    mem.route_to_zone("some text")
    mem.reset_metrics()
    
    metrics = mem.get_metrics()
    assert metrics.active_count == 0
    assert metrics.pattern_count == 0
    assert metrics.archived_count == 0


def test_get_memory_manager_singleton():
    """get_memory_manager returns same instance."""
    # Note: This tests the lazy singleton pattern
    # Reset first to ensure clean state
    import backend.services.memory_zones as mz
    mz._default_memory = None
    
    mem1 = get_memory_manager()
    mem2 = get_memory_manager()
    
    assert mem1 is mem2
