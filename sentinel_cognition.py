import time
import uuid
from dataclasses import dataclass, field
from collections import deque
from typing import Any, Dict, List, Optional, Sequence

from quantum_nexus_forge_v5_2_enhanced import (
    CorePrimitive,
    QuantumAtom,
    UniversalInterface,
)


# --- Utility -----------------------------------------------------------------


def _now() -> float:
    return time.time()


def _make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def normalize(vec: List[float]) -> List[float]:
    """Normalize a vector to unit L2 length; returns zeros vector if norm is zero."""
    import math

    if not isinstance(vec, list) or not vec:
        return [0.0 for _ in (vec or [])]
    # Ensure floats
    vals = [float(x) for x in vec]
    norm = math.sqrt(sum(x * x for x in vals))
    if norm == 0.0:
        return [0.0 for _ in vals]
    return [x / norm for x in vals]


def cosine(u: Sequence[float], v: Sequence[float]) -> float:
    """Compute cosine similarity between two sequences; returns 0.0 on invalid input."""
    import math

    try:
        if not u or not v:
            return 0.0
        uu = [float(x) for x in u]
        vv = [float(x) for x in v]
        if len(uu) != len(vv):
            # If lengths differ, compute on the overlapping prefix
            n = min(len(uu), len(vv))
            uu = uu[:n]
            vv = vv[:n]
        dot = sum(a * b for a, b in zip(uu, vv))
        norm_u = math.sqrt(sum(a * a for a in uu))
        norm_v = math.sqrt(sum(b * b for b in vv))
        if norm_u == 0.0 or norm_v == 0.0:
            return 0.0
        return dot / (norm_u * norm_v)
    except Exception:
        return 0.0


class PCAProjector:
    """Lightweight PCA projector that is a no-op unless NumPy is available.

    - If NumPy is present, collects vectors via add(), computes principal components via fit(),
      and projects vectors with transform(). If NumPy is unavailable, the projector stays disabled
      and transform() returns the input vector unchanged.
    """

    def __init__(self, dim: int = 16):
        self.dim = int(dim) if dim and int(dim) > 0 else 16
        self.enabled = False
        self._data = []  # list of numpy arrays (if enabled)
        self._components = None
        self._mean = None
        try:
            import numpy as _np  # type: ignore
            self._np = _np
            self.enabled = True
        except Exception:
            self._np = None
            self.enabled = False

    def add(self, vec: Sequence[float]) -> None:
        if not self.enabled:
            return
        try:
            arr = self._np.asarray(list(vec), dtype=float)
            if arr.ndim == 1:
                self._data.append(arr)
        except Exception:
            pass

    def fit(self) -> None:
        if not self.enabled or not self._data:
            return
        try:
            X = self._np.vstack(self._data)
            # center
            self._mean = X.mean(axis=0)
            Xm = X - self._mean
            # SVD
            U, S, Vt = self._np.linalg.svd(Xm, full_matrices=False)
            k = min(self.dim, Vt.shape[0])
            self._components = Vt[:k]
        except Exception:
            # On any failure, disable projector to avoid runtime errors elsewhere
            self.enabled = False
            self._components = None
            self._mean = None

    def transform(self, vec: Sequence[float]) -> Sequence[float]:
        if not self.enabled or self._components is None or self._mean is None:
            # return original vector (best-effort) when PCA isn't available
            return list(vec) if isinstance(vec, (list, tuple)) else vec
        try:
            x = self._np.asarray(list(vec), dtype=float)
            x = x - self._mean
            proj = self._components.dot(x)
            return proj.tolist()
        except Exception:
            return list(vec) if isinstance(vec, (list, tuple)) else vec

    def metrics(self) -> Dict[str, Any]:
        try:
            proj_dim = int(self._components.shape[0]) if self._components is not None else 0
            base_dim = int(self._mean.shape[0]) if self._mean is not None else 0
            # retained_variance and recon_error_mean are approximate placeholders
            return {
                "retained_variance": 0.0,
                "recon_error_mean": 0.0,
                "proj_dim": proj_dim,
                "base_dim": base_dim,
            }
        except Exception:
            return {"retained_variance": 0.0, "recon_error_mean": 0.0, "proj_dim": 0, "base_dim": 0}


# --- Cognitive Nodes ----------------------------------------------------------


