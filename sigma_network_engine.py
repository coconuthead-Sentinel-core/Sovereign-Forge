"""
Sigma Network Engine: feature-flagged cognitive engine driven by Sentinel profile.

This module demonstrates how to map the default profile into runtime flags
for conditional behavior. It also provides a MemoryCacheManager
that persists writes via a JSONStore for traceability.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.service import service  # use singleton to access profile
from backend.storage import JSONStore


class MemoryCacheManager:
    """Minimal write-through cache using JSONStore.

    Writes are appended to data/memory_cache.json with a simple schema:
      { "encoding": str, "items": [ {"payload": any} ... ] }
    """

    _store = JSONStore(path="data/memory_cache.json")

    @classmethod
    def write_memory(cls, obj: Any, *, encoding: str = "basic") -> None:
        payload = cls._store.load() or {}
        payload.setdefault("encoding", encoding)
        arr = payload.setdefault("items", [])
        arr.append({"payload": obj})
        cls._store.save(payload)


class SigmaNetworkEngine:
    """Core decision engine controlled by Sentinel profile flags."""

    def __init__(self) -> None:
        # Retrieve persisted Sentinel profile from the service
        self.profile: Dict[str, Any] = service.profile_get()
        self.log = logging.getLogger("SigmaEngine")
        self._set_feature_flags()

    def _set_feature_flags(self) -> None:
        p = self.profile or {}
        # COGNITIVE CORE FLAGS
        self.GNN_ACTIVE = (
            p.get("cognitive_core", {})
            .get("gnn_extensions", {})
            .get("GNN_connectivity_rules", False)
        )
        self.MULTI_LANG_ACTIVE = (
            p.get("cognitive_core", {})
            .get("gnn_extensions", {})
            .get("multi_language_abstraction", False)
        )
        # MEMORY SYSTEM FLAGS (MemoryCache)
        mem = p.get("memory_system", {}).get("memory_cache_config", {})
        self.JSON_SCHEMA_ENCODING = bool(mem.get("json_schema_encoding", False))
        self.LATTICE_ENCODING_ACTIVE = bool(mem.get("lattice_encoding_active", False))
        self.log.info(
            "Engine Initialized. GNN_ACTIVE=%s, JSON_SCHEMA=%s",
            self.GNN_ACTIVE,
            self.JSON_SCHEMA_ENCODING,
        )

    def process_input(self, data: Any) -> Any:
        # Cognitive Core Logic
        if self.GNN_ACTIVE:
            self.log.debug("GNN Connectivity Rules ENGAGED.")
            output = self._run_gnn_logic(data)
        else:
            self.log.debug("Standard Logic Lattice ENGAGED.")
            output = self._run_standard_logic(data)

        # Memory System Logic
        if self.JSON_SCHEMA_ENCODING:
            self.log.debug("Writing memory via JSON Schema.")
            MemoryCacheManager.write_memory(output, encoding="json_schema")
        elif self.LATTICE_ENCODING_ACTIVE:
            self.log.debug("Writing memory via lattice encoding.")
            MemoryCacheManager.write_memory(output, encoding="lattice_encoding_lite")
        else:
            MemoryCacheManager.write_memory(output, encoding="basic_txt")

        return output

    # --- Placeholder Methods ---
    def _run_gnn_logic(self, data: Any) -> Any:
        return {"mode": "gnn", "value": data}

    def _run_standard_logic(self, data: Any) -> Any:
        return {"mode": "standard", "value": data}
