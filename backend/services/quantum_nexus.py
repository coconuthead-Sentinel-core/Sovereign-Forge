from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass(frozen=True)
class GreatGreg:
    cell: str
    r: int
    c: int
    node: int
    label: str


class QuantumNexus:
    """
    Loads the Quantum Nexus YAML blueprint and provides:
      - dependency lookup (dep_AllFiles_L2R_to_Z1, dep_A1_to_V1)
      - Great Greg coordinate resolver (A1, Node_3:P1, Node_3.R3C4)
    """

    def __init__(self, blueprint: Dict[str, Any]):
        self.bp = blueprint
        self._rc_map = (blueprint.get("great_greg_coordinates", {}) or {}).get("rc_map", {}) or {}
        self._deps = {d["id"]: d for d in (blueprint.get("dependencies") or []) if isinstance(d, dict) and "id" in d}

    @classmethod
    def from_yaml(cls, path: str | Path) -> "QuantumNexus":
        p = Path(path)
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        # Accept either top-level blueprint or nested under "quantum_nexus_blueprint"
        if "quantum_nexus_blueprint" in data:
            data = data["quantum_nexus_blueprint"]
        return cls(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuantumNexus":
        """Construct from an in-memory blueprint dict.

        Accepts either a top-level blueprint or one nested under
        ``quantum_nexus_blueprint`` (matching ``from_yaml`` semantics).
        """
        if "quantum_nexus_blueprint" in data:
            data = data["quantum_nexus_blueprint"]
        return cls(data)

    def dependency(self, dep_id: str) -> Dict[str, Any]:
        if dep_id not in self._deps:
            raise KeyError(f"Dependency not found: {dep_id}")
        return self._deps[dep_id]

    def resolve_cell(self, cell: str) -> GreatGreg:
        # Case-insensitive lookup: try exact, then upper-case, then any case match
        original = cell.strip()
        info = self._rc_map.get(original)
        canonical = original
        if not info:
            up = original.upper()
            info = self._rc_map.get(up)
            if info:
                canonical = up
            else:
                # last attempt: case-insensitive scan
                for k, v in self._rc_map.items():
                    if k.lower() == original.lower():
                        info = v
                        canonical = k
                        break
        if not info:
            raise KeyError(f"Unknown cell: {original}")
        return GreatGreg(
            cell=canonical, r=int(info["r"]), c=int(info["c"]),
            node=int(info["node"]), label=str(info["label"]),
        )

    # ── Origin / Terminus shortcuts ───────────────────────────────────
    @property
    def origin(self) -> GreatGreg:
        """A1 — Prime Truth (lowest r,c — the architecture's origin)."""
        return self._extreme(reverse=False)

    @property
    def terminus(self) -> GreatGreg:
        """Last cell — Dynamic Expansion frontier."""
        return self._extreme(reverse=True)

    def _extreme(self, *, reverse: bool) -> GreatGreg:
        if not self._rc_map:
            raise KeyError("rc_map is empty")
        # Sort by (r, c) ascending for origin, descending for terminus
        items = sorted(
            self._rc_map.items(),
            key=lambda kv: (int(kv[1]["r"]), int(kv[1]["c"])),
            reverse=reverse,
        )
        cell, info = items[0]
        return GreatGreg(
            cell=cell, r=int(info["r"]), c=int(info["c"]),
            node=int(info["node"]), label=str(info["label"]),
        )

    # ── Path tracing ─────────────────────────────────────────────────
    def diagonal_trace(self, dep_id: str = "dep_A1_to_V1"
                       ) -> List[GreatGreg]:
        """Resolve a diagonal_dependency's `path` (list of cells) into GreatGregs."""
        dep = self.dependency(dep_id)
        path = dep.get("path", [])
        return [self.resolve_cell(c) for c in path]

    def lateral_trace(self, dep_id: str = "dep_AllFiles_L2R_to_Z1"
                      ) -> List[GreatGreg]:
        """Resolve a lateral_row_major_dependency's `path` (list of rows of cells)."""
        dep = self.dependency(dep_id)
        path = dep.get("path", [])
        out: List[GreatGreg] = []
        for row in path:
            if isinstance(row, list):
                for cell in row:
                    out.append(self.resolve_cell(cell))
            else:
                out.append(self.resolve_cell(row))
        return out

    # ── Node lookup ──────────────────────────────────────────────────
    def node(self, node_id: str) -> Dict[str, Any]:
        for n in (self.bp.get("nodes") or []):
            if isinstance(n, dict) and n.get("id") == node_id:
                return n
        raise KeyError(f"Node not found: {node_id}")

    def get_node_cells(self, node_id: str) -> List[GreatGreg]:
        n = self.node(node_id)
        return [self.resolve_cell(c) for c in (n.get("cells") or [])]

    # ── API formatting ───────────────────────────────────────────────
    def to_api_response(self, cell: str) -> Dict[str, Any]:
        gg = self.resolve_cell(cell)
        return {
            "cell":    gg.cell,
            "row":     gg.r,
            "column":  gg.c,
            "node":    gg.node,
            "node_id": f"Node_{gg.node}",
            "label":   gg.label,
        }

    def resolve(self, ref: str) -> GreatGreg:
        """
        Accepts:
          - "P1"
          - "Node_3:P1"
          - "Node_3.R3C4"  (will map back to the matching cell if possible)
        """
        ref = ref.strip()

        # Node_3:P1 → P1
        if ":" in ref:
            _, cell = ref.split(":", 1)
            return self.resolve_cell(cell)

        # Node_3.R3C4 → find cell by r/c/node
        if ".R" in ref and "C" in ref:
            node_part, rc_part = ref.split(".", 1)
            node = int("".join(ch for ch in node_part if ch.isdigit()))
            rc_part = rc_part.upper().lstrip("R")
            r_str, c_str = rc_part.split("C", 1)
            r, c = int(r_str), int(c_str)

            # scan rc_map for matching triplet
            for cell, info in self._rc_map.items():
                if int(info["node"]) == node and int(info["r"]) == r and int(info["c"]) == c:
                    return GreatGreg(cell=cell, r=r, c=c, node=node, label=str(info["label"]))
            raise KeyError(f"No cell found for {ref} (node={node}, r={r}, c={c})")

        # default: treat as cell
        return self.resolve_cell(ref)