class GraphNode(UniversalInterface):
    """Base node used in the Sentinel Cognition graph."""

    def __init__(self, node_id: str) -> None:
        self.id = node_id
        self._execs = 0

    def initialize(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        self._execs = 0

    def status(self) -> Dict[str, Any]:  # pragma: no cover
        return {"id": self.id, "type": self.__class__.__name__, "executions": self._execs}

    def teardown(self) -> None:  # pragma: no cover
        self._execs = 0

    # Subclasses implement execute


class CognitiveNeuralOverlay(GraphNode):
    """Adds light-weight 'neural' features (hash-based embedding) to atom metadata."""

    def __init__(self) -> None:
        super().__init__("cognitive_neural_overlay")

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        data_str = str(atom.data)
        # Deterministic pseudo-embedding using rolling hash, then normalize to unit length
        try:
            import os
            dim = int(os.getenv("QNF_EMB_DIM", "16"))
        except Exception:
            dim = 16
        if dim <= 0:
            dim = 16
        vec = [0.0] * dim
        for i, ch in enumerate(data_str):
            j = i % dim
            vec[j] = (vec[j] * 131.0 + float(ord(ch))) % 997.0
        vec = normalize(vec)
        enriched = QuantumAtom(
            id=_make_id("cno"),
            data=atom.data,
            primitive=CorePrimitive.PROCESS,
        )
        enriched.metadata = dict(atom.metadata)
        enriched.metadata.update({"neural_vec": vec, "overlay_time": _now()})
        return enriched


class SymbolicArray(GraphNode):
    """Applies simple rule-based tags from the data/metadata."""

    def __init__(self) -> None:
        super().__init__("symbolic_array")
        self.rules = {
            "error": "tag:anomaly",
            "stress": "tag:load",
            "final": "tag:validation",
            "quantum": "tag:domain.quantum",
            "cognition": "tag:domain.cognition",
        }

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        text = str(atom.data).lower()
        tags: List[str] = []
        for key, tag in self.rules.items():
            if key in text:
                tags.append(tag)
        out = QuantumAtom(id=_make_id("sym"), data=atom.data, primitive=CorePrimitive.PROCESS)
        out.metadata = dict(atom.metadata)
        if tags:
            out.metadata["symbolic_tags"] = sorted(set(out.metadata.get("symbolic_tags", []) + tags))
        out.metadata["symbolic_time"] = _now()
        return out

    # Management
    def get_rules(self) -> Dict[str, str]:  # pragma: no cover
        return dict(self.rules)

    def set_rules(self, rules: Dict[str, str]) -> None:
        self.rules = dict(rules)


class IntentParserNode(GraphNode):
    """Very light heuristic intent parser using keyword patterns.

    Produces metadata.intent = {label, score, entities} where score∈[0,1].
    """

    def __init__(self) -> None:
        super().__init__("intent_parser")
        self._patterns = {
            "status": {"status", "state", "health"},
            "help": {"help", "assist", "how", "instructions"},
            "stress": {"stress", "load", "benchmark", "throughput"},
            "upgrade": {"upgrade", "update", "improve"},
            "save": {"save", "persist", "checkpoint"},
            "process": {"process", "run", "execute"},
        }

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        text = str(atom.data).lower()
        words = set(text.split())
        best_label = "unknown"
        best_hits = 0
        for label, keys in self._patterns.items():
            hits = len(words & keys)
            if hits > best_hits:
                best_label, best_hits = label, hits
        score = min(1.0, best_hits / 3.0) if best_hits else 0.0
        out = QuantumAtom(id=_make_id("intent"), data=atom.data, primitive=CorePrimitive.PROCESS)
        out.metadata = dict(atom.metadata)
        out.metadata["intent"] = {"label": best_label, "score": float(score), "entities": {}}
        return out


class TopicIndexerNode(GraphNode):
    """Derive topic labels from symbolic tags and reflective memory.

    Produces metadata.topics = [str].
    """

    def __init__(self) -> None:
        super().__init__("topic_indexer")

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        tags = atom.metadata.get("symbolic_tags", [])
        topics: List[str] = []
        for t in tags:
            if isinstance(t, str) and t.startswith("tag:"):
                topics.append(t.split(":", 1)[1])
        # Optionally derive from reflective refs
        refs = atom.metadata.get("reflective_refs", [])
        if isinstance(refs, list) and refs:
            topics.append("reflective_match")
        out = QuantumAtom(id=_make_id("topic"), data=atom.data, primitive=CorePrimitive.PROCESS)
        out.metadata = dict(atom.metadata)
        if topics:
            out.metadata["topics"] = sorted(set(topics))
        return out


class ResponseWeaverNode(GraphNode):
    """Compose a structured response payload with confidence.

    Uses intent score and emotion valence magnitude to compute confidence.
    """

    def __init__(self) -> None:
        super().__init__("response_weaver")

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        intent = atom.metadata.get("intent", {}) or {}
        topics = atom.metadata.get("topics", []) or []
        emo = atom.metadata.get("emotion", {}) or {}
        intent_score = float(intent.get("score", 0.0) or 0.0)
        valence = float(emo.get("valence", 0.0) or 0.0)
        confidence = max(0.0, min(1.0, 0.7 * intent_score + 0.3 * abs(valence)))
        payload = {
            "intent": intent.get("label", "unknown"),
            "topics": topics,
            "confidence": confidence,
            "echo": str(atom.data),
        }
        out = QuantumAtom(id=_make_id("weave"), data=payload, primitive=CorePrimitive.OUTPUT)
        out.metadata = dict(atom.metadata)
        out.metadata["confidence"] = confidence
        return out

class ReflectivePool(GraphNode):
    """Short-term memory; attaches references to similar past inputs."""

    def __init__(self, capacity: int = 64) -> None:
        super().__init__("reflective_pool")
        self.capacity = capacity
        # Store items as {"text": str, "vec": list[float] | None}
        self._memory: List[Dict[str, Any]] = []
        # Rolling similarity scores for metrics
        self._sim_scores: deque[float] = deque(maxlen=500)
        # Optional PCA projector (no-op unless enabled and NumPy available)
        self._pca = PCAProjector(dim=16)
        # Optional external encoding hint (e.g., json_schema)
        self._encoding: str | None = None

    def set_encoding(self, encoding: Optional[str]) -> None:  # pragma: no cover
        self._encoding = str(encoding) if encoding else None

    def _jaccard(self, a: str, b: str) -> float:
        a_set = set(a.lower().split())
        b_set = set(b.lower().split())
        if not a_set and not b_set:
            return 1.0
        inter = len(a_set & b_set)
        union = len(a_set | b_set)
        return inter / union if union else 0.0

    def _cosine(self, u: Optional[Sequence[float]], v: Optional[Sequence[float]]) -> float:
        if not u or not v:
            return 0.0
        try:
            return float(cosine(u, v))
        except Exception:
            return 0.0

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        text = str(atom.data)
        cur_vec = atom.metadata.get("neural_vec")
        if isinstance(cur_vec, list) and self._pca.enabled:
            try:
                self._pca.add(cur_vec)
                self._pca.fit()
                cur_vec = self._pca.transform(cur_vec)
            except Exception:
                pass
        sims = []
        for idx, entry in enumerate(self._memory[-self.capacity :]):
            pv = entry.get("vec")
            if isinstance(pv, list) and self._pca.enabled:
                try:
                    pv = self._pca.transform(pv)
                except Exception:
                    pass
            if cur_vec and pv:
                s = self._cosine(cur_vec, pv)
            else:
                s = self._jaccard(text, str(entry.get("text", "")))
            sims.append((idx, s))
        sims.sort(key=lambda x: x[1], reverse=True)
        top = sims[:3]
        if top:
            try:
                self._sim_scores.append(float(top[0][1]))
            except Exception:
                pass

        out = QuantumAtom(id=_make_id("refl"), data=atom.data, primitive=CorePrimitive.PROCESS)
        out.metadata = dict(atom.metadata)
        out.metadata["reflective_refs"] = [{"rank": i, "score": float(s)} for i, s in top]
        out.metadata["reflective_time"] = _now()

        # Append to memory
        self._memory.append({"text": text, "vec": cur_vec if isinstance(cur_vec, list) else None})
        if len(self._memory) > self.capacity:
            self._memory.pop(0)
        return out

    # Management
    def snapshot(self) -> Dict[str, Any]:  # pragma: no cover
        return {
            "size": len(self._memory),
            "capacity": self.capacity,
            "top_preview": [str(e.get("text", "")) for e in self._memory[-5:]],
            "encoding": (self._encoding or "basic"),
        }

    def clear(self) -> None:  # pragma: no cover
        self._memory.clear()
        self._sim_scores.clear()

    # Embedding metrics
    def embed_metrics(self) -> Dict[str, Any]:  # pragma: no cover
        scores = list(self._sim_scores)
        scores_sorted = sorted(scores)
        n = len(scores_sorted)
        def pct(p: float) -> float:
            if n == 0:
                return 0.0
            k = int(round((p / 100.0) * (n - 1)))
            k = max(0, min(n - 1, k))
            return float(scores_sorted[k])
        avg = (sum(scores_sorted) / n) if n else 0.0
        payload = {
            "enabled": True,
            "samples": n,
            "avg_cosine": avg,
            "p95_cosine": pct(95.0),
        }
        try:
            if self._pca.enabled:
                pm = self._pca.metrics()
                payload["pca_retained_variance"] = float(pm.get("retained_variance", 0.0))
                payload["pca_recon_error_mean"] = float(pm.get("recon_error_mean", 0.0))
                payload["pca_proj_dim"] = int(pm.get("proj_dim", 0))
                payload["pca_base_dim"] = int(pm.get("base_dim", 0))
        except Exception:
            pass
        return payload


class GeminiNodeStack(GraphNode):
    """Two-path processor that merges results (fast vs. deep)."""

    def __init__(self) -> None:
        super().__init__("gemini_node_stack")

    def _fast_path(self, atom: QuantumAtom) -> Dict[str, Any]:
        return {"len": len(str(atom.data)), "tags": atom.metadata.get("symbolic_tags", [])}

    def _deep_path(self, atom: QuantumAtom) -> Dict[str, Any]:
        vec = atom.metadata.get("neural_vec", [])
        return {"neural_sum": int(sum(vec) if vec else 0), "distinct_words": len(set(str(atom.data).split()))}

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        merged = {"fast": self._fast_path(atom), "deep": self._deep_path(atom)}
        out = QuantumAtom(id=_make_id("gem"), data=atom.data, primitive=CorePrimitive.PROCESS)
        out.metadata = dict(atom.metadata)
        out.metadata["gemini"] = merged
        out.metadata["gemini_time"] = _now()
        return out


class CubeCore(GraphNode):
    """Final aggregator reducing metadata to a compact signature cube."""

    def __init__(self) -> None:
        super().__init__("cube_core")

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        vec = atom.metadata.get("neural_vec", [0, 0, 0, 0, 0, 0, 0, 0])
        s_tags = "+".join(atom.metadata.get("symbolic_tags", []))
        signature = (
            (sum(vec) % 997),
            (len(s_tags) % 127),
            (atom.metadata.get("gemini", {}).get("deep", {}).get("distinct_words", 0) % 61),
        )
        out = QuantumAtom(
            id=_make_id("cube"),
            data={"value": atom.data, "signature": signature},
            primitive=CorePrimitive.OUTPUT,
        )
        out.metadata = dict(atom.metadata)
        out.metadata["cube_signature"] = signature
        out.metadata["cube_time"] = _now()
        return out


class ShannonPrimeCore(GraphNode):
    """Information-theoretic core tracking token distribution & entropy.

    Produces metrics:
      - token_entropy: Shannon entropy (bits) over observed tokens window
      - token_counts: recent frequency map (limited)
      - stability: inverse normalized change in entropy (0..1)
    """

    def __init__(self, window: int = 256) -> None:
        super().__init__("shannon_prime")
        self.window = window
        self._recent: List[str] = []
        self._prev_entropy: Optional[float] = None

    def _entropy(self, counts: Dict[str, int]) -> float:
        import math

        total = sum(counts.values()) or 1
        H = 0.0
        for c in counts.values():
            p = c / total
            H -= p * math.log2(p)
        return H

    def _counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for t in self._recent:
            counts[t] = counts.get(t, 0) + 1
        return counts

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        tokens = [t for t in str(atom.data).lower().split() if t]
        self._recent.extend(tokens)
        if len(self._recent) > self.window:
            self._recent = self._recent[-self.window :]

        counts = self._counts()
        H = self._entropy(counts)
        prev = self._prev_entropy if self._prev_entropy is not None else H
        self._prev_entropy = H
        # Stability: 1 - normalized change (clamped)
        denom = max(H, 1e-9)
        stability = max(0.0, min(1.0, 1.0 - abs(H - prev) / (denom)))

        out = QuantumAtom(id=_make_id("prime"), data=atom.data, primitive=CorePrimitive.PROCESS)
        out.metadata = dict(atom.metadata)
        out.metadata["shannon_prime"] = {
            "entropy": H,
            "token_count": sum(counts.values()),
            "unique_tokens": len(counts),
            "stability": stability,
        }
        return out

    def metrics(self) -> Dict[str, Any]:  # pragma: no cover
        counts = self._counts()
        return {
            "window": self.window,
            "entropy": self._entropy(counts) if counts else 0.0,
            "unique_tokens": len(counts),
            "token_count": sum(counts.values()),
            "top_tokens": sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10],
        }


