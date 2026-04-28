"""
Response Merger — Combines outputs from QNF and Sentinel into one unified response.

Sovereign Forge calls both platforms in parallel. This module takes the two
independent response dicts and produces a single merged payload that surfaces
the best of both processing styles.

Merge strategy:
    - Text responses are concatenated with clear platform attribution.
    - Numeric scores (confidence, entropy, coherence) are averaged.
    - Metadata from both platforms is preserved under platform-specific keys.
    - If one platform is offline, the available response is returned with a
      degraded-mode flag rather than failing the entire request.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Sentinel for unavailable platform response
_OFFLINE_MARKER = "platform_unavailable"


def _is_offline(response: Dict[str, Any]) -> bool:
    """Return True if the platform response indicates an error or offline state."""
    return response.get("status") == _OFFLINE_MARKER or "error" in response


def _extract_text(response: Dict[str, Any], platform_name: str) -> str:
    """
    Extract the primary text content from a platform response.

    Tries common response key patterns used by QNF and Sentinel.
    """
    # Sentinel / sovereign format: choices[0].message.content
    choices = response.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")

    # QNF format: response or result top-level key
    for key in ("response", "result", "output", "text", "message"):
        if key in response:
            val = response[key]
            if isinstance(val, str):
                return val

    # Fallback
    return f"[{platform_name}: no extractable text]"


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def merge(
    qnf_response: Dict[str, Any],
    sentinel_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge QNF and Sentinel platform responses into a single unified payload.

    Args:
        qnf_response:      Response dict from Quantum Nexus Forge.
        sentinel_response: Response dict from Sentinel Forge.

    Returns:
        Unified response dict with the following top-level keys:
            unified_response    — merged text output
            platform_status     — online/offline state for each platform
            qnf                 — raw QNF response (preserved for transparency)
            sentinel            — raw Sentinel response (preserved)
            merged_metrics      — averaged numeric scores
            degraded_mode       — True if one platform was unavailable
    """
    qnf_offline = _is_offline(qnf_response)
    sentinel_offline = _is_offline(sentinel_response)

    degraded = qnf_offline or sentinel_offline

    if degraded:
        logger.warning(
            "Sovereign merge in degraded mode — QNF offline: %s | Sentinel offline: %s",
            qnf_offline,
            sentinel_offline,
        )

    # --- Extract text from each platform ------------------------------------

    qnf_text = (
        "[QuantumNexusForge offline]"
        if qnf_offline
        else _extract_text(qnf_response, "QuantumNexusForge")
    )

    sentinel_text = (
        "[SentinelForge offline]"
        if sentinel_offline
        else _extract_text(sentinel_response, "SentinelForge")
    )

    # --- Build unified text response ----------------------------------------

    if qnf_offline and not sentinel_offline:
        unified_text = f"[SentinelForge] {sentinel_text}"
    elif sentinel_offline and not qnf_offline:
        unified_text = f"[QuantumNexusForge] {qnf_text}"
    else:
        unified_text = (
            f"[QuantumNexusForge]\n{qnf_text}\n\n"
            f"[SentinelForge]\n{sentinel_text}"
        )

    # --- Merge numeric metrics ----------------------------------------------

    qnf_meta = qnf_response.get("_cognitive_metadata", {})
    sentinel_meta = sentinel_response.get("_cognitive_metadata", {})

    def avg_metric(key: str) -> Optional[float]:
        vals = []
        for meta in (qnf_meta, sentinel_meta):
            if key in meta:
                vals.append(_safe_float(meta[key]))
        if not vals:
            return None
        return round(sum(vals) / len(vals), 3)

    merged_metrics: Dict[str, Any] = {}
    for metric_key in ("input_entropy", "output_entropy", "symbolic_confidence"):
        val = avg_metric(metric_key)
        if val is not None:
            merged_metrics[metric_key] = val

    # Aggregate symbolic tags from both platforms
    qnf_tags = set(qnf_meta.get("symbolic_tags", []))
    sentinel_tags = set(sentinel_meta.get("symbolic_tags", []))
    merged_metrics["combined_symbolic_tags"] = list(qnf_tags | sentinel_tags)

    # --- Platform status summary -------------------------------------------

    platform_status = {
        "QuantumNexusForge": "offline" if qnf_offline else "online",
        "SentinelForge": "offline" if sentinel_offline else "online",
    }

    # --- Assemble final payload --------------------------------------------

    return {
        "unified_response": unified_text,
        "platform_status": platform_status,
        "merged_metrics": merged_metrics,
        "degraded_mode": degraded,
        "qnf": qnf_response,
        "sentinel": sentinel_response,
    }
