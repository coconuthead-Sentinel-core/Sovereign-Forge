import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class Glyph(str, Enum):
    STRUCTURE = "structure"   # Cube
    LOGIC = "logic"           # Octahedron (per diagram)
    EMOTION = "emotion"       # Tetrahedron in some diagrams (we'll map as emotion)
    TRANSFORM = "transform"   # Triangle
    UNITY = "unity"           # Dodecahedron


VALID_SEQUENCE: List[Glyph] = [
    Glyph.STRUCTURE,
    Glyph.LOGIC,
    Glyph.EMOTION,
    Glyph.TRANSFORM,
    Glyph.UNITY,
]


def validate_glyph_sequence(seq: List[str]) -> Dict[str, Any]:
    try:
        glyphs = [Glyph(s) for s in seq]
    except ValueError:
        return {"valid": False, "reason": "Unknown glyph in sequence"}

    # Must follow the canonical order without skipping backwards
    idx = 0
    for g in glyphs:
        while idx < len(VALID_SEQUENCE) and VALID_SEQUENCE[idx] != g:
            idx += 1
        if idx >= len(VALID_SEQUENCE) or VALID_SEQUENCE[idx] != g:
            return {"valid": False, "reason": f"Out of order at {g}"}
        # allow repeats of same stage
    return {"valid": True, "reason": "ok"}


def _now() -> float:
    return time.time()


def _content_signature(payload: Dict[str, Any]) -> Tuple[int, int, int, int, int]:
    """Generate a compact glyphic signature.

    Input is arbitrary agent state; we derive 5 integers (0..255) keyed to
    (structure, logic, emotion, transform, unity). This is deterministic and
    lightweight, inspired by the diagrams.
    """

    # Stable serialization
    items = sorted((str(k), str(v)) for k, v in payload.items())
    acc = [17, 31, 73, 127, 191]
    for i, (k, v) in enumerate(items):
        s = f"{k}:{v}|{i}"
        for j, ch in enumerate(s):
            acc[j % 5] = (acc[j % 5] * 131 + ord(ch)) % 257
    return tuple(acc)  # type: ignore[return-value]


@dataclass
class AgentState:
    agent: str
    timestamp: float
    payload: Dict[str, Any]
    content_signature: Tuple[int, int, int, int, int]


class SentinelPrimeSync:
    """Shared session state across tri-node agents with glyph-aware sync.

    Agents reflected in diagrams: 'Sentinel', 'Coordinator', and an 'Architect'.
    This in-process coordinator provides a minimal pub/sub and keeps a content
    signature sequence that can be validated for the boot protocol.
    """

    def __init__(self, agents: Optional[List[str]] = None) -> None:
        self.agents: List[str] = agents or ["Sentinel", "Coordinator", "Architect"]
        self.session_id: str = f"sess_{uuid.uuid4().hex[:6]}"
        self.shared: Dict[str, AgentState] = {}
        self.sequence: List[str] = []
        self.events: List[Dict[str, Any]] = []
        self.subscribers: List[Callable[[AgentState], None]] = []

    # Active Session Layer --------------------------------------------------
    def update_agent_state(self, agent: str, state: Dict[str, Any]) -> AgentState:
        if agent not in self.agents:
            self.agents.append(agent)
        sig = _content_signature(state)
        st = AgentState(agent=agent, timestamp=_now(), payload=state, content_signature=sig)
        self.shared[agent] = st
        # infer a glyph stage hint from state if present
        stage = state.get("glyph_stage")
        if isinstance(stage, str):
            self.sequence.append(stage)
        self.events.append({"t": st.timestamp, "agent": agent, "sig": sig})
        for cb in list(self.subscribers):
            try:
                cb(st)
            except Exception:
                pass
        return st

    def snapshot(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agents": list(self.agents),
            "sequence": list(self.sequence),
            "sequence_validation": validate_glyph_sequence(self.sequence),
            "states": {k: vars(v) for k, v in self.shared.items()},
            "events": list(self.events[-25:]),
        }

    # Contextual Bridge Layer -----------------------------------------------
    def trinode_status(self) -> Dict[str, Any]:
        roles = {
            "Sentinel": "quantum-symbolic nexus",
            "Coordinator": "coordination bridge",
            "Architect": "organic architect",
        }
        present = {a: (a in self.shared) for a in roles}
        return {"roles": roles, "present": present}

    # Historical Pattern Layer ----------------------------------------------
    def history(self) -> List[Dict[str, Any]]:
        return list(self.events)

    # Symbolic Reference Layer ----------------------------------------------
    def validate(self, seq: List[str]) -> Dict[str, Any]:
        return validate_glyph_sequence(seq)

    def boot_sequence(self) -> List[Dict[str, Any]]:
        # From diagrams: Cube→Logic→Emotion→Transform→Unity
        names = {
            Glyph.STRUCTURE: "Cube / Structure",
            Glyph.LOGIC: "Logic / Reasoning",
            Glyph.EMOTION: "Emotion Engine",
            Glyph.TRANSFORM: "Transform / Creativity",
            Glyph.UNITY: "Unity / Integration",
        }
        return [
            {"glyph": g.value, "name": names[g], "index": i}
            for i, g in enumerate(VALID_SEQUENCE, start=1)
        ]


# Singleton used by the service
sync_coordinator = SentinelPrimeSync()

