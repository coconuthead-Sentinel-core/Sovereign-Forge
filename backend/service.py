import threading
import os
import time
import uuid
from typing import Any, Dict, Optional
from collections import deque

from quantum_nexus_forge_v5_2_enhanced import QuantumNexusForge
from sentinel_cognition import SentinelCognitionGraph
from quantum_nexus_forge_v5_2_enhanced import QuantumAtom
from sentinel_profile import initialize_sentinel, default_profile
from sentinel_sync import sync_coordinator, _content_signature
from .eventbus import bus
from .storage import JSONStore
from .llm import get_llm, LLMError


class QNFService:
    """Middle layer wrapping QuantumNexusForge with thread-safety and jobs."""

    def __init__(self) -> None:
        self._qnf = QuantumNexusForge()
        self._lock = threading.RLock()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._jobs_lock = threading.Lock()
        # --- Event Stream (playtesting / instrumentation) -------------------
        self._event_queue: deque = deque(maxlen=1000)
        self._event_cv = threading.Condition()
        # --- Simple friendships / guilds (in‑memory skeleton) --------------
        self._friendships: Dict[str, set] = {}
        self._guilds: Dict[str, Dict[str, Any]] = {}
        # Cognitive graph based on the provided blueprint
        self._cog = SentinelCognitionGraph()
        # Persistence
        self._store = JSONStore()
        self._load_state_if_present()
        # --- Nexus Notes (centroid embeddings) -----------------------------
        self._notes: Dict[str, Dict[str, Any]] = {}
        # --- Threads / Routing ----------------------------------------------
        # Topic threads keyed by thread_id; simple mapping topic->thread_id
        self._threads: Dict[str, Dict[str, Any]] = {}
        self._topic_to_thread: Dict[str, str] = {}
        self._intent_counts: Dict[str, int] = {}
        self._topic_counts: Dict[str, int] = {}
        self._persist_counter: int = 0
        # Seeds and topic matrix (memory/reflex)
        self._seeds: set[str] = set()
        self._topic_matrix: Dict[str, Dict[str, int]] = {}
        # Last resonance snapshot
        self._last_coherence_score: Dict[str, Any] = {}
        # Topic alias mapping (seed/keyword -> canonical topic label)
        self._topic_alias: Dict[str, str] = {}
        # --- Triage tuner (SGD scaffold) -----------------------------------
        self._tuner = {
            "enabled": False,
            "lr": 0.1,
            "target_p95_ms": 50.0,
            "min_ms": 10.0,
            "max_ms": 5000.0,
        }
        # --- Sentinel Profile ----------------------------------------------
        self._profile: Dict[str, Any] = initialize_sentinel(default_profile())
        # Wire profile into cognition pipeline
        try:
            self._cog.set_profile(self._profile)
        except Exception:
            pass

    # Core operations
    def process(self, data: Any, pool_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            return self._qnf.process(data, pool_id)

    def status(self) -> Dict[str, Any]:
        # Status reads can be done without the global lock, but keep simple and safe
        with self._lock:
            return self._qnf.status()

    def metrics(self) -> Dict[str, Any]:
        """Return a compact metrics payload useful for ops/monitoring."""
        with self._lock:
            st = self._qnf.status()
        pools = st.get("pool_status", {})
        pool_metrics: Dict[str, Any] = {}
        # Optional conversion: estimated bytes per heap entry
        try:
            entry_bytes = int(os.getenv("QNF_HEAP_ENTRY_BYTES", "0"))
        except Exception:
            entry_bytes = 0
        global_total_bytes = 0.0
        for pid, pdata in pools.items():
            entries = pdata.get("heap_size")
            # derive MiB/GiB if possible
            heap_mib = 0.0
            heap_gib = 0.0
            try:
                if isinstance(entries, (int, float)) and entry_bytes > 0:
                    total_bytes = float(entries) * float(entry_bytes)
                    heap_mib = total_bytes / (1024.0 ** 2)
                    heap_gib = total_bytes / (1024.0 ** 3)
                    global_total_bytes += total_bytes
            except Exception:
                pass
            pool_metrics[pid] = {
                "processor_count": pdata.get("processor_count"),
                "total_executions": pdata.get("total_executions"),
                "heap_size": entries,
                "heap_mib": heap_mib,
                "heap_gib": heap_gib,
                "sched_heap_stale_ratio": pdata.get("sched_heap_stale_ratio"),
                "avg_latency_ms": pdata.get("avg_latency_ms"),
                "p95_latency_ms": pdata.get("p95_latency_ms"),
                "build": self._per_pool_build(pid),
            }
        global_heap_mib = global_total_bytes / (1024.0 ** 2) if global_total_bytes > 0 else 0.0
        global_heap_gib = global_total_bytes / (1024.0 ** 3) if global_total_bytes > 0 else 0.0
        # Cognition embedding metrics (lightweight; optional)
        try:
            cog_embed = self._cog.embed_metrics()
        except Exception:
            cog_embed = {"enabled": False}
        # Online triage tuner step (if enabled)
        try:
            if self._tuner.get("enabled") is True:
                p95 = float(st.get("p95_latency_ms", 0.0) or 0.0)
                target = float(self._tuner.get("target_p95_ms", 50.0))
                lr = float(self._tuner.get("lr", 0.1))
                old_thr = getattr(self._qnf, "_p95_scale_threshold_ms", target)
                # Heuristic gradient step: if p95>target, decrease threshold to scale earlier
                delta = p95 - target
                new_thr = float(old_thr) - lr * delta
                new_thr = max(float(self._tuner.get("min_ms", 10.0)), min(float(self._tuner.get("max_ms", 5000.0)), new_thr))
                try:
                    self._qnf.set_p95_scale_threshold_ms(new_thr)  # type: ignore[attr-defined]
                except Exception:
                    pass
                tuner_state = {
                    "enabled": True,
                    "p95_ms": p95,
                    "target_ms": target,
                    "threshold_ms": new_thr,
                    "lr": lr,
                }
            else:
                tuner_state = {"enabled": False}
        except Exception:
            tuner_state = {"enabled": False}
        return {
            "total_pools": st.get("total_pools"),
            "total_processors": st.get("total_processors"),
            "avg_latency_ms": st.get("avg_latency_ms"),
            "p95_latency_ms": st.get("p95_latency_ms"),
            "avg_heap_stale_ratio": st.get("avg_heap_stale_ratio"),
            "max_heap_stale_ratio": st.get("max_heap_stale_ratio"),
            "global_heap_mib": global_heap_mib,
            "global_heap_gib": global_heap_gib,
            "pools": pool_metrics,
            "cog_embedding": cog_embed,
            "triage_tuner": tuner_state,
        }

    # --- Build / Version ----------------------------------------------------
    def build_info(self) -> Dict[str, Any]:
        """Return basic build/version metadata for Prometheus info metrics
        and debugging. Values are read from env with sensible defaults.
        """
        import os

        def _get(name: str, default: str) -> str:
            return os.getenv(name, default)

        return {
            "app": _get("QNF_APP", "qnf"),
            "version": _get("QNF_VERSION", "dev"),
            "git_sha": _get("QNF_GIT_SHA", "unknown"),
            "build_time": _get("QNF_BUILD_TIME", "unknown"),
        }

    # --- Per‑pool build -----------------------------------------------------
    def _per_pool_build(self, pool_id: str) -> Dict[str, Any]:
        import os

        # Support two naming schemes for env vars:
        #  1) QNF_{POOLID}_<VAR>
        #  2) QNF_POOL_{POOLID}_<VAR>
        pid = pool_id.upper()
        prefixes = [f"QNF_{pid}_", f"QNF_POOL_{pid}_"]

        def _get(var: str, default: str) -> str:
            for p in prefixes:
                val = os.getenv(f"{p}{var}")
                if val is not None:
                    return val
            return default

        return {
            "version": _get("VERSION", "dev"),
            "git_sha": _get("GIT_SHA", "unknown"),
            "build_time": _get("BUILD_TIME", "unknown"),
        }

    # --- Event Stream API ---------------------------------------------------
    def add_event(self, payload: Dict[str, Any]) -> None:
        with self._event_cv:
            self._event_queue.append(payload)
            self._event_cv.notify_all()

    def event_stream(self):
        last_idx = 0
        while True:
            with self._event_cv:
                while last_idx >= len(self._event_queue):
                    self._event_cv.wait(timeout=5)
                    # keep idle loop but don't synthesize fake SSE events here
                    # the API layer will handle batching/keepalive for NDJSON
                    if last_idx >= len(self._event_queue):
                        yield None
                # emit new items
                items = list(self._event_queue)[last_idx:]
                last_idx = len(self._event_queue)
            for ev in items:
                yield ev

    # --- Friendships / Guilds (skeleton) -----------------------------------
    def add_friendship(self, player: str, friend: str) -> Dict[str, Any]:
        self._friendships.setdefault(player, set()).add(friend)
        self._friendships.setdefault(friend, set()).add(player)
        return {"player": player, "friend": friend}

    def list_friendships(self, player: str) -> Dict[str, Any]:
        return {"player": player, "friends": sorted(self._friendships.get(player, set()))}

    def create_guild(self, guild_id: str, name: str) -> Dict[str, Any]:
        if guild_id in self._guilds:
            return self._guilds[guild_id]
        self._guilds[guild_id] = {"id": guild_id, "name": name, "members": set()}
        return self._guilds[guild_id]

    def add_guild_member(self, guild_id: str, player: str) -> Dict[str, Any]:
        g = self._guilds.setdefault(guild_id, {"id": guild_id, "name": guild_id, "members": set()})
        g["members"].add(player)
        return {"guild": guild_id, "members": sorted(g["members"])}

    def get_guild(self, guild_id: str) -> Dict[str, Any]:
        g = self._guilds.get(guild_id)
        if not g:
            return {"id": guild_id, "name": guild_id, "members": []}
        return {"id": g["id"], "name": g["name"], "members": sorted(g["members"])}

    # --- Events history ------------------------------------------------------
    def recent_events(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Return up to `limit` most recent events (newest last)."""
        if limit <= 0:
            return []
        data = list(self._event_queue)
        if len(data) <= limit:
            return data
        return data[-limit:]

    def create_pool(self, pool_id: str, initial_size: int = 3) -> str:
        with self._lock:
            return self._qnf.create_pool(pool_id, initial_size)

    def teardown(self) -> None:
        with self._lock:
            self._qnf.teardown_complete()

    def rebuild(self, default_pools: int = 2, pool_size: int = 5) -> None:
        with self._lock:
            self._qnf.rebuild_from_foundation(
                {"default_pools": default_pools, "pool_size": pool_size}
            )

    # Cognitive Graph operations
    def cog_process(self, data: Any) -> Dict[str, Any]:
        result = self._cog.process(data)
        # Publish a lightweight cognition event for dashboards
        try:
            meta = result.metadata or {}
            intent = (meta.get("intent") or {}).get("label", "unknown")
            confidence = float(meta.get("confidence", 0.0) or 0.0)
            topics = meta.get("topics", []) or []
            # Seed/alias integration: boost small confidence and add alias topics for matched seeds
            try:
                words = set(str(data).lower().split())
                hits = words & self._seeds
                if hits:
                    # small additive boost up to +0.2
                    boost = min(0.2, 0.1 * len(hits))
                    confidence = min(1.0, confidence + boost)
                    meta.setdefault("intent", {}).update({"score": confidence})
                    meta["seeds"] = sorted(hits)
                    if "seeded" not in topics:
                        topics.append("seeded")
                    # add alias topics mapped to matched seeds
                    for s in hits:
                        alias = self._topic_alias.get(s)
                        if alias and alias not in topics:
                            topics.append(alias)
            except Exception:
                pass
            # normalize topics through alias map
            try:
                topics = [self._topic_alias.get(t, t) for t in topics]
            except Exception:
                pass
            bus.publish({
                "type": "cog.intent",
                "data": {"intent": intent, "confidence": confidence, "topics": topics},
            })
            # Update stats
            self._intent_counts[intent] = self._intent_counts.get(intent, 0) + 1
            for t in topics:
                self._topic_counts[t] = self._topic_counts.get(t, 0) + 1
            # Threading: append to a thread for the first topic (or 'general')
            top_topic = topics[0] if topics else "general"
            thread_id = self._topic_to_thread.get(top_topic)
            if not thread_id:
                thread_id = f"thr_{uuid.uuid4().hex[:8]}"
                self._topic_to_thread[top_topic] = thread_id
                self._threads[thread_id] = {"id": thread_id, "topic": top_topic, "items": [], "created": time.time(), "updated": time.time()}
            sig = _content_signature({"text": str(data), "intent": intent, "topics": topics})
            entry = {"ts": time.time(), "text": str(data), "intent": intent, "confidence": confidence, "content_signature": list(sig)}
            thr = self._threads.get(thread_id)
            if thr is not None:
                items = thr.get("items", [])
                items.append(entry)
                if len(items) > 200:
                    del items[: len(items) - 200]
                thr["items"] = items
                thr["updated"] = time.time()
            # Routing hint (no side effects; informational only)
            route = self._route_hint(intent=intent, topics=topics, confidence=confidence)
            result.metadata["route"] = route
            # Opportunistic persistence every 10 updates
            self._persist_counter = (self._persist_counter + 1) % 10
            if self._persist_counter == 0:
                self._persist_runtime_state()
            # Compute resonance snapshot
            try:
                sym_tags = meta.get("symbolic_tags", []) or []
                rule_comp = min(1.0, len(sym_tags) / 5.0)
                refs = meta.get("reflective_refs", []) or []
                sim_comp = float(refs[0].get("score", 0.0)) if refs and isinstance(refs[0], dict) else 0.0
                sp = meta.get("shannon_prime", {}) or {}
                stability = float(sp.get("stability", 0.0) or 0.0)
                emo = meta.get("emotion", {}) or {}
                valence = abs(float(emo.get("valence", 0.0) or 0.0))
                eth = meta.get("ethics", {}) or {}
                ethics_ok = 0 if any(bool(v) for v in eth.values()) else 1
                thread_activity = min(1.0, len(thr.get("items", [])) / 50.0) if thr else 0.0
                components = {
                    "rules": rule_comp,
                    "similarity": sim_comp,
                    "stability": stability,
                    "ethics_ok": float(ethics_ok),
                    "thread_activity": thread_activity,
                }
                score = sum(components.values()) / len(components)
                self._last_coherence_score = {"score": score, **components}
                result.metadata["coherence_score"] = dict(self._last_coherence_score)
            except Exception:
                pass
        except Exception:
            pass
        return {
            "input": result.input,
            "output": result.output,
            "signature": result.signature,
            "processing_time": result.processing_time,
            "metadata": result.metadata,
        }

    # --- Routing / Threads API ---------------------------------------------
    def _route_hint(self, *, intent: str, topics: list[str], confidence: float) -> Dict[str, Any]:
        intent = (intent or "").lower()
        if intent in ("help",):
            return {"action": "help", "target": "local"}
        if intent in ("status",):
            return {"action": "status", "target": "local"}
        if intent in ("stress", "benchmark"):
            return {"action": "stress_test", "target": "local"}
        if intent in ("upgrade", "update"):
            return {"action": "upgrade", "target": "llm"}
        return {"action": "process", "target": "local"}

    def cog_threads(self, topic: Optional[str] = None) -> Dict[str, Any]:
        out = []
        for tid, th in self._threads.items():
            if topic and th.get("topic") != topic:
                continue
            out.append({
                "id": tid,
                "topic": th.get("topic"),
                "count": len(th.get("items", [])),
                "created": th.get("created"),
                "updated": th.get("updated"),
            })
        out.sort(key=lambda x: x.get("updated", 0.0), reverse=True)
        return {"threads": out}

    def cog_stats(self) -> Dict[str, Any]:
        return {"intents": dict(self._intent_counts), "topics": dict(self._topic_counts)}

    def cog_thread(self, thread_id: str, limit: int = 50) -> Dict[str, Any]:
        thr = self._threads.get(thread_id)
        if not thr:
            return {"id": thread_id, "topic": None, "items": []}
        items = list(thr.get("items", []))
        if limit > 0 and len(items) > limit:
            items = items[-limit:]
        return {"id": thread_id, "topic": thr.get("topic"), "items": items}

    def seeds_get(self) -> Dict[str, Any]:
        return {"seeds": sorted(self._seeds)}

    def seeds_add(self, items: list[str]) -> Dict[str, Any]:
        if not isinstance(items, list):
            return self.seeds_get()
        for x in items:
            if isinstance(x, str) and x.strip():
                self._seeds.add(x.strip().lower())
        self._persist_runtime_state()
        return self.seeds_get()

    def cog_matrix(self, top_k: int = 20) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for topic, counts in self._topic_matrix.items():
            pairs = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
            out[topic] = pairs
        return {"matrix": out}

    def coherence_score_last(self) -> Dict[str, Any]:
        return dict(self._last_coherence_score)

    def symbols_pack(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        shapes = payload.get("shapes") if isinstance(payload, dict) else None
        if not isinstance(shapes, dict):
            shapes = payload if isinstance(payload, dict) else {}
        cur_rules = self._cog.get_rules()
        added = {"seeds": 0, "aliases": 0, "rules": 0}
        for name, cfg in (shapes or {}).items():
            if not isinstance(cfg, dict):
                continue
            topic = cfg.get("topic")
            seeds = cfg.get("seeds") or []
            rules = cfg.get("rules") or {}
            # seeds
            for s in seeds:
                if isinstance(s, str) and s.strip():
                    token = s.strip().lower()
                    if token not in self._seeds:
                        added["seeds"] += 1
                    self._seeds.add(token)
                    if isinstance(topic, str) and topic:
                        self._topic_alias[token] = topic
            # alias the shape name itself
            if isinstance(topic, str) and topic:
                self._topic_alias[str(name).lower()] = topic
                added["aliases"] += 1
            # rules
            if isinstance(rules, dict):
                for rk, rv in rules.items():
                    rk = str(rk)
                    rv = str(rv)
                    if rk not in cur_rules:
                        added["rules"] += 1
                    cur_rules[rk] = rv
        self._cog.set_rules(cur_rules)
        self._persist_runtime_state()
        return {
            "total_seeds": len(self._seeds),
            "total_aliases": len(self._topic_alias),
            "total_rules": len(cur_rules),
            "added": added,
        }

    def symbols_interpret(self, sequence: str) -> Dict[str, Any]:
        """Parse a simple symbol/node sequence and suggest a route and topics.

        Accepts tokens like "APEX->CORE->EMIT" or emojis "🜂->♾->🚀" and
        returns normalized tokens, any alias topics that match, and a route hint.
        """
        if not isinstance(sequence, str):
            return {"tokens": [], "route": {"action": "process", "target": "local"}, "topics": []}
        raw = sequence.replace("→", "->").replace("—", "->")
        parts = [p.strip() for p in raw.split("->") if p.strip()]
        norm_map = {
            "APEX": "APEX", "🜂": "APEX", "FIRE": "APEX",
            "CORE": "CORE", "♾": "CORE",
            "EMIT": "EMIT", "🚀": "EMIT",
            "ROOT": "ROOT", "🌳": "ROOT",
            "CUBE": "CUBE", "🧊": "CUBE",
        }
        tokens: list[str] = [norm_map.get(p.upper(), p.upper()) for p in parts]
        topics: list[str] = []
        for t in tokens:
            alias = self._topic_alias.get(t.lower()) or self._topic_alias.get(t)
            if alias and alias not in topics:
                topics.append(alias)
        action = "process"
        target = "local"
        if tokens[:3] == ["APEX", "CORE", "EMIT"]:
            action = "process"
        elif "ROOT" in tokens:
            action = "help" if "APEX" in tokens else "status"
        elif "CUBE" in tokens:
            action = "stress_test"
        return {"tokens": tokens, "topics": topics, "route": {"action": action, "target": target}}

    def aliases_get(self) -> Dict[str, Any]:
        return {"aliases": dict(self._topic_alias)}

    # --- Activation Presets -------------------------------------------------
    def activate(self, preset: str) -> Dict[str, Any]:
        """Run a safe, idempotent activation sequence.

        Presets:
          - "standard": rebuild small pools, seed context, save
          - "enhanced": larger pools, seed more, apply rule upgrade, save

        Does not change environment variables; returns hints for optional env toggles.
        """
        preset = (preset or "standard").lower()
        if preset not in ("standard", "enhanced"):
            preset = "standard"
        # Plan sizing
        pools = 2 if preset == "standard" else 3
        size = 5 if preset == "standard" else 7
        # Rebuild
        self.rebuild(pools, size)
        # Seed context
        seeds = [
            "status help baseline",
            "quantum cognition load metrics",
            "upgrade rules suggestions apply",
            "reflective memory topic indexing",
        ]
        if preset == "enhanced":
            seeds.extend([
                "stress benchmark throughput",
                "ethics guard sensitive",
            ])
        for s in seeds:
            try:
                self.cog_process(s)
            except Exception:
                pass
        # Optional: upgrade rules for enhanced
        upgraded = False
        if preset == "enhanced":
            try:
                self.upgrade_apply()
                upgraded = True
            except Exception:
                upgraded = False
        # Persist snapshot
        try:
            self.state_save()
        except Exception:
            pass
        # Hints for env (user can set and restart if desired)
        hints = {
            "use_pca": "Set QNF_USE_NUMPY=1 and QNF_USE_PCA=1 then restart to enable PCA metrics",
            "emb_dim": "Optionally set QNF_EMB_DIM (e.g., 32)",
        }
        return {
            "preset": preset,
            "pools": pools,
            "pool_size": size,
            "seeds": len(seeds),
            "rules_upgraded": upgraded,
            "hints": hints,
            "threads": len(self._threads),
            "intents": dict(self._intent_counts),
            "topics": dict(self._topic_counts),
        }

    def cog_status(self) -> Dict[str, Any]:
        return self._cog.status()

    def cog_get_rules(self) -> Dict[str, Any]:
        return {"rules": self._cog.get_rules()}

    def cog_set_rules(self, rules: Dict[str, str]) -> Dict[str, Any]:
        self._cog.set_rules(rules)
        return {"status": "ok", "rules": self._cog.get_rules()}

    def cog_memory_snapshot(self) -> Dict[str, Any]:
        return self._cog.memory_snapshot()

    def cog_memory_clear(self) -> Dict[str, Any]:
        self._cog.memory_clear()
        return {"status": "ok"}

    def cog_prime_metrics(self) -> Dict[str, Any]:
        return self._cog.prime_metrics()

    def cog_suggestions(self, limit: int = 5) -> Dict[str, Any]:
        return {"suggestions": self._cog.generate_rule_suggestions(limit=limit)}

    # --- SentinelPrimeSync (tri-node) -------------------------------------
    def sync_update(self, agent: str, state: Dict[str, Any]) -> Dict[str, Any]:
        st = sync_coordinator.update_agent_state(agent, state)
        payload = {
            "agent": st.agent,
            "timestamp": st.timestamp,
            "content_signature": st.content_signature,
            "sequence_validation": sync_coordinator.validate(sync_coordinator.sequence),
        }
        # Publish event for WebSocket listeners
        bus.publish({"type": "sync.update", "data": payload})
        return payload

    def sync_snapshot(self) -> Dict[str, Any]:
        return sync_coordinator.snapshot()

    def sync_trinode(self) -> Dict[str, Any]:
        return sync_coordinator.trinode_status()

    def sync_validate(self, sequence: list[str]) -> Dict[str, Any]:
        return sync_coordinator.validate(sequence)

    def sync_boot(self) -> list[Dict[str, Any]]:
        return sync_coordinator.boot_sequence()

    # --- Persistence / Self-Upgrade ---------------------------------------
    def _load_state_if_present(self) -> None:
        state = self._store.load()
        rules = state.get("rules")
        memory = state.get("memory")
        profile = state.get("profile")
        threads = state.get("threads")
        stats = state.get("stats")
        seeds = state.get("seeds")
        matrix = state.get("matrix")
        aliases = state.get("aliases")
        threads = state.get("threads")
        stats = state.get("stats")
        if isinstance(rules, dict):
            self._cog.set_rules(rules)
        if isinstance(memory, list):
            self._cog.memory_load(memory)
        if isinstance(profile, dict):
            self._profile = profile
            try:
                self._cog.set_profile(self._profile)
            except Exception:
                pass
        # Restore threads, stats, seeds and matrix if present
        try:
            if isinstance(threads, dict):
                self._threads = threads
                self._topic_to_thread.clear()
                for tid, th in threads.items():
                    topic = th.get("topic")
                    if isinstance(topic, str):
                        self._topic_to_thread.setdefault(topic, tid)
            if isinstance(stats, dict):
                ic = stats.get("intents") or {}
                tc = stats.get("topics") or {}
                if isinstance(ic, dict):
                    self._intent_counts = {str(k): int(v) for k, v in ic.items()}
                if isinstance(tc, dict):
                    self._topic_counts = {str(k): int(v) for k, v in tc.items()}
            if isinstance(seeds, list):
                self._seeds = {str(x).lower() for x in seeds}
            if isinstance(matrix, dict):
                self._topic_matrix = {str(k): {str(kk): int(vv) for kk, vv in (v or {}).items()} for k, v in matrix.items()}
            if isinstance(aliases, dict):
                self._topic_alias = {str(k).lower(): str(v) for k, v in aliases.items()}
        except Exception:
            pass

    def state_save(self) -> Dict[str, Any]:
        snapshot = {
            "rules": self._cog.get_rules(),
            "memory": self._cog.memory_snapshot().get("top_preview", []),
            "profile": self._profile,
            "threads": self._threads,
            "stats": {"intents": self._intent_counts, "topics": self._topic_counts},
            "seeds": sorted(self._seeds),
            "matrix": self._topic_matrix,
            "aliases": self._topic_alias,
        }
        self._store.save(snapshot)
        return {"status": "ok", "saved": True}

    def _persist_runtime_state(self) -> None:
        """Persist threads and stats opportunistically."""
        try:
            base = self._store.load() or {}
            base["threads"] = self._threads
            base["stats"] = {"intents": self._intent_counts, "topics": self._topic_counts}
            base["seeds"] = sorted(self._seeds)
            base["matrix"] = self._topic_matrix
            self._store.save(base)
        except Exception:
            pass

    def state_dump(self) -> Dict[str, Any]:
        base = self._store.load() or {}
        base.setdefault("profile", self._profile)
        return base

    def upgrade_plan(self) -> Dict[str, Any]:
        metrics = self._cog.prime_metrics()
        suggestions = self._cog.generate_rule_suggestions(limit=10)
        return {"prime": metrics, "suggestions": suggestions}

    def upgrade_apply(self) -> Dict[str, Any]:
        # Merge suggestions into rules; later we can add tunables for pools, etc.
        current = self._cog.get_rules()
        for pair in self._cog.generate_rule_suggestions(limit=50):
            current.setdefault(pair["pattern"], pair["tag"])
        self._cog.set_rules(current)
        self._store.save({
            "rules": current,
            "memory": self._cog.memory_snapshot().get("top_preview", []),
            "profile": self._profile,
        })
        bus.publish({"type": "upgrade.apply", "data": {"rules_count": len(current)}})
        return {"status": "ok", "rules_count": len(current)}

    # --- Sentinel Profile API ---------------------------------------------
    def profile_get(self) -> Dict[str, Any]:
        return dict(self._profile)

    def profile_initialize(self) -> Dict[str, Any]:
        self._profile = initialize_sentinel(self._profile)
        try:
            self._cog.set_profile(self._profile)
        except Exception:
            pass
        return dict(self._profile)

    # --- Nexus Notes API ----------------------------------------------------
    def notes_list(self) -> list[Dict[str, Any]]:
        out: list[Dict[str, Any]] = []
        for nid, note in self._notes.items():
            vec = note.get("centroid")
            out.append({
                "id": nid,
                "tag": note.get("tag"),
                "count": note.get("count", 0),
                "vec_dim": len(vec) if isinstance(vec, list) else 0,
            })
        return sorted(out, key=lambda x: x.get("id", ""))

    def notes_upsert(self, note_id: str, text: Optional[str] = None, vec: Optional[list[float]] = None, weight: float = 1.0, tag: Optional[str] = None) -> Dict[str, Any]:
        if not note_id:
            raise ValueError("note_id is required")
        if vec is None and text is None:
            raise ValueError("either vec or text must be provided")
        if vec is None and text is not None:
            # Compute embedding via cognitive overlay
            a = QuantumAtom(data=text)
            e = self._cog.sp.cno.execute(a)  # type: ignore[attr-defined]
            vec = e.metadata.get("neural_vec")
            if not isinstance(vec, list):
                raise ValueError("could not compute embedding from text")
        note = self._notes.get(note_id, {"centroid": None, "count": 0, "tag": None})
        c = note.get("centroid")
        n = int(note.get("count", 0))
        w = float(weight) if weight > 0 else 1.0
        if not isinstance(c, list) or not c:
            new_c = list(vec or [])
            new_n = int(w)
        else:
            if len(c) != len(vec or []):
                raise ValueError("vector dimension mismatch")
            new_c = [ (n*cv + w*vv) / (n + w) for cv, vv in zip(c, vec or []) ]
            new_n = int(n + w)
        if tag is not None:
            note["tag"] = tag
        note["centroid"] = new_c
        note["count"] = new_n
        self._notes[note_id] = note
        return {"id": note_id, "tag": note.get("tag"), "count": new_n, "vec_dim": len(new_c)}

    # --- Triage tuner controls ---------------------------------------------
    def triage_tuner_get(self) -> Dict[str, Any]:
        return dict(self._tuner)

    def triage_tuner_set(self, enabled: Optional[bool] = None, lr: Optional[float] = None, target_p95_ms: Optional[float] = None) -> Dict[str, Any]:
        if enabled is not None:
            self._tuner["enabled"] = bool(enabled)
        if lr is not None:
            self._tuner["lr"] = float(max(0.0, lr))
        if target_p95_ms is not None:
            self._tuner["target_p95_ms"] = float(max(1.0, target_p95_ms))
        return dict(self._tuner)

    # --- LLM / Chat ---------------------------------------------------------
    def ai_chat(self, messages: list[dict], model: str | None, temperature: float) -> Dict[str, Any]:
        try:
            llm = get_llm()
            return llm.chat(messages=messages, model=model, temperature=temperature)
        except LLMError as e:
            return {"error": str(e)}

    def ai_embeddings(self, texts: list[str], model: str | None) -> Dict[str, Any]:
        try:
            llm = get_llm()
            return llm.embeddings(input=texts, model=model)
        except LLMError as e:
            return {"error": str(e)}

    # Stress testing
    def stress_test(self, iterations: int, concurrent: bool) -> Dict[str, Any]:
        with self._lock:
            return self._qnf.stress_test(iterations=iterations, concurrent=concurrent)

    # Background jobs (for async stress tests)
    def submit_stress_job(self, iterations: int, concurrent: bool) -> str:
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        with self._jobs_lock:
            self._jobs[job_id] = {"status": "queued", "created": time.time()}

        def _run() -> None:
            self._update_job(job_id, status="running")
            try:
                result = self.stress_test(iterations=iterations, concurrent=concurrent)
                self._update_job(job_id, status="completed", result=result)
            except Exception as exc:  # pragma: no cover
                self._update_job(job_id, status="failed", error=str(exc))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return job_id

    def _update_job(
        self, job_id: str, *, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None
    ) -> None:
        with self._jobs_lock:
            payload: Dict[str, Any] = self._jobs.get(job_id, {})
            payload.update({"status": status, "updated": time.time()})
            if result is not None:
                payload["result"] = result
            if error is not None:
                payload["error"] = error
            self._jobs[job_id] = payload

    def job_status(self, job_id: str) -> Dict[str, Any]:
        with self._jobs_lock:
            if job_id not in self._jobs:
                return {"status": "not_found", "job_id": job_id}
            payload = dict(self._jobs[job_id])
            payload["job_id"] = job_id
            return payload


# Singleton service instance
service = QNFService()
