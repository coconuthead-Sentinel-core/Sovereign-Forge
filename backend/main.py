import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as api_router
from .ws_api import router as ws_router
from .adapters.azure_openai import AzureCognitiveTokenProvider
from .infrastructure.cosmos_repo import CosmosDBRepository
import uvicorn
import asyncio

# Set event loop policy for Windows
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sovereign-forge")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Cosmos DB Repository (will use Mock DB mode if unavailable)
    await CosmosDBRepository.initialize()
    logger.info("Cosmos DB Repository initialized.")

    # Warm up token to fail-fast on bad identity/env.
    provider = AzureCognitiveTokenProvider()
    try:
        await provider.get_token()
        logger.info("AAD token warmup successful.")
    except Exception as exc:
        logger.warning("AAD warmup failed: %s", exc)
    finally:
        await provider.aclose()
    
    yield
    
    # Cleanup on shutdown
    await CosmosDBRepository.close()

app = FastAPI(
    title="Sovereign Forge — Multi-Platform Orchestration Gateway",
    description=(
        "Unified gateway that routes requests to Quantum Nexus Forge and "
        "Sentinel of Sentinel's Forge in parallel, then merges their outputs "
        "into a single coherent response."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: Old middleware for request size, rate limiting, and API key are removed.
# New implementation uses dependency injection (`api_key_guard`) and Pydantic settings.

# Include routers
app.include_router(api_router, prefix="/api")
# app.include_router(ai_router, prefix="/api")

# Mount WebSocket router at root so paths like /ws/sync, /ws/cognitive,
# /ws/metrics, /ws/events resolve. Without this they 404'd silently.
app.include_router(ws_router)

@app.post("/api/testpost")
async def test_post():
    return {"message": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9000,
        timeout_keep_alive=75,
        log_level="info"
    )

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9000,
        timeout_keep_alive=75,
        log_level="info"
    )
