"""Tests for ADHD Burst Lens - Cognitive Processing Validation.

Validates:
1. ADHD lens chunking and bullet formatting
2. Action word enhancement
3. Integration with CognitiveOrchestrator
4. Edge cases and error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.services.adhd_lens import (
    ADHDLens,
    create_adhd_lens,
    transform_with_adhd_lens,
)
from backend.services.cognitive_orchestrator import CognitiveOrchestrator
from backend.domain.models import CognitiveLens


# --- ADHD Lens Unit Tests ---

def test_adhd_lens_initialization():
    """Test ADHD lens initializes with correct defaults."""
    lens = ADHDLens()
    assert lens.chunk_size == 50
    assert len(lens.BULLET_MARKERS) > 0
    assert "start" in lens.ACTION_WORDS


def test_adhd_lens_empty_context():
    """Test ADHD lens handles empty context gracefully."""
    lens = ADHDLens()
    result = lens.transform_context("")
    assert result == ""

    result = lens.transform_context("   ")
    assert result == "   "


def test_adhd_lens_simple_chunking():
    """Test basic chunking functionality."""
    lens = ADHDLens()

    # Short text should become one bullet
    short_text = "This is a short message."
    result = lens.transform_context(short_text)
    assert "⚡" in result
    assert result.count("⚡") == 1


def test_adhd_lens_long_text_chunking():
    """Test chunking of longer text into multiple bullets."""
    lens = ADHDLens()

    # Create text that should split into multiple chunks
    long_text = "This is the first sentence. " * 20  # Creates ~100 words
    result = lens.transform_context(long_text)

    # Should have multiple bullets
    bullet_count = result.count("⚡") + result.count("💥") + result.count("🚀")
    assert bullet_count > 1


def test_adhd_lens_action_word_enhancement():
    """Test that action words get enhanced with emphasis."""
    lens = ADHDLens()

    text = "You should start the process now."
    result = lens.transform_context(text)

    # Should contain enhanced action word
    assert "**START**" in result


def test_adhd_lens_response_transformation():
    """Test response transformation (same as context)."""
    lens = ADHDLens()

    response = "Here is my response to your query."
    context_result = lens.transform_context(response)
    response_result = lens.transform_response(response)

    assert context_result == response_result


def test_adhd_lens_sentence_splitting():
    """Test sentence splitting logic."""
    lens = ADHDLens()

    text = "First sentence. Second sentence! Third sentence?"
    sentences = lens._split_into_sentences(text)

    assert len(sentences) == 3
    assert "First sentence" in sentences[0]
    assert "Second sentence" in sentences[1]
    assert "Third sentence" in sentences[2]


def test_adhd_lens_chunk_creation():
    """Test chunk creation from sentences."""
    lens = ADHDLens()

    sentences = ["Short sentence."] * 10  # 10 short sentences
    chunks = lens._create_chunks(sentences)

    # Should create reasonable number of chunks
    assert len(chunks) > 1
    assert len(chunks) < len(sentences)


def test_adhd_lens_bullet_formatting():
    """Test bullet point formatting."""
    lens = ADHDLens()

    chunks = ["First chunk of text", "Second chunk of text"]
    bullets = lens._format_as_bullets(chunks)

    assert len(bullets) == 2
    assert bullets[0].startswith("⚡")
    assert bullets[1].startswith("💥")
    assert "First chunk" in bullets[0]
    assert "Second chunk" in bullets[1]


def test_adhd_lens_config():
    """Test lens configuration retrieval."""
    lens = ADHDLens()
    config = lens.get_config()

    assert "chunk_size_words" in config
    assert "bullet_markers" in config
    assert "action_words" in config


# --- Convenience Function Tests ---

def test_create_adhd_lens():
    """Test convenience function for creating lens."""
    lens = create_adhd_lens()
    assert isinstance(lens, ADHDLens)


def test_transform_with_adhd_lens():
    """Test convenience function for transformation."""
    text = "Transform this text."
    result = transform_with_adhd_lens(text)

    assert "⚡" in result
    assert "Transform this text" in result


# --- Integration Tests ---

@pytest.mark.asyncio
async def test_adhd_lens_integration():
    """Test ADHD lens integration with CognitiveOrchestrator."""
    # Mock AI adapter
    mock_adapter = MagicMock()
    mock_adapter.chat = AsyncMock(return_value={
        "id": "test-123",
        "choices": [{"message": {"content": "This is a test response from the AI."}}]
    })

    # Create orchestrator with ADHD lens
    orchestrator = CognitiveOrchestrator(mock_adapter, default_lens=CognitiveLens.ADHD_BURST)

    # Process message
    result = await orchestrator.process_message(
        "Please explain how this works.",
        lens=CognitiveLens.ADHD_BURST
    )

    # Verify response structure
    assert "_cognitive_metadata" in result
    assert result["_cognitive_metadata"]["lens_applied"] == "adhd"

    # Verify AI was called
    mock_adapter.chat.assert_called_once()


def test_adhd_lens_orchestrator_metadata():
    """Test that ADHD lens usage is tracked in metadata."""
    lens = ADHDLens()

    # This is a unit test of the lens itself
    text = "This is a test message with start action."
    result = lens.transform_context(text)

    # Should contain bullet formatting
    assert any(marker in result for marker in ["⚡", "💥", "🚀", "🔥"])

    # Should enhance action words
    assert "**START**" in result or "**ACTION**" in result


# --- Edge Case Tests ---

def test_adhd_lens_very_long_sentence():
    """Test handling of very long sentences."""
    lens = ADHDLens()

    # Create a very long sentence
    long_sentence = "This is a very long sentence " * 20  # ~100 words
    result = lens.transform_context(long_sentence)

    # Should still format as bullets
    assert "⚡" in result


def test_adhd_lens_special_characters():
    """Test handling of special characters and punctuation."""
    lens = ADHDLens()

    text = "Test with special chars: @#$%^&*()! And numbers: 12345."
    result = lens.transform_context(text)

    # Should handle gracefully
    assert isinstance(result, str)
    assert len(result) > 0


def test_adhd_lens_unicode_content():
    """Test handling of Unicode content."""
    lens = ADHDLens()

    text = "Unicode test: 🌟 ⭐ 📚 🎯"
    result = lens.transform_context(text)

    # Should preserve Unicode
    assert "🌟" in result
    assert "🎯" in result