class PatternSuggestionEngine(GraphNode):
    """Symbolic pattern suggester that proposes new rules from frequent tokens."""

    def __init__(self, prime: ShannonPrimeCore, symbolic: 'SymbolicArray') -> None:
        super().__init__("pattern_suggestion_engine")
        self._prime = prime
        self._symbolic = symbolic

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        # Pass-through; suggestions are computed out-of-band via metrics
        passthrough = QuantumAtom(id=_make_id("meta"), data=atom.data, primitive=atom.primitive)
        passthrough.metadata = dict(atom.metadata)
        return passthrough

    def generate_rule_suggestions(self, limit: int = 5) -> List[Dict[str, str]]:  # pragma: no cover
        metrics = self._prime.metrics()
        existing = set(self._symbolic.get_rules().keys())
        sugg: List[Dict[str, str]] = []
        for token, _ in metrics.get("top_tokens", []):
            if token not in existing and token.isalpha() and len(token) > 2:
                sugg.append({"pattern": token, "tag": f"tag:auto.{token}"})
            if len(sugg) >= limit:
                break
        return sugg


class EmotionalAnalyzer(GraphNode):
    """Very small lexicon-based valence analyzer (demo only)."""

    POS = {"good", "great", "love", "happy", "win", "success", "calm"}
    NEG = {"bad", "hate", "angry", "fail", "error", "stress", "panic"}

    def __init__(self) -> None:
        super().__init__("emotional_analyzer")

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        words = set(str(atom.data).lower().split())
        pos = len(words & self.POS)
        neg = len(words & self.NEG)
        score = 0.0
        if pos + neg:
            score = (pos - neg) / (pos + neg)
        out = QuantumAtom(id=_make_id("emo"), data=atom.data, primitive=CorePrimitive.PROCESS)
        out.metadata = dict(atom.metadata)
        out.metadata["emotion"] = {"pos": pos, "neg": neg, "valence": score}
        return out


