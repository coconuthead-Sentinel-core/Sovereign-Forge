"""Cognitive Orchestrator - Enhanced Middle Layer for Sentinel Forge.

Extends ChatService with three-zone memory, symbolic processing, and
neurodivergent cognitive lenses while preserving all existing behavior.

Architecture:
    api.py → CognitiveOrchestrator → AI Adapter → cosmos_repo
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    Active      Pattern      Archived
    Memory       Emerge       Storage
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List

from backend.services.chat_service import ChatService
from backend.domain.models import (
    Note,
    ZonedNote,
    MemoryZone,
    CognitiveLens,
    ZoneMetrics,
    SymbolicMetadata,
    SymbolMatch,
)
from backend.services.memory_zones import (
    ThreeZoneMemory,
    calculate_entropy,
    classify_zone,
    get_memory_manager,
)
from backend.services.glyph_processor import (
    SymbolPatternMatcher,
    get_symbol_pattern_matcher,
)
from backend.services.glyph_parser import (
    parse_symbol_sequence,
    get_concept_for_symbol,
)
from backend.services.adhd_lens import (
    ADHDLens,
    create_adhd_lens,
)
from backend.services.autism_lens import (
    AutismLens,
    create_autism_lens,
)
from backend.services.dyslexia_lens import (
    DyslexiaLens,
    create_dyslexia_lens,
)
from backend.infrastructure.cosmos_repo import cosmos_repo
from backend.eventbus import bus

logger = logging.getLogger(__name__)


# Re-export for backward compatibility with existing tests
CognitiveZone = MemoryZone  # Alias


# --- Main Orchestrator ---

class CognitiveOrchestrator(ChatService):
    """
    Enhanced middle layer orchestrating the Cognitive Pipeline:
    
    1. Input Analysis (entropy calculation)
    2. Zone Classification (active/pattern/crystal)
    3. Context Retrieval (zone-aware memory)
    4. AI Processing (lens-adjusted generation)
    5. Memory Consolidation (zone-tagged storage)
    6. Event Publishing (real-time updates)
    
    Inherits all ChatService behavior - safe extension.
    """
    
    def __init__(
        self,
        ai_adapter,
        default_lens: CognitiveLens = CognitiveLens.NEUROTYPICAL,
        memory_manager: Optional[ThreeZoneMemory] = None,
        symbol_matcher: Optional[SymbolPatternMatcher] = None,
    ):
        """
        Initialize CognitiveOrchestrator.

        Args:
            ai_adapter: Mock or Azure OpenAI adapter (inherited)
            default_lens: Default cognitive processing mode
            memory_manager: Three-zone memory manager (defaults to shared instance)
            symbol_matcher: Symbol pattern matcher for symbolic pattern recognition
        """
        super().__init__(ai_adapter)
        self.default_lens = default_lens
        self.memory_manager = memory_manager or get_memory_manager()
        self.symbol_matcher = symbol_matcher or get_symbol_pattern_matcher()
        self.adhd_lens = create_adhd_lens()
        self.autism_lens = create_autism_lens()
        self.dyslexia_lens = create_dyslexia_lens()
        self._zone_counts = {zone: 0 for zone in CognitiveZone}
        logger.info(f"CognitiveOrchestrator initialized with lens: {default_lens.value}")

    async def process_message(
        self,
        user_message: str,
        context: str = "",
        lens: Optional[CognitiveLens] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through the enhanced Cognitive Pipeline.
        
        Extends ChatService.process_message with:
        - Entropy-based zone classification
        - Symbolic pattern recognition
        - Lens-adjusted processing
        - Zone transition events
        
        Args:
            user_message: The user's input text
            context: Optional system context
            lens: Cognitive lens to apply (defaults to self.default_lens)
        
        Returns:
            Standard chat completion response with added zone metadata
        """
        active_lens = lens or self.default_lens
        
        # 1. Calculate input entropy
        input_entropy = calculate_entropy(user_message)
        input_zone = classify_zone(input_entropy)
        
        logger.debug(f"Input entropy: {input_entropy:.2f} -> Zone: {input_zone.value}")

        # 2. Process symbolic patterns
        symbolic_metadata = self.symbol_matcher.process_text(user_message)

        logger.debug(f"Symbolic processing: {len(symbolic_metadata.matched_symbols)} matches, "
                    f"confidence: {symbolic_metadata.processing_confidence:.2f}")

        # 2.5. Parse symbol sequences in the message
        symbol_parse_result = parse_symbol_sequence(user_message)

        logger.debug(f"Symbol parsing: {symbol_parse_result['parsed_count']} symbols parsed")
        
        # 3. Apply lens transformation to context (placeholder for future enhancement)
        adjusted_context = self._apply_lens(context, active_lens)
        
        # 4. Call parent's AI processing (preserves existing behavior)
        try:
            response = await super().process_message(user_message, adjusted_context)
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            raise
        
        # 5. Extract response text and calculate output entropy
        choices = response.get("choices", [])
        if choices:
            ai_text = choices[0].get("message", {}).get("content", "")
            output_entropy = calculate_entropy(ai_text)
            output_zone = classify_zone(output_entropy)
        else:
            ai_text = ""
            output_entropy = 0.0
            output_zone = CognitiveZone.ARCHIVED
        
        # 6. Update zone counts
        self._zone_counts[output_zone] += 1
        
        # 7. Publish zone event (for real-time dashboards)
        self._publish_zone_event(
            note_id=response.get("id", "unknown"),
            input_zone=input_zone,
            output_zone=output_zone,
            entropy=output_entropy,
        )
        
        # 8. Publish symbolic event if matches found
        if symbolic_metadata.matched_symbols:
            self._publish_symbolic_event(
                note_id=response.get("id", "unknown"),
                symbolic_metadata=symbolic_metadata,
            )

        # 8.5. Publish symbol parsing event if symbols found
        if symbol_parse_result["parsed"]:
            self._publish_symbol_parse_event(
                note_id=response.get("id", "unknown"),
                symbol_data=symbol_parse_result,
            )

        # 9. Add cognitive metadata to response
        response["_cognitive_metadata"] = {
            "input_entropy": round(input_entropy, 3),
            "output_entropy": round(output_entropy, 3),
            "input_zone": input_zone.value,
            "output_zone": output_zone.value,
            "lens_applied": active_lens.value,
            "symbolic_matches": len(symbolic_metadata.matched_symbols),
            "dominant_topic": symbolic_metadata.dominant_topic,
            "symbolic_tags": list(symbolic_metadata.symbolic_tags),
            "symbolic_confidence": round(symbolic_metadata.processing_confidence, 3),
            "parsed_symbols": symbol_parse_result["parsed_count"],
            "symbol_concepts": symbol_parse_result["concepts"],
        }
        
        return response

    def _apply_lens(self, context: str, lens: CognitiveLens) -> str:
        """
        Apply cognitive lens transformation to context.
        
        Now implements ADHD Burst, Autism Precision, and Dyslexia Spatial lenses.
        """
        if lens == CognitiveLens.ADHD_BURST:
            # Apply ADHD lens transformation
            transformed = self.adhd_lens.transform_context(context)
            logger.debug("Applied ADHD Burst lens transformation")
            return transformed
        elif lens == CognitiveLens.AUTISM_PRECISION:
            # Apply Autism lens transformation
            transformed = self.autism_lens.transform_context(context)
            logger.debug("Applied Autism Precision lens transformation")
            return transformed
        elif lens == CognitiveLens.DYSLEXIA_SPATIAL:
            # Apply Dyslexia lens transformation
            transformed = self.dyslexia_lens.transform_context(context)
            logger.debug("Applied Dyslexia Spatial lens transformation")
            return transformed
        
        # Default: return context unchanged
        return context

    def _publish_zone_event(
        self,
        note_id: str,
        input_zone: CognitiveZone,
        output_zone: CognitiveZone,
        entropy: float,
    ) -> None:
        """Publish zone transition event to EventBus."""
        event = {
            "type": "zone.classified",
            "data": {
                "note_id": note_id,
                "input_zone": input_zone.value,
                "output_zone": output_zone.value,
                "entropy": round(entropy, 3),
                "zone_counts": {k.value: v for k, v in self._zone_counts.items()},
            }
        }
        try:
            bus.publish(event, topic="cognitive")
        except Exception as e:
            logger.warning(f"Failed to publish zone event: {e}")

    def _publish_symbolic_event(
        self,
        note_id: str,
        symbolic_metadata: SymbolicMetadata,
    ) -> None:
        """Publish symbolic pattern match event to EventBus."""
        if not symbolic_metadata.matched_symbols:
            return

        event = {
            "type": "symbolic.matched",
            "data": {
                "note_id": note_id,
                "matched_symbols": [
                    {
                        "shape": symbol.shape,
                        "topic": symbol.topic,
                        "confidence": round(symbol.confidence, 3),
                        "matched_seeds": symbol.matched_seeds,
                    }
                    for symbol in symbolic_metadata.matched_symbols
                ],
                "dominant_topic": symbolic_metadata.dominant_topic,
                "symbolic_tags": list(symbolic_metadata.symbolic_tags),
                "processing_confidence": round(symbolic_metadata.processing_confidence, 3),
            }
        }
        try:
            bus.publish(event, topic="symbolic")
        except Exception as e:
            logger.warning(f"Failed to publish symbolic event: {e}")

    def _publish_symbol_parse_event(
        self,
        note_id: str,
        symbol_data: Dict[str, Any],
    ) -> None:
        """Publish symbol parsing event to EventBus."""
        if not symbol_data.get("parsed", False):
            return

        event = {
            "type": "symbol.parsed",
            "data": {
                "note_id": note_id,
                "parsed_symbols": symbol_data["glyphs"],
                "concepts": symbol_data["concepts"],
                "parsed_count": symbol_data["parsed_count"],
                "sequence_length": symbol_data["sequence_length"],
            }
        }
        try:
            bus.publish(event, topic="symbol")
        except Exception as e:
            logger.warning(f"Failed to publish symbol parse event: {e}")

    def get_zone_metrics(self) -> Dict[str, Any]:
        """Return current zone distribution metrics."""
        total = sum(self._zone_counts.values()) or 1
        return {
            "total_processed": total,
            "zone_distribution": {
                zone.value: {
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                }
                for zone, count in self._zone_counts.items()
            },
            "default_lens": self.default_lens.value,
        }


# --- Factory Function (Optional convenience) ---

def create_orchestrator(ai_adapter, lens: str = "neurotypical") -> CognitiveOrchestrator:
    """
    Factory function to create CognitiveOrchestrator with string lens name.
    
    Args:
        ai_adapter: The AI adapter (Mock or Azure)
        lens: Lens name as string ("neurotypical", "adhd", "autism", "dyslexia")
    
    Returns:
        Configured CognitiveOrchestrator instance
    """
    lens_map = {
        "neurotypical": CognitiveLens.NEUROTYPICAL,
        "adhd": CognitiveLens.ADHD_BURST,
        "autism": CognitiveLens.AUTISM_PRECISION,
        "dyslexia": CognitiveLens.DYSLEXIA_SPATIAL,
    }
    cognitive_lens = lens_map.get(lens.lower(), CognitiveLens.NEUROTYPICAL)
    return CognitiveOrchestrator(ai_adapter, default_lens=cognitive_lens)
