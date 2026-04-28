# Sentinel Forge - Cognitive Architecture

## Overview

Sentinel Forge is a neurodivergent-aware AI orchestration platform that extends FastAPI with three-zone memory management, symbolic processing, and adaptive cognitive lenses. The system processes user input through entropy-based zone classification, applies neurodivergent processing modes, and maintains real-time observability.

## Core Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │───▶│ Cognitive        │───▶│ AI Adapter      │
│   REST/WebSocket│    │ Orchestrator     │    │ (Azure/Mock)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Memory Zones     │
                       │ Active           │
                       │ Pattern          │
                       │ Archived         │
                       └──────────────────┘
```

## Three-Zone Memory System

### Zone Classification
Memory is classified based on Shannon entropy thresholds:

- **Active Zone** (`entropy > 0.7`): High-entropy, novel content requiring real-time processing
- **Pattern Zone** (`0.3 < entropy <= 0.7`): Emerging patterns, semi-stable content
- **Archived Zone** (`entropy <= 0.3`): Low-entropy, stable patterns for long-term storage

### Zone Routing
- **Active**: Immediate AI processing with lens adaptation
- **Pattern**: Consolidated storage with pattern analysis
- **Archived**: Archival storage with retrieval optimization

### Metrics Tracking
Zone distribution is tracked in `CognitiveOrchestrator._zone_counts` and exposed via `get_zone_metrics()`:

```python
{
    "total_processed": 150,
    "zone_distribution": {
        "active": {"count": 45, "percentage": 30.0},
        "pattern": {"count": 60, "percentage": 40.0},
        "archived": {"count": 45, "percentage": 30.0}
    }
}
```

## Neurodivergent Cognitive Lenses

### ADHD Burst Lens (`adhd_lens.py`)
- **Purpose**: Rapid context-switching for high-stimulation processing
- **Features**:
  - 50-word chunking with bullet-point formatting
  - Action word emphasis (`BULLET_MARKERS`, `ACTION_WORDS`)
  - Burst processing for quick information intake
- **When Applied**: High-entropy content requiring fast processing

### Autism Precision Lens (`autism_lens.py`)
- **Purpose**: Detail-focused processing with explicit structure
- **Features**:
  - Explicit categorization and relationship indicators
  - Structure enhancement for logical flow
  - Pattern recognition for consistency
- **When Applied**: Complex structured content needing clarity

### Dyslexia Spatial Lens (`dyslexia_lens.py`)
- **Purpose**: Multi-dimensional processing with visual anchors
- **Features**:
  - Spatial anchors and navigation paths
  - Visual chunking with color indicators
  - Overview maps for content structure
- **When Applied**: Content requiring spatial organization

### Lens Usage Tracking
Lens application is tracked in `CognitiveOrchestrator._lens_counts`:

```python
{
    "lens_usage": {
        "neurotypical": {"count": 50, "percentage": 33.3},
        "adhd": {"count": 40, "percentage": 26.7},
        "autism": {"count": 35, "percentage": 23.3},
        "dyslexia": {"count": 25, "percentage": 16.7}
    }
}
```

## Symbolic Processing Pipeline

### Symbol Pattern Processor (`symbol_processor.py`)
- **Input**: Raw text content
- **Processing**: Pattern matching against `symbols_pack.json`
- **Output**: `SymbolicMetadata` with matched symbols and confidence scores

### Symbol Sequence Parser (`symbol_parser.py`)
- **Input**: Text with embedded symbol sequences
- **Processing**: Parse symbol syntax (e.g., `[APEX:action]`, `[CORE:process]`)
- **Output**: Parsed concepts and relationships

### Event Topics
- **cognitive**: Zone transitions and processing events
- **symbolic**: Symbol matches and pattern recognition
- **symbol**: Parsed symbol sequences and concepts

### Payload Schema
```json
{
    "type": "cognitive.zone_transition",
    "data": {
        "note_id": "uuid",
        "input_zone": "active",
        "output_zone": "pattern",
        "entropy": 0.65,
        "timestamp": 1234567890
    }
}
```

## Real-Time Bridge (WebSocket)

### Endpoints
- **`/ws/cognitive`**: Combined cognitive events + periodic metrics
- **`/ws/metrics`**: Legacy metrics endpoint (2s intervals)
- **`/ws/events`**: Event streaming

### Metrics Publishing
- **Frequency**: Every 2 seconds
- **Payload**: Full zone metrics + lens usage + symbolic counts
- **Schema**:
```json
{
    "type": "cognitive.metrics",
    "data": {
        "zone_metrics": {
            "total_processed": 150,
            "zone_distribution": {...},
            "lens_usage": {...},
            "symbolic_matches": 23,
            "default_lens": "neurotypical"
        },
        "timestamp": 1234567890
    }
}
```

### Client Integration
Dashboard connects via WebSocket and updates UI elements:
- Zone percentages in Cognitive Zones card
- Symbolic match counts
- Real-time lens usage visualization

## Extensibility

### Adding New Symbols
1. Update `data/symbols_pack.json` with new patterns
2. Test via `SymbolPatternMatcher.process_text()`
3. Deploy and monitor symbolic match rates

### Adding New Lenses
1. Create new lens class in `backend/services/`
2. Implement `transform_context()` method
3. Add to `CognitiveOrchestrator.__init__()`
4. Update `CognitiveLens` enum
5. Add tests in `tests/test_*_lens.py`

### Custom Metrics
Extend `get_zone_metrics()` to include domain-specific counters:
- Response quality scores
- Processing latency per lens
- Memory consolidation rates

## Configuration

### Environment Variables
- `MOCK_AI=true`: Enable mock AI responses
- `COSMOS_KEY`: Azure Cosmos DB connection
- `AOAI_ENDPOINT`: Azure OpenAI endpoint
- `API_KEY`: WebSocket authentication

### Dependencies
- **Core**: FastAPI, Pydantic, Azure SDKs
- **AI**: Azure OpenAI, llama-stack (optional)
- **Testing**: pytest, Azure AI Evaluation
- **Memory**: Custom three-zone implementation

## Testing Strategy

### Unit Tests
- Lens transformation accuracy
- Zone classification entropy thresholds
- Symbolic pattern matching

### Integration Tests
- Full CognitiveOrchestrator pipeline
- WebSocket event publishing
- Memory zone transitions

### Evaluation
- Azure AI Evaluation SDK for response quality
- Custom metrics for cognitive performance
- A/B testing across different lens configurations

## Performance Considerations

### Memory Management
- Zone-based storage prevents memory bloat
- Entropy thresholds prevent over-classification
- EventBus uses queues to prevent blocking

### Scalability
- Stateless orchestrator design
- Shared memory manager instance
- WebSocket connection pooling

### Monitoring
- Real-time metrics via WebSocket
- Zone distribution histograms
- Lens usage analytics
- Symbolic processing confidence scores