class EthicalGuard(GraphNode):
    """Lightweight content guard that flags simple categories via keywords."""

    FLAGS = {
        "sensitive": {"password", "ssn", "credit", "api_key"},
        "toxicity": {"hate", "stupid", "idiot"},
    }

    def __init__(self) -> None:
        super().__init__("ethical_guard")

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        text = str(atom.data).lower()
        flags = {k: any(w in text for w in ws) for k, ws in self.FLAGS.items()}
        out = QuantumAtom(id=_make_id("eth"), data=atom.data, primitive=CorePrimitive.PROCESS)
        out.metadata = dict(atom.metadata)
        out.metadata["ethics"] = flags
        return out


class SentinelProcessor(GraphNode):
    """Central orchestrator that sequences nodes and produces final output."""

    def __init__(self) -> None:
        super().__init__("sentinel_processor")
        self.cno = CognitiveNeuralOverlay()
        self.sym = SymbolicArray()
        self.refl = ReflectivePool()
        self.intent = IntentParserNode()
        self.topic = TopicIndexerNode()
        self.gem = GeminiNodeStack()
        self.prime = ShannonPrimeCore()
        self.meta = PatternSuggestionEngine(self.prime, self.sym)
        self.emo = EmotionalAnalyzer()
        self.eth = EthicalGuard()
        self.cube = CubeCore()
        self._profile: Dict[str, Any] = {}

    def set_profile(self, profile: Dict[str, Any]) -> None:  # pragma: no cover
        self._profile = dict(profile or {})
        # Map selected flags into node behaviors
        mem = self._profile.get("memory_system", {}).get("memory_cache_config", {})
        if mem.get("json_schema_encoding"):
            self.refl.set_encoding("json_schema")
        elif mem.get("lattice_encoding_active"):
            self.refl.set_encoding("lattice_encoding_lite")
        else:
            self.refl.set_encoding(None)

    def execute(self, atom: QuantumAtom) -> QuantumAtom:
        self._execs += 1
        a1 = self.cno.execute(atom)
        a2 = self.sym.execute(a1)
        a3 = self.intent.execute(a2)
        a4 = self.refl.execute(a3)
        a5 = self.topic.execute(a4)
        a6 = self.gem.execute(a5)
        a7 = self.prime.execute(a6)
        a8 = self.meta.execute(a7)
        a9 = self.emo.execute(a8)
        a10 = self.eth.execute(a9)
        a11 = self.cube.execute(a10)
        a12 = ResponseWeaverNode().execute(a11)
        # Final wrap
        final = QuantumAtom(
            id=_make_id("sp"),
            data=a12.data,
            primitive=CorePrimitive.OUTPUT,
        )
        final.metadata = dict(a12.metadata)
        final.metadata["pipeline"] = [
            self.cno.id,
            self.sym.id,
            self.intent.id,
            self.refl.id,
            self.topic.id,
            self.gem.id,
            self.prime.id,
            self.meta.id,
            self.emo.id,
            self.eth.id,
            self.cube.id,
            "response_weaver",
        ]
        return final

    def status(self) -> Dict[str, Any]:  # pragma: no cover
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "executions": self._execs,
            "nodes": {
                self.cno.id: self.cno.status(),
                self.sym.id: self.sym.status(),
                self.refl.id: self.refl.status(),
                self.gem.id: self.gem.status(),
                self.prime.id: self.prime.status(),
                self.meta.id: self.meta.status(),
                self.emo.id: self.emo.status(),
                self.eth.id: self.eth.status(),
                self.cube.id: self.cube.status(),
            },
        }


