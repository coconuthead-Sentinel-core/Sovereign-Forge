"""
Platform Bridge — Async HTTP clients for QNF and Sentinel.

Sovereign Forge communicates with both downstream platforms via
non-blocking HTTP requests. Each platform client degrades gracefully
if the target platform is offline — the gateway never hard-fails due
to a single platform being unavailable.

Platform ports (configurable via environment):
    QNF      — http://localhost:5000  (Flask)
    Sentinel — http://localhost:8000  (FastAPI)
    Sovereign — http://localhost:9000  (this service)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# --- Platform base URLs (override via .env) ----------------------------------

QNF_BASE_URL: str = os.getenv("QNF_BASE_URL", "http://localhost:5000")
SENTINEL_BASE_URL: str = os.getenv("SENTINEL_BASE_URL", "http://localhost:8000")

# Shared timeout for all platform calls
PLATFORM_TIMEOUT: float = float(os.getenv("PLATFORM_TIMEOUT_SECONDS", "10.0"))


# --- Platform client ---------------------------------------------------------

class PlatformClient:
    """
    Async HTTP client for a single downstream platform.

    Usage:
        async with PlatformClient(base_url="http://localhost:5000") as client:
            result = await client.chat("Hello")
    """

    def __init__(self, base_url: str, platform_name: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._name = platform_name
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "PlatformClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=PLATFORM_TIMEOUT,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # --- Health check --------------------------------------------------------

    async def health(self) -> Dict[str, Any]:
        """Return platform health status, or an error dict on failure."""
        try:
            resp = await self._client.get("/api/status")
            resp.raise_for_status()
            return {"platform": self._name, "status": "online", "detail": resp.json()}
        except Exception as exc:
            logger.warning("%s health check failed: %s", self._name, exc)
            return {"platform": self._name, "status": "offline", "error": str(exc)}

    # --- Chat / process ------------------------------------------------------

    async def chat(
        self,
        message: str,
        lens: Optional[str] = None,
        context: str = "",
    ) -> Dict[str, Any]:
        """
        Send a chat message to the platform and return its response.

        Args:
            message: User message text.
            lens:    Cognitive lens identifier (e.g. "adhd", "autism").
            context: Optional system context string.

        Returns:
            Platform response dict, or an error dict on failure.
        """
        payload: Dict[str, Any] = {"message": message, "context": context}
        if lens:
            payload["lens"] = lens

        try:
            resp = await self._client.post("/api/ai/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            data["_source_platform"] = self._name
            return data
        except Exception as exc:
            logger.warning("%s chat call failed: %s", self._name, exc)
            return {
                "_source_platform": self._name,
                "error": str(exc),
                "status": "platform_unavailable",
            }

    # --- Metrics snapshot ----------------------------------------------------

    async def metrics(self) -> Dict[str, Any]:
        """Fetch the platform's current metrics snapshot."""
        try:
            resp = await self._client.get("/api/metrics")
            resp.raise_for_status()
            data = resp.json()
            data["_source_platform"] = self._name
            return data
        except Exception as exc:
            logger.warning("%s metrics call failed: %s", self._name, exc)
            return {
                "_source_platform": self._name,
                "error": str(exc),
                "status": "platform_unavailable",
            }


# --- Convenience factories ---------------------------------------------------

def get_qnf_client() -> PlatformClient:
    """Return a PlatformClient configured for Quantum Nexus Forge."""
    return PlatformClient(base_url=QNF_BASE_URL, platform_name="QuantumNexusForge")


def get_sentinel_client() -> PlatformClient:
    """Return a PlatformClient configured for Sentinel."""
    return PlatformClient(base_url=SENTINEL_BASE_URL, platform_name="SentinelForge")
