# Portfolio Brief — Sovereign Forge (Forge Trilogy Capstone)

> **One-page recruiter overview.** Architecture detail in [`../README.md`](../README.md) and [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Polish-pass changelog in [`../POLISH_NOTES.md`](../POLISH_NOTES.md).

## TL;DR

**Multi-platform orchestration gateway** that takes a single user request and fans it out in parallel via `asyncio.gather()` to both downstream platforms — Quantum Nexus Forge (port 5000, symbolic processing) and Sentinel-Forge (port 8000, cognitive lens processing) — then merges the dual-platform outputs into one coherent response. Users interact with one product; three engines work underneath.

## Naming

Canonical public name: **Sovereign Forge**.
This repo is the gateway layer and should not be used as an alias for either downstream platform.

## Role demonstrated

**AI Orchestrator Architect** — explicit asynchronous fan-out coordination across heterogeneous AI services, response merging, gateway service design, accessibility-aware test discipline.

## What this project demonstrates (for hiring review)

| Capability | Evidence in the codebase |
|---|---|
| **Asynchronous parallel fan-out** | `SovereignRouter` uses `asyncio.gather()` to call QNF and Sentinel concurrently; latency = max(t_qnf, t_sentinel), not sum |
| **Heterogeneous service composition** | `PlatformBridge` — async HTTP clients tailored per downstream platform (different APIs, different response shapes) |
| **Response merger pattern** | `ResponseMerger` combines dual-platform outputs into a single coherent payload (canonical industry pattern: ensemble aggregator) |
| **Multi-tier deployment artifact** | `Dockerfile` + `docker-compose.yml` — coordinated container startup with port mapping (9000 / 5000 / 8000) |
| **Accessibility-engineering discipline** | Dedicated test files: `test_adhd_lens.py`, `test_autism_lens.py`, `test_dyslexia_lens.py` — neurodivergent-lens coverage as first-class quality criterion |
| **Test breadth** | 13-test pytest suite covering ADHD/autism/dyslexia lenses, cognitive orchestrator, domain models, event bus, glyph-event bridge, glyph processor, memory zones, quantum nexus integration, vectors, WebSocket API |
| **Documentation discipline** | ARCHITECTURE.md + CHECKLIST.md + CONTRIBUTING.md + LICENSE + Makefile — every senior-engineering artifact present |
| **Symbolic + cognitive integration** | `sigma_network_engine.py` + `vector_utils.py` + `quantum_nexus_forge_v5_2_enhanced.py` — bridges symbolic and embedding-vector layers |

## Architecture (lifted from `README.md` for at-a-glance review)

```
User Request
     │
     ▼
Sovereign Forge (port 9000)
     │
     ├──► Quantum Nexus Forge  (port 5000) — symbolic / logical
     │
     └──► Sentinel Forge       (port 8000) — cognitive lens
              │
              ▼
       Response Merger
              │
              ▼
     Unified Response
```

### Gateway services
- **PlatformBridge** — async HTTP clients for QNF and Sentinel
- **ResponseMerger** — dual-platform output combination
- **SovereignRouter** — `asyncio.gather()` parallel dispatch

## Why this is the trilogy capstone

| Trilogy member | Role |
|---|---|
| **Quantum Nexus Forge** (LIB-PROJ-003) | Standalone MVP — multi-agent orchestration at proof-of-concept scale |
| **Sentinel-of-sentinel-s-Forge** (LIB-PROJ-001) | Production-grade — FastAPI + Azure OpenAI + Cosmos DB + JWT/RBAC + Stripe + WebSockets |
| **Sovereign Forge (this project — LIB-PROJ-004)** | **Capstone gateway** — fans requests to both downstream platforms in parallel and merges responses |

Together the three demonstrate the **same architectural instincts at three integration scales**: standalone (QNF), production-grade enterprise (Sentinel-Forge), and unified-multi-platform-gateway (this project).

## Differentiators worth naming for HR

1. **`asyncio.gather()` parallel fan-out is non-trivial** — many candidates write sequential awaits and only learn the correct pattern under code review. This codebase demonstrates the right pattern from the start.
2. **Accessibility-engineering as test category** — most projects treat accessibility as documentation; this one has dedicated test files per neurodivergent lens (ADHD / autism / dyslexia).
3. **Heterogeneous response merging** — combining outputs from systems with different APIs into one coherent response is a real architectural skill, not just plumbing.

## Author

**Shannon Brian Kelly** — Healthcare CNA → AI Systems Developer career transition.
Built in collaboration with Claude AI (Anthropic).

## License

See `LICENSE` at project root.

---

*Portfolio Brief v001 — 2026-04-28. Generated during the multi-project portfolio sprint. Available for verification on screen-share at the hiring team's request.*
