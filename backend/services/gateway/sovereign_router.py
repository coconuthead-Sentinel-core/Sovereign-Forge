"""
Sovereign Router — Orchestrates parallel calls to QNF and Sentinel.

This is the core of Sovereign Forge. A single inbound request is fanned
out to both downstream platforms concurrently using asyncio.gather(), the
results are merged by ResponseMerger, and a unified payload is returned.

Architecture:
    Caller → SovereignRouter.process()
                  │
          asyncio.gather()
         ┌────────┴────────┐
         ▼                 ▼
    QNF Chat API    Sentinel Chat API
         │                 │
         └────────┬────────┘
                  ▼
           ResponseMerger.merge()
                  │
                  ▼
          Unified Response
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from backend.services.gateway.platform_bridge import (
    get_qnf_client,
    get_sentinel_client,
)
from backend.services.gateway.response_merger import merge

logger = logging.getLogger(__name__)


class SovereignRouter:
    """
    Orchestrates parallel processing across Quantum Nexus Forge and Sentinel.

    All public methods are async and safe to call from FastAPI route handlers.
    """

    # --- Chat (primary use case) -------------------------------------------

    async def process(
        self,
        message: str,
        lens: Optional[str] = None,
        context: str = "",
    ) -> Dict[str, Any]:
        """
        Send a message to both platforms in parallel and return a merged response.

        Args:
            message: User message text.
            lens:    Cognitive lens identifier ("adhd", "autism", "dyslexia",
                     "dyscalculia", or None for neurotypical).
            context: Optional system context string.

        Returns:
            Merged response dict from ResponseMerger.merge().
        """
        logger.info("SovereignRouter.process — lens=%s | message length=%d", lens, len(message))

        async with get_qnf_client() as qnf, get_sentinel_client() as sentinel:
            qnf_task = qnf.chat(message=message, lens=lens, context=context)
            sentinel_task = sentinel.chat(message=message, lens=lens, context=context)

            qnf_response, sentinel_response = await asyncio.gather(
                qnf_task,
                sentinel_task,
                return_exceptions=False,
            )

        merged = merge(qnf_response, sentinel_response)
        logger.info(
            "SovereignRouter.process complete — degraded_mode=%s",
            merged.get("degraded_mode"),
        )
        return merged

    # --- Health check -------------------------------------------------------

    async def health(self) -> Dict[str, Any]:
        """
        Query the health of both downstream platforms in parallel.

        Returns:
            Dict with health status for each platform plus Sovereign's own status.
        """
        async with get_qnf_client() as qnf, get_sentinel_client() as sentinel:
            qnf_health, sentinel_health = await asyncio.gather(
                qnf.health(),
                sentinel.health(),
            )

        return {
            "sovereign": "online",
            "platforms": {
                "QuantumNexusForge": qnf_health,
                "SentinelForge": sentinel_health,
            },
        }

    # --- Metrics snapshot ---------------------------------------------------

    async def metrics(self) -> Dict[str, Any]:
        """
        Fetch metrics from both platforms in parallel and return combined snapshot.

        Returns:
            Dict with metrics from each platform under platform-specific keys.
        """
        async with get_qnf_client() as qnf, get_sentinel_client() as sentinel:
            qnf_metrics, sentinel_metrics = await asyncio.gather(
                qnf.metrics(),
                sentinel.metrics(),
            )

        return {
            "QuantumNexusForge": qnf_metrics,
            "SentinelForge": sentinel_metrics,
        }


# --- Singleton instance ------------------------------------------------------

_router_instance: Optional[SovereignRouter] = None


def get_sovereign_router() -> SovereignRouter:
    """Return the shared SovereignRouter singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = SovereignRouter()
        logger.info("SovereignRouter singleton initialized.")
    return _router_instance
