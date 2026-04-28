"""Tests for CognitiveOrchestrator - Middle Layer Validation.

Validates:
1. Inheritance from ChatService works correctly
2. Entropy calculation produces expected values
3. Zone classification follows threshold rules
4. Orchestrator preserves ChatService behavior
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.services.cognitive_orchestrator import (
    CognitiveOrchestrator,
    CognitiveZone,
    CognitiveLens,
    calculate_entropy,
    classify_zone,
    create_orchestrator,
)
from backend.services.chat_service import ChatService


# --- Entropy Calculation Tests ---

def test_entropy_empty_string():
    """Empty string should have zero entropy."""
    assert calculate_entropy("") == 0.0


def test_entropy_single_word():
    """Single word has max entropy (1 unique / 1 total = 1.0)."""
    assert calculate_entropy("hello") == 1.0


def test_entropy_repeated_words():
    """Repeated words have lower entropy."""
    # "hello hello hello" = 1 unique / 3 total = 0.333...
    entropy = calculate_entropy("hello hello hello")
    assert 0.3 <= entropy <= 0.4


def test_entropy_diverse_text():
    """Diverse text has higher entropy."""
    # All unique words = high entropy
    entropy = calculate_entropy("the quick brown fox jumps")
    assert entropy == 1.0


def test_entropy_mixed_text():
    """Mixed repetition produces mid-range entropy."""
    # "hello world hello" = 2 unique / 3 total = 0.666...
    entropy = calculate_entropy("hello world hello")
    assert 0.6 <= entropy <= 0.7


# --- Zone Classification Tests ---

def test_classify_zone_high_entropy():
    """High entropy (>0.7) routes to ACTIVE zone."""
    assert classify_zone(0.8) == CognitiveZone.ACTIVE
    assert classify_zone(0.95) == CognitiveZone.ACTIVE
    assert classify_zone(1.0) == CognitiveZone.ACTIVE


def test_classify_zone_mid_entropy():
    """Mid entropy (0.3-0.7) routes to PATTERN zone."""
    assert classify_zone(0.5) == CognitiveZone.PATTERN
    assert classify_zone(0.31) == CognitiveZone.PATTERN
    assert classify_zone(0.7) == CognitiveZone.PATTERN


def test_classify_zone_low_entropy():
    """Low entropy (<0.3) routes to ARCHIVED zone."""
    assert classify_zone(0.1) == CognitiveZone.ARCHIVED
    assert classify_zone(0.0) == CognitiveZone.ARCHIVED
    assert classify_zone(0.29) == CognitiveZone.ARCHIVED


def test_classify_zone_boundary_high():
    """Boundary test: 0.71 should be ACTIVE."""
    assert classify_zone(0.71) == CognitiveZone.ACTIVE


def test_classify_zone_boundary_low():
    """Boundary test: 0.3 should be ARCHIVED."""
    assert classify_zone(0.3) == CognitiveZone.ARCHIVED


# --- Orchestrator Inheritance Tests ---

def test_orchestrator_inherits_chat_service():
    """CognitiveOrchestrator must inherit from ChatService."""
    assert issubclass(CognitiveOrchestrator, ChatService)


def test_orchestrator_initialization():
    """Orchestrator initializes with adapter and default lens."""
    mock_adapter = MagicMock()
    orch = CognitiveOrchestrator(mock_adapter)
    
    assert orch.ai_adapter == mock_adapter
    assert orch.default_lens == CognitiveLens.NEUROTYPICAL


def test_orchestrator_custom_lens():
    """Orchestrator accepts custom default lens."""
    mock_adapter = MagicMock()
    orch = CognitiveOrchestrator(mock_adapter, default_lens=CognitiveLens.ADHD_BURST)
    
    assert orch.default_lens == CognitiveLens.ADHD_BURST


def test_orchestrator_zone_metrics_initial():
    """Zone metrics start at zero."""
    mock_adapter = MagicMock()
    orch = CognitiveOrchestrator(mock_adapter)
    
    metrics = orch.get_zone_metrics()
    assert metrics["total_processed"] == 1  # Avoids division by zero
    for zone_data in metrics["zone_distribution"].values():
        assert zone_data["count"] == 0


# --- Factory Function Tests ---

def test_create_orchestrator_default():
    """Factory creates orchestrator with neurotypical lens by default."""
    mock_adapter = MagicMock()
    orch = create_orchestrator(mock_adapter)
    
    assert isinstance(orch, CognitiveOrchestrator)
    assert orch.default_lens == CognitiveLens.NEUROTYPICAL


def test_create_orchestrator_adhd():
    """Factory creates orchestrator with ADHD lens."""
    mock_adapter = MagicMock()
    orch = create_orchestrator(mock_adapter, lens="adhd")
    
    assert orch.default_lens == CognitiveLens.ADHD_BURST


def test_create_orchestrator_case_insensitive():
    """Factory handles case-insensitive lens names."""
    mock_adapter = MagicMock()
    orch = create_orchestrator(mock_adapter, lens="AUTISM")
    
    assert orch.default_lens == CognitiveLens.AUTISM_PRECISION


# --- Async Process Message Tests ---

@pytest.mark.asyncio
async def test_orchestrator_process_message_returns_response():
    """Orchestrator.process_message returns valid response with metadata."""
    mock_adapter = AsyncMock()
    mock_adapter.chat.return_value = {
        "id": "test-123",
        "choices": [{
            "message": {"content": "Hello from mock AI"}
        }]
    }
    
    orch = CognitiveOrchestrator(mock_adapter)
    response = await orch.process_message("test input")
    
    assert "choices" in response
    assert "_cognitive_metadata" in response
    assert "input_entropy" in response["_cognitive_metadata"]
    assert "output_zone" in response["_cognitive_metadata"]


@pytest.mark.asyncio
async def test_orchestrator_preserves_parent_behavior():
    """Orchestrator calls parent's AI adapter correctly."""
    mock_adapter = AsyncMock()
    mock_adapter.chat.return_value = {
        "id": "test-456",
        "choices": [{
            "message": {"content": "Response text"}
        }]
    }
    
    orch = CognitiveOrchestrator(mock_adapter)
    await orch.process_message("hello world", context="system prompt")
    
    # Verify adapter was called
    mock_adapter.chat.assert_called_once()
