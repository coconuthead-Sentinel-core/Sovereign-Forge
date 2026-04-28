# Sovereign Forge — Multi-Platform Orchestration Gateway

**Unified cognitive AI gateway for the Forge Trilogy** | 2025

## Overview

Sovereign Forge is the third platform in the Forge Trilogy. It acts as the
unified orchestration gateway that routes a single user request to both
downstream platforms — **Quantum Nexus Forge** and **Sentinel of Sentinel's Forge** —
in parallel, then merges their outputs into one coherent response.

Users interact with one product. Three engines work underneath.

## Project Identity

The canonical public name for this repo is **Sovereign Forge**.
This is the gateway project in the portfolio set, not an alias for **Quantum Nexus Forge**, **Sentinel-of-sentinel-s-Forge**, or **Sentinel Forge Cognitive AI Orchestrator**.

## Architecture

```
User Request
     │
     ▼
Sovereign Forge (port 9000)
     │
     ├──► Quantum Nexus Forge  (port 5000) — symbolic/logical processing
     │
     └──► Sentinel Forge       (port 8000) — cognitive lens processing
              │
              ▼
       Response Merger
              │
              ▼
     Unified Response
```

### Gateway Services

- **PlatformBridge** — async HTTP clients for QNF and Sentinel
- **ResponseMerger** — combines dual-platform outputs into one payload
- **SovereignRouter** — fans out requests in parallel via `asyncio.gather()`

### Cognitive Processing (inherited)

- **Three-Zone Memory**: HIGH (>0.7 entropy), MEDIUM (0.3–0.7), LOW (<0.3)
- **Cognitive Lenses**: ADHD, Autism, Dyslexia, Dyscalculia, Neurotypical
- **Entropy-based routing**: Shannon entropy classifies input complexity

## Quick Start

### Prerequisites

- Python 3.11+
- Quantum Nexus Forge running on port 5000
- Sentinel of Sentinel's Forge running on port 8000

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Set QNF_BASE_URL and SENTINEL_BASE_URL if not using defaults

# Run Sovereign Forge
uvicorn backend.main:app --reload --port 9000
```

### Environment Variables

```bash
# Platform URLs (defaults shown)
QNF_BASE_URL=http://localhost:5000
SENTINEL_BASE_URL=http://localhost:8000
PLATFORM_TIMEOUT_SECONDS=10.0

# AI Configuration
MOCK_AI=true
AOAI_ENDPOINT=https://your-endpoint.openai.azure.com/

# Database
COSMOS_ENDPOINT=https://your-account.documents.azure.com/
COSMOS_KEY=your-key
```

## API Reference

### Gateway Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/gateway/health` | Health status of both downstream platforms |
| GET | `/api/gateway/metrics` | Combined metrics snapshot from both platforms |
| POST | `/api/gateway/process` | Unified dual-platform processing |

### POST /api/gateway/process

```json
{
  "message": "Explain the concept of entropy",
  "lens": "adhd",
  "context": ""
}
```

**Response:**
```json
{
  "unified_response": "[QuantumNexusForge]\n...\n\n[SentinelForge]\n...",
  "platform_status": {
    "QuantumNexusForge": "online",
    "SentinelForge": "online"
  },
  "merged_metrics": {
    "input_entropy": 0.812,
    "output_entropy": 0.743,
    "combined_symbolic_tags": ["logic", "pattern", "analysis"]
  },
  "degraded_mode": false,
  "qnf": { ... },
  "sentinel": { ... }
}
```

### Degraded Mode

If one platform is offline, Sovereign Forge returns a response from the
available platform with `"degraded_mode": true`. The gateway never
hard-fails due to a single platform being unavailable.

## Project Structure

```
Sovereign Forge/
├── backend/
│   ├── main.py                     # FastAPI app entry (port 9000)
│   ├── api.py                      # REST endpoints (includes gateway routes)
│   ├── services/
│   │   ├── gateway/                # Sovereign Forge core
│   │   │   ├── platform_bridge.py  # Async HTTP clients for QNF + Sentinel
│   │   │   ├── response_merger.py  # Dual-platform response merger
│   │   │   └── sovereign_router.py # Parallel orchestration engine
│   │   ├── cognitive_orchestrator.py
│   │   ├── memory_zones.py
│   │   └── [cognitive lenses]
│   ├── infrastructure/
│   └── adapters/
├── frontend/
├── tests/
├── evaluation/
└── requirements.txt
```

## Performance

**Evaluation Results (inherited baseline — 80 queries):**
- Relevance: 3.94/5.0
- Coherence: 3.99/5.0
- Groundedness: 3.96/5.0

## License

MIT License — Copyright (c) 2025 Shannon Bryan Kelly

## Acknowledgments

Built by Shannon Bryan Kelly in collaboration with Claude AI.