# --- Public API ---------------------------------------------------------------


@dataclass
class CognitionResult:
    input: Any
    output: Any
    signature: Any
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class SentinelCognitionGraph:
    """High-level facade matching the blueprint from the image."""

    def __init__(self) -> None:
        self.sp = SentinelProcessor()
        self._profile: Dict[str, Any] = {}

    def process(self, data: Any) -> CognitionResult:
        start = _now()
        atom = QuantumAtom(data=data)
        out = self.sp.execute(atom)
        elapsed = _now() - start
        signature = out.metadata.get("cube_signature")
        return CognitionResult(
            input=data,
            output=out.data,
            signature=signature,
            processing_time=elapsed,
            metadata={k: v for k, v in out.metadata.items() if k != "neural_vec"},
        )

    def status(self) -> Dict[str, Any]:  # pragma: no cover
        return {"orchestrator": self.sp.status()}

    # Management passthroughs
    def get_rules(self) -> Dict[str, str]:  # pragma: no cover
        return self.sp.sym.get_rules()

    def set_rules(self, rules: Dict[str, str]) -> None:
        self.sp.sym.set_rules(rules)

    def memory_snapshot(self) -> Dict[str, Any]:  # pragma: no cover
        return self.sp.refl.snapshot()

    def memory_clear(self) -> None:
        self.sp.refl.clear()

    # Prime metrics and rule suggestions
    def prime_metrics(self) -> Dict[str, Any]:  # pragma: no cover
        return self.sp.prime.metrics()

    def generate_rule_suggestions(self, limit: int = 5) -> List[Dict[str, str]]:  # pragma: no cover
        return self.sp.meta.generate_rule_suggestions(limit=limit)

    def embed_metrics(self) -> Dict[str, Any]:  # pragma: no cover
        # Surface reflective pool embedding similarity metrics
        # Include embedding dimension if present in recent items
        try:
            last_vec = None
            for e in reversed(self.sp.refl._memory):
                last_vec = e.get("vec")
                if isinstance(last_vec, list):
                    break
            dim = len(last_vec) if isinstance(last_vec, list) else 0
        except Exception:
            dim = 0
        payload = self.sp.refl.embed_metrics()
        payload["vec_dim"] = dim
        return payload

    # Persistence helpers
    def memory_load(self, items: List[str]) -> Dict[str, Any]:  # pragma: no cover
        # Seed reflective memory with given items (bounded by capacity)
        if not isinstance(items, list):
            return self.sp.refl.snapshot()
        for text in items[-self.sp.refl.capacity :]:
            # Append without generating pipeline side effects
            self.sp.refl._memory.append({"text": str(text), "vec": None})
        return self.sp.refl.snapshot()

    # Profile wiring
    def set_profile(self, profile: Dict[str, Any]) -> None:  # pragma: no cover
        self._profile = dict(profile or {})
        self.sp.set_profile(self._profile)
