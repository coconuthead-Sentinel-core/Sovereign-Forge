# Sentinel Forge Cognitive AI Orchestration Platform 🌌

![CI](https://github.com/coconuthead-Sentinel-core/sentinel-forge-cognitive-orchestrator/workflows/Python%20application/badge.svg)

**Neurodivergent-Aware Cognitive Orchestration** | December 19, 2025

## 🎯 Mission
Building AI that adapts to diverse cognitive processing styles to promote accessibility and inclusivity. This platform orchestrates cognitive processing through specialized modes for various thinking patterns.

## 🧠 Core Architecture

### Processing Modes (Internal Implementation)
- **Dynamic Burst Mode**: Dynamic burst processing with rapid context-switching
- **Precision Pattern Mode**: Precision pattern recognition with detail-focused analysis
- **Multi-dimensional Symbol Mode**: Multi-dimensional symbol interpretation and spatial cognition
- **Baseline Mode**: Baseline processing for comparison and accessibility

### Three-Zone Memory System
- **🟢 Active Processing**: High-entropy real-time data (>0.7 entropy)
- **🟡 Pattern Emergence**: Mid-entropy pattern recognition (0.3-0.7 entropy)
- **🔴 Crystallized Storage**: Low-entropy stable memory (<0.3 entropy)

### Glyph Processing Engine
- **5 Geometric Primitives**: Tetrahedron, Cube, Octahedron, Dodecahedron, Icosahedron
- **Symbolic Stream Processing**: Interpret emoji sequences as cognitive operations
- **Spatial Cognition**: 3D coordinate system with cognitive elevation mapping

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Azure OpenAI access (optional - mock mode available)

### Installation
```bash
# Clone the repository
git clone https://github.com/coconuthead-Sentinel-core/sentinel-forge-cognitive-orchestrator.git
cd sentinel-forge-cognitive-orchestrator

# Install dependencies
pip install -r requirements.txt

# For development with mock AI
echo "MOCK_AI=true" > .env

# Run the API server
uvicorn backend.main:app --reload --port 8000

# Run evaluation pipeline
python scripts/run_full_eval.py
```

### Basic Usage
```python
from backend.services.cognitive_orchestrator import CognitiveOrchestrator

# Initialize with ADHD processing lens
orchestrator = CognitiveOrchestrator(lens="adhd")

# Process cognitive input
result = orchestrator.process("🌌🔥💫")
print(result.spatial_coordinates)
```

## 📊 Performance Metrics

**Evaluation Results (80 queries processed):**
- **Relevance**: 3.94/5.0
- **Coherence**: 3.99/5.0
- **Groundedness**: 3.96/5.0
- **Overall Quality**: Production-ready

## 🏗️ Project Structure

```
sentinel-forge-cognitive-orchestrator/
├── backend/                          # FastAPI application
│   ├── api.py                       # REST endpoints
│   ├── ws_api.py                    # WebSocket real-time sync
│   ├── services/                    # Business logic
│   │   ├── cognitive_orchestrator.py # Main processing engine
│   │   ├── glyph_processor.py       # Symbol interpretation
│   │   ├── memory_zones.py          # Three-zone memory
│   │   └── adhd_lens.py            # Cognitive lenses
│   ├── infrastructure/              # Data persistence
│   │   └── cosmos_repo.py          # Azure Cosmos DB
│   └── adapters/                    # AI model adapters
│       ├── azure_openai.py         # Azure OpenAI integration
│       └── mock_adapter.py         # Development fallback
├── evaluation/                      # Testing & validation
│   ├── run_evaluation.py           # Full pipeline test
│   ├── collect_responses.py        # Response gathering
│   └── eval_results.json           # Performance metrics
├── frontend/                        # Web dashboard
│   ├── dashboard.html              # Real-time metrics UI
│   └── app.js                      # Client-side logic
├── scripts/                         # Development utilities
│   ├── smoke_test.py               # Health checks
│   └── init_cosmos.py              # Database setup
└── tests/                          # Unit test suite
    ├── test_cognitive_orchestrator.py
    └── test_glyph_processor.py
```

## 🔧 Configuration

### Environment Variables
```bash
# AI Configuration
MOCK_AI=true                          # Use mock responses for development
AOAI_ENDPOINT=https://your-endpoint.openai.azure.com/
API_KEY=your-guard-key                # For API endpoint protection

# Database (Cosmos DB)
COSMOS_ENDPOINT=https://your-account.documents.azure.com/
COSMOS_KEY=your-key                   # Empty = auto-mock mode

# Development
PYTHONPATH=/path/to/project
```

### Azure Integration
- **Cosmos DB**: Document storage with automatic mock fallback
- **Azure OpenAI**: GPT-4 integration with AAD authentication
- **Application Insights**: Optional telemetry and monitoring

## 🧪 Testing

### Run Full Test Suite
```bash
# Unit tests
pytest tests/

# Integration tests
python scripts/smoke_test.py

# Evaluation pipeline
python scripts/run_full_eval.py
```

### Test Coverage
- Cognitive lens processing accuracy
- Memory zone transitions
- Glyph pattern recognition
- WebSocket real-time sync
- API endpoint validation

## 🌐 API Reference

### REST Endpoints
- `GET /api/status` - Health check
- `POST /api/chat` - Cognitive processing
- `GET /api/metrics` - Performance dashboard
- `POST /api/glyph/process` - Symbol interpretation

### WebSocket Events
- `/ws/sync` - Real-time cognitive state
- `/ws/metrics` - Live performance updates
- `/ws/events` - System notifications

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Install dependencies: `pip install -r requirements.txt`
4. Run tests: `pytest tests/`
5. Submit pull request

### Code Standards
- Type hints required
- Docstrings for public methods
- Pydantic models for data validation
- Async/await for I/O operations

## 📈 Roadmap

### Completed ✅
- Cognitive lens implementations (4 lenses)
- Three-zone memory system
- Glyph processing engine
- Real-time dashboard
- Evaluation pipeline
- Production deployment ready

### In Progress 🚧
- Azure SDK live scoring integration
- Voice interface prototype
- Multi-region deployment

### Future Vision 🎯
- Community lens contributions
- Mobile applications
- Research partnerships
- Enterprise integrations

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with ❤️ by Shannon Bryan Kelly (Coconut Head) in collaboration with Claude AI.

**Special Thanks:**
- Neurodivergent community for inspiration
- Open source contributors
- Cognitive science researchers

---

*Making AI accessible to all cognitive styles, one framework at a time.* 🧠✨

**December 19, 2025** - Repository published and CI active.

Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): 2026-01-01 10:18:15
Current User's Login: coconuthead-Sentinel-core