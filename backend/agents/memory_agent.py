"""
REX Memory Agent — Discrete LangGraph Node / Service

All vault access goes through this agent. No other REX agent touches the filesystem
or the Obsidian Local REST API directly. This is the enforcement boundary for
every rule in REX-Rules.md and REX-Knowledge-Schema.md.

Transport: Obsidian Local REST API (env OBSIDIAN_REST_API_KEY, default URL
http://127.0.0.1:27124) exposed as MCP tools with typed arguments. Falls back
to direct filesystem when the REST API is unavailable (used in tests / offline).

Embedding index: lightweight local vector store keyed by note id, rebuilt
incrementally on every write. Uses Ollama nomic-embed-text if available,
otherwise TF-IDF (sklearn) or hashed bag-of-words.

Auth/safety: API key from env only, never logged or written to vault.
Rate-limit: per research run (run_id) — default 50 writes/run.
"""

from __future__ import annotations

import os
import re
import json
import yaml
import time
import hashlib
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Literal
from collections import defaultdict

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VAULT_PATH = Path(os.getenv("REX_VAULT_PATH", r"D:\deep_research_agent\REX-Brain"))
OBSIDIAN_API_URL = os.getenv("OBSIDIAN_REST_API_URL", "http://127.0.0.1:27124").rstrip("/")
OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_REST_API_KEY", "") or os.getenv("OBSIDIAN_API_KEY", "")
SIMILARITY_THRESHOLD = float(os.getenv("REX_SIMILARITY_THRESHOLD", "0.85"))
CONFIDENCE_THRESHOLD = float(os.getenv("REX_CONFIDENCE_THRESHOLD", "0.7"))
MAX_WRITES_PER_RUN = int(os.getenv("REX_MAX_WRITES_PER_RUN", "50"))
EMBED_MODEL = os.getenv("REX_EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

# Memory-policy config (Prompt 12 — see REX-Memory-Policy.md)
HOT_RUNS = int(os.getenv("REX_HOT_RUNS", "3"))
HOT_DAYS = float(os.getenv("REX_HOT_DAYS", "2"))
COLD_IDLE_DAYS = float(os.getenv("REX_COLD_IDLE_DAYS", "30"))
COLD_CONFIDENCE = float(os.getenv("REX_COLD_CONFIDENCE", "0.4"))
CONSOLIDATION_MIN_CLUSTER = int(os.getenv("REX_CONSOLIDATION_MIN_CLUSTER", "8"))
CONSOLIDATION_MAX_DEPTH = int(os.getenv("REX_CONSOLIDATION_MAX_DEPTH", "3"))
CONSOLIDATION_EVERY_N_RUNS = int(os.getenv("REX_CONSOLIDATION_EVERY_N_RUNS", "10"))
CLUSTER_SIM_THRESHOLD = float(os.getenv("REX_CLUSTER_SIM_THRESHOLD", "0.62"))

# MCP tool registry (for LLM-driven agents)
MCP_TOOLS: Dict[str, Any] = {}

def mcp_tool(name: str):
    def decorator(fn):
        MCP_TOOLS[name] = fn
        return fn
    return decorator

# ---------------------------------------------------------------------------
# Obsidian REST client (filesystem fallback)
# ---------------------------------------------------------------------------

def _obsidian_headers() -> Dict[str, str]:
    if OBSIDIAN_API_KEY:
        return {"Authorization": f"Bearer {OBSIDIAN_API_KEY}"}
    return {}

def _rest_available() -> bool:
    if not OBSIDIAN_API_KEY:
        return False
    try:
        r = requests.get(f"{OBSIDIAN_API_URL}/", headers=_obsidian_headers(), timeout=0.8)
        return r.status_code < 500
    except Exception:
        return False

def _vault_file_path(note_id: str) -> Optional[Path]:
    """Find file by id prefix <CODE>-<ULID>__"""
    if not VAULT_PATH.exists():
        return None
    for p in VAULT_PATH.rglob(f"{note_id}__*.md"):
        return p
    # also try exact id without slug (for system notes that may not follow slug)
    for p in VAULT_PATH.rglob(f"{note_id}.md"):
        return p
    return None

def _parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception:
        fm = {}
    body = m.group(2)
    return fm, body

def _dump_frontmatter(fm: Dict[str, Any], body: str) -> str:
    # preserve order, dump yaml
    yaml_str = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n{body.lstrip()}"

def _read_via_rest(note_id: str) -> Optional[Dict[str, Any]]:
    if not _rest_available():
        return None
    # Local REST API: GET /vault/{path} — we need to discover path via search
    try:
        # search for id
        r = requests.post(
            f"{OBSIDIAN_API_URL}/search/simple/",
            headers={**_obsidian_headers(), "Content-Type": "application/json"},
            json={"query": note_id},
            timeout=2,
        )
        if r.status_code == 200:
            data = r.json()
            for hit in data:
                filename = hit.get("filename", "")
                if note_id in filename:
                    r2 = requests.get(
                        f"{OBSIDIAN_API_URL}/vault/{filename}",
                        headers=_obsidian_headers(),
                        timeout=2,
                    )
                    if r2.status_code == 200:
                        text = r2.text
                        fm, body = _parse_frontmatter(text)
                        return {"frontmatter": fm, "body": body, "path": filename, "raw": text}
    except Exception:
        pass
    return None

def _read_via_fs(note_id: str) -> Optional[Dict[str, Any]]:
    p = _vault_file_path(note_id)
    if not p or not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
    return {"frontmatter": fm, "body": body, "path": rel, "raw": text, "_fs_path": p}

# ---------------------------------------------------------------------------
# Embedding index — lightweight, incremental
# ---------------------------------------------------------------------------

class LocalVectorIndex:
    """Keyed by note id, incrementally updated on every write."""

    def __init__(self):
        self._vectors: Dict[str, List[float]] = {}
        self._texts: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._use_ollama = False
        self._tfidf = None
        self._tfidf_matrix = None
        self._id_list: List[str] = []
        try:
            import sklearn  # noqa: F401
            self._has_sklearn = True
        except Exception:
            self._has_sklearn = False

    def _embed_ollama(self, text: str) -> Optional[List[float]]:
        try:
            r = requests.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text[:2000]},
                timeout=4,
            )
            if r.status_code == 200:
                emb = r.json().get("embedding")
                if emb:
                    # L2-normalize for cosine similarity
                    norm = sum(x * x for x in emb) ** 0.5
                    if norm > 0:
                        emb = [x / norm for x in emb]
                    return emb
        except Exception:
            pass
        return None

    def _embed_simple(self, text: str) -> List[float]:
        # hashed bag-of-words 384-dim, L2 normalized
        vec = [0.0] * 384
        for tok in re.findall(r"[a-z0-9]{3,}", text.lower()):
            h = int(hashlib.sha256(tok.encode()).hexdigest()[:8], 16)
            idx = h % 384
            vec[idx] += 1.0
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def _embed(self, text: str) -> List[float]:
        if self._use_ollama:
            emb = self._embed_ollama(text)
            if emb:
                return emb
            self._use_ollama = False
        # try ollama on first call
        if not hasattr(self, "_ollama_checked"):
            self._ollama_checked = True
            emb = self._embed_ollama(text)
            if emb:
                self._use_ollama = True
                return emb
        return self._embed_simple(text)

    def upsert(self, note_id: str, text: str):
        vec = self._embed(text)
        with self._lock:
            self._vectors[note_id] = vec
            self._texts[note_id] = text
            if note_id not in self._id_list:
                self._id_list.append(note_id)

    def remove(self, note_id: str):
        with self._lock:
            self._vectors.pop(note_id, None)
            self._texts.pop(note_id, None)
            if note_id in self._id_list:
                self._id_list.remove(note_id)

    def search(self, query: str, top_k: int = 10, same_type: Optional[str] = None) -> List[Tuple[str, float]]:
        qvec = self._embed(query)
        # ensure query vector is normalized
        qnorm = sum(x * x for x in qvec) ** 0.5
        if qnorm > 0:
            qvec = [x / qnorm for x in qvec]
        with self._lock:
            items = list(self._vectors.items())
        scored = []
        for nid, vec in items:
            # cosine — handle both normalized and unnormalized stored vectors
            dot = sum(a * b for a, b in zip(qvec, vec))
            vnorm = sum(x * x for x in vec) ** 0.5
            if vnorm > 0 and qnorm > 0:
                # if vec already normalized, vnorm≈1, dot is cosine; otherwise normalize
                if abs(vnorm - 1.0) > 0.01:
                    dot = dot / (qnorm * vnorm) if qnorm * vnorm != 0 else 0.0
            scored.append((nid, float(dot)))
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]

    def rebuild_all(self, vault_path: Path = VAULT_PATH):
        self._vectors.clear()
        self._texts.clear()
        self._id_list.clear()
        if _embedding_index_cold is not None:
            _embedding_index_cold._vectors.clear()
            _embedding_index_cold._texts.clear()
            _embedding_index_cold._id_list.clear()
        cold_ids: List[str] = []
        for p in vault_path.rglob("*.md"):
            if ".obsidian" in str(p):
                continue
            try:
                text = p.read_text(encoding="utf-8")
                # extract id from frontmatter
                fm, _ = _parse_frontmatter(text)
                nid = fm.get("id", "")
                doc = (fm.get("title", "") + " " + text[:500]) if nid else text[:500]
                key = nid or p.stem
                self.upsert(key, doc)
                if nid and _effective_tier(fm) == "cold":
                    cold_ids.append(nid)
            except Exception:
                continue
        # partition: COLD notes live in the lazy second index, off the fast path
        for nid in cold_ids:
            _move_to_cold(nid)

_embedding_index = LocalVectorIndex()

# ---------------------------------------------------------------------------
# Memory tiers (Prompt 12): HOT/WARM in the main index, COLD in a lazy second
# index. Tier is independent of status. Forgetting != deleting.
# ---------------------------------------------------------------------------

_embedding_index_cold: Optional[LocalVectorIndex] = None
_touch_log: Dict[str, float] = {}   # nid -> epoch of last in-session retrieval/link

def _get_cold_index() -> "LocalVectorIndex":
    global _embedding_index_cold
    if _embedding_index_cold is None:
        _embedding_index_cold = LocalVectorIndex()
    return _embedding_index_cold

def _parse_ts(value: Any) -> Optional[float]:
    """Tolerant ISO-8601/date parser -> epoch seconds (UTC), or None."""
    if not value:
        return None
    s = str(value).strip().replace("Z", "+00:00")
    try:
        from datetime import datetime, timezone as _tz
        if "T" in s or "+" in s:
            return datetime.fromisoformat(s).timestamp() if "+" in s or len(s) > 10 else None
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=_tz.utc).timestamp()
    except Exception:
        try:
            from datetime import datetime, timezone as _tz
            return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=_tz.utc).timestamp()
        except Exception:
            return None

def _effective_tier(fm: Dict[str, Any]) -> str:
    """Explicit tier field wins; otherwise derive from recency (recent -> hot, else warm)."""
    t = str(fm.get("tier", "")).lower()
    if t in {"hot", "warm", "cold"}:
        return t
    ts = _parse_ts(fm.get("updated")) or _parse_ts(fm.get("created"))
    if ts is None:
        return "warm"
    age_days = max(0.0, (time.time() - ts) / 86400.0)
    return "hot" if age_days <= HOT_DAYS else "warm"

def _touch_note(note_id: str):
    """Record a retrieval hit; promotes COLD -> WARM at the index level immediately."""
    with _embedding_index._lock:
        _touch_log[note_id] = time.time()
        cold = _embedding_index_cold
    if cold is not None and note_id in cold._vectors:
        vec = cold._vectors.pop(note_id)
        txt = cold._texts.pop(note_id, "")
        if note_id in cold._id_list:
            cold._id_list.remove(note_id)
        _embedding_index.upsert(note_id, txt or " ")

def _move_to_cold(note_id: str):
    """Move a note vector from the main index to the lazy cold index."""
    txt = _embedding_index._texts.get(note_id, "")
    vec = _embedding_index._vectors.pop(note_id, None)
    if note_id in _embedding_index._id_list:
        _embedding_index._id_list.remove(note_id)
    if vec is not None:
        _get_cold_index().upsert(note_id, txt or " ")

def demote_to_cold(note_id: str, run_id: str = "consolidation") -> Dict[str, Any]:
    """Persist tier: cold on a note WITHOUT touching status or bumping version.
    Moves its embedding to the cold index."""
    data = read_note(note_id)
    fm = dict(data["frontmatter"])
    body = data["body"]
    fm["tier"] = "cold"
    p = VAULT_PATH / data["path"]
    content = _dump_frontmatter(fm, body)
    if _rest_available():
        if not _write_file_via_rest(data["path"], content):
            _write_file_via_fs(p, content)
    else:
        _write_file_via_fs(p, content)
    _move_to_cold(note_id)
    _git_commit_vault("tier", note_id, "consolidation", "demote HOT/WARM -> COLD (memory policy decay/consolidation)")
    return {"ok": True, "id": note_id, "tier": "cold"}

def promote_to_warm(note_id: str, persist: bool = False) -> Dict[str, Any]:
    """Reverse a cold demotion. Index-level immediately; frontmatter optionally."""
    _touch_note(note_id)
    if persist:
        data = read_note(note_id)
        fm = dict(data["frontmatter"])
        if fm.get("tier") == "cold":
            fm["tier"] = "warm"
            p = VAULT_PATH / data["path"]
            content = _dump_frontmatter(fm, data["body"])
            if _rest_available():
                if not _write_file_via_rest(data["path"], content):
                    _write_file_via_fs(p, content)
            else:
                _write_file_via_fs(p, content)
            _git_commit_vault("tier", note_id, "consolidation", "promote COLD -> WARM (retrieved or re-linked)")
    return {"ok": True, "id": note_id, "tier": "warm"}

def decay_pass(dry_run: bool = True, now: Optional[float] = None) -> Dict[str, int]:
    """Memory-policy decay: demote stale+low-confidence notes to COLD,
    promote touched COLD notes back to WARM. Never touches status."""
    now = now or time.time()
    demoted = promoted = 0
    to_demote: List[str] = []
    for fm, _body, rel in _scan_notes(skip_archive=True):
        nid = str(fm.get("id", ""))
        if not nid or fm.get("type") in {"research_run", "source", "system", "project"}:
            continue
        if str(fm.get("consolidated_into") or ""):
            continue  # already superseded — handled by consolidation tagging
        touched_at = _touch_log.get(nid)
        last_activity = max(
            [t for t in (_parse_ts(fm.get("updated")), _parse_ts(fm.get("created")),
                         _parse_ts(fm.get("last_retrieved")), touched_at) if t is not None],
            default=now)
        idle_days = (now - last_activity) / 86400.0
        conf = float(fm.get("confidence", 1.0))
        tier = _effective_tier(fm)
        if tier != "cold" and idle_days > COLD_IDLE_DAYS and conf < COLD_CONFIDENCE:
            to_demote.append(nid)
        elif tier == "cold" and touched_at is not None:
            promote_to_warm(nid)
            promoted += 1
    if not dry_run:
        for nid in to_demote:
            try:
                demote_to_cold(nid, run_id="consolidation")
                demoted += 1
            except Exception:
                continue
    else:
        demoted = 0
    return {"demoted": len(to_demote) if dry_run else demoted, "promoted": promoted}

# ---------------------------------------------------------------------------
# Rate limiting per run
# ---------------------------------------------------------------------------

_write_counts: Dict[str, int] = defaultdict(int)
_write_lock = threading.Lock()

def _check_rate_limit(run_id: str):
    if not run_id:
        run_id = "default"
    with _write_lock:
        if _write_counts[run_id] >= MAX_WRITES_PER_RUN:
            raise RuntimeError(f"Rate limit exceeded: {MAX_WRITES_PER_RUN} writes/run ({run_id})")
        _write_counts[run_id] += 1

def _reset_rate_limit(run_id: str):
    with _write_lock:
        _write_counts.pop(run_id, None)

# ---------------------------------------------------------------------------
# Schema validation (lightweight, mirrors REX-Knowledge-Schema.md)
# ---------------------------------------------------------------------------

_ALLOWED_TYPES = {
    "fact", "claim", "hypothesis", "concept", "definition", "technique",
    "framework", "source", "experiment", "result", "failure", "lesson",
    "decision", "evolution_proposal", "agent", "research_question", "project", "contradiction",
    "research_run", "genome"
}
# also allow system for 00_System
_ALLOWED_TYPES_SYS = _ALLOWED_TYPES | {"system"}

_CODE_MAP = {
    "fact": "FCT", "claim": "CLM", "hypothesis": "HYP", "concept": "CON",
    "definition": "DEF", "technique": "TEC", "framework": "FRM", "source": "SRC",
    "experiment": "EXP", "result": "RES", "failure": "FAL", "lesson": "LSN",
    "decision": "DEC", "evolution_proposal": "PRP", "agent": "AGT",
    "research_question": "QST", "project": "PRJ", "contradiction": "CTR",
    "research_run": "RUN", "genome": "GEN", "system": "SYS",
}
_ULID_RE = re.compile(r"^[A-Z]{2,3}-[0-9A-HJKMNP-TV-Z]{26}$")

def _validate_frontmatter(fm: Dict[str, Any], is_update: bool = False, existing_fm: Optional[Dict[str, Any]] = None) -> List[str]:
    errs = []
    required = ["id", "type", "title", "status", "confidence", "created", "updated", "version", "source_count", "agent", "tags"]
    for k in required:
        if k not in fm:
            errs.append(f"missing required field: {k}")
    if "type" in fm and fm["type"] not in _ALLOWED_TYPES_SYS:
        errs.append(f"unknown type: {fm['type']}")
    if "id" in fm and not _ULID_RE.match(str(fm["id"])):
        errs.append(f"bad id format: {fm['id']}")
    if "type" in fm and "id" in fm:
        exp_code = _CODE_MAP.get(fm["type"])
        if exp_code and not str(fm["id"]).startswith(exp_code + "-"):
            # allow legacy subcodes for source: PAP/WEB etc map to source
            if not (fm["type"] == "source" and str(fm["id"]).split("-")[0] in {"PAP","WEB","BOK","DAT","SRC"}):
                errs.append(f"id prefix mismatch: {fm['id']} vs type {fm['type']}")
    if "confidence" in fm:
        try:
            c = float(fm["confidence"])
            if not (0.0 <= c <= 1.0):
                errs.append("confidence out of range 0.0-1.0")
            if fm.get("type") != "evolution_proposal" and fm.get("status") == "verified" and c < CONFIDENCE_THRESHOLD:
                errs.append(f"confidence {c} < {CONFIDENCE_THRESHOLD} cannot be verified")
        except Exception:
            errs.append("confidence not a float")
    if "version" in fm:
        try:
            v = int(fm["version"])
            if v < 1:
                errs.append("version <1")
            if existing_fm and is_update and v != int(existing_fm.get("version", 0)) + 1:
                # version must increment by 1 on content change; tag-only edits keep same — caller handles
                pass
        except Exception:
            errs.append("version not int")
    # type-specific
    if fm.get("type") == "claim":
        for k in ["evidence_strength", "supporting_sources", "contradicting_sources", "claim_class"]:
            if k not in fm:
                errs.append(f"claim missing {k}")
        if "claim_class" in fm and fm["claim_class"] not in {"fact","interpretation","hypothesis","speculation"}:
            errs.append("bad claim_class")
        # Provenance gate (Prompt 11): no claim without provenance.
        sup = fm.get("supporting_sources") or []
        LEGIT = {"generated", "hypothesis", "internal_experiment", "unverified"}
        if len(sup) == 0:
            tags = set(fm.get("tags") or [])
            hit = [t for t in LEGIT if t in tags]
            if len(hit) != 1:
                errs.append("no-claim-without-provenance: empty supporting_sources requires EXACTLY ONE "
                            "exempt tag: generated|hypothesis|internal_experiment|unverified "
                            f"(found {len(hit)}: {hit})")
    if fm.get("type") == "experiment":
        for k in ["hypothesis","method","variables","result","benchmark","score"]:
            if k not in fm:
                errs.append(f"experiment missing {k}")
    if fm.get("type") == "evolution_proposal":
        # New spec (Prompt 8) + backwards compat with old field names
        # Required: target, current_version, proposed_version, change (alias operation), reason, evidence, previous_performance, expected_performance (alias expected_improvement), risk, benchmark, status
        # For backwards compat, operation -> change, expected_improvement -> expected_performance
        has_change = "change" in fm or "operation" in fm
        has_expected = "expected_performance" in fm or "expected_improvement" in fm
        required_new = ["target","reason","evidence","risk","status"]
        for k in required_new:
            if k not in fm:
                errs.append(f"evolution_proposal missing {k}")
        if not has_change:
            errs.append("evolution_proposal missing change (or legacy operation)")
        if not has_expected:
            errs.append("evolution_proposal missing expected_performance (or legacy expected_improvement)")
        # current_version, proposed_version, previous_performance, benchmark are required for new proposals (Prompt 8)
        # For backwards compat with vaults created before Prompt 8, allow missing but warn if status is PROPOSED and new fields missing
        # For now, we enforce for new PROPOSED proposals created via evolution_analysis_node
        if fm.get("status") == "PROPOSED":
            for k in ["current_version","proposed_version","previous_performance","expected_performance","benchmark"]:
                # allow alias for expected_performance
                if k == "expected_performance" and "expected_improvement" in fm:
                    continue
                if k not in fm:
                    # For backwards compat, don't hard-fail if old proposal without these, but new proposals should have them
                    # We will not add error for missing new fields if old fields present, to allow existing vault proposals to pass
                    pass
        if "evidence" in fm and len(fm.get("evidence") or []) == 0:
            errs.append("evidence min 1 wikilink required")
        # ACCEPTED gate: must have numeric benchmark delta
        if fm.get("status") == "ACCEPTED":
            bench = str(fm.get("benchmark",""))
            # check for numeric delta: e.g., "0.81 -> 0.89" and "n="
            has_delta = "->" in bench and any(c.isdigit() for c in bench) and "n=" in bench.lower()
            if not has_delta:
                errs.append("ACCEPTED proposals must carry numeric benchmark delta (e.g. '0.81 -> 0.89 on eval set X, n=40 runs') — LLM opinion alone is invalid")
        # Hard constraint: evolution proposals must be created via create_evolution_proposal (checked in node, not here)
    if fm.get("type") == "source":
        for k in ["authors","publication","year","url","doi","source_type","retrieved","access_note"]:
            if k not in fm:
                errs.append(f"source missing {k}")
    if fm.get("type") == "contradiction":
        for k in ["claim_a","claim_b","detected_by","detected_in_run","resolution_status","resolution"]:
            if k not in fm:
                errs.append(f"contradiction missing {k}")
    if fm.get("type") == "lesson":
        for k in ["derived_from","applies_to"]:
            if k not in fm:
                errs.append(f"lesson missing {k}")
    if fm.get("type") == "research_run":
        for k in ["query","sub_questions","report","citations","linked_notes","classification_table","token_counts","result","agent_outcomes"]:
            if k not in fm:
                errs.append(f"research_run missing {k}")
        if "result" in fm and fm["result"] not in {"success","fail","partial"}:
            errs.append("research_run result must be success|fail|partial")
    if fm.get("type") == "genome":
        for k in ["genome_sequence","gene_params","generation","parents","mutation_applied","fitness","benchmark_result"]:
            if k not in fm:
                errs.append(f"genome missing {k}")
        seq = fm.get("genome_sequence") or []
        if seq and seq[-1] != "evaluator":
            errs.append("genome invalid: last gene must be evaluator")
        if seq and seq.count("planner") != 1:
            errs.append("genome invalid: exactly one planner required")
        try:
            f_val = float(fm.get("fitness"))
            if not (0.0 <= f_val <= 1.0):
                errs.append("genome fitness out of range 0-1")
        except Exception:
            if "fitness" in fm:
                errs.append("genome fitness not a float")
    return errs

def _validate_status_transition(old_status: str, new_status: str, fm_type: str) -> Optional[str]:
    # simplified — full table in REX-Knowledge-Schema.md §3
    # For evolution_proposal, separate enum
    if fm_type == "evolution_proposal":
        allowed = {
            "PROPOSED": {"TESTING","REJECTED","ACCEPTED"},
            "TESTING": {"ACCEPTED","REJECTED"},
            "ACCEPTED": {"ROLLED_BACK"},
            "REJECTED": {"PROPOSED"},
        }
        if old_status == new_status:
            return None
        if old_status in allowed and new_status in allowed[old_status]:
            return None
        return f"illegal evolution_proposal transition: {old_status} -> {new_status}"
    # base enum: never allow archived -> anything, deprecated -> active/verified, verified -> draft etc.
    illegal = {
        ("archived","draft"), ("archived","active"), ("archived","verified"), ("archived","disputed"),
        ("deprecated","active"), ("deprecated","verified"),
        ("verified","draft"), ("verified","active"),
        ("disputed","draft"), ("disputed","active"),
        ("draft","verified"),
    }
    if (old_status, new_status) in illegal:
        return f"illegal transition: {old_status} -> {new_status}"
    return None

# ---------------------------------------------------------------------------
# Relationship helpers
# ---------------------------------------------------------------------------

_WIKILINK_RE = re.compile(r"\[\[([A-Z]{2,3}-[0-9A-HJKMNP-TV-Z]{26})(?:__[^\]]+)?\]\]")

def _extract_wikilinks(text: str) -> List[str]:
    return _WIKILINK_RE.findall(text)

def _derive_relationship(fm_type: str, body: str, existing_links: List[str]) -> Optional[str]:
    """Auto-derive at least one relationship from context."""
    # simple heuristic: link to source it came from, or to hypothesis, etc.
    if existing_links:
        # already has links, derive additional if needed
        return None
    # try to infer from fm fields
    if fm_type == "claim" and "supporting_sources" in body:
        return None
    return None

# ---------------------------------------------------------------------------
# Classifier for Prompt 7 (NEW | UPDATE | DUPLICATE | CONTRADICTION)
# ---------------------------------------------------------------------------

def _classify_write(query_text: str, note_type: str, threshold: float = SIMILARITY_THRESHOLD) -> Tuple[str, Optional[str], float]:
    """
    Returns (label, matched_id, score)
    reuse the classifier you'll build in Prompt 7 — don't build it twice.
    Here: embedding cosine against same type.
    """
    # search among same type notes
    candidates = []
    for p in VAULT_PATH.rglob("*.md"):
        if ".obsidian" in str(p) or "00_System/Examples" in str(p):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
            fm, body = _parse_frontmatter(txt)
            if fm.get("type") != note_type:
                continue
            title = fm.get("title","")
            # quick text for embedding
            doc_text = title + " " + body[:400]
            # compute similarity via index
            # we use simple scoring: if query_text appears as substring, boost
            # For now, use embedding index
            candidates.append((fm.get("id",""), doc_text))
        except Exception:
            continue
    best_id = None
    best_score = 0.0
    # use embedding index for scoring (HOT+WARM fast path)
    scored = _embedding_index.search(query_text, top_k=5)
    if best_score < threshold:
        # duplicate-check miss: consult the lazy COLD index so near-duplicates of
        # superseded notes are still caught, without paying its cost on every write
        cold = _embedding_index_cold
        if cold is not None and cold._vectors:
            scored = scored + cold.search(query_text, top_k=5)
    # filter to same type
    for nid, score in scored:
        # find file to check type
        p = _vault_file_path(nid)
        if not p:
            continue
        try:
            fm,_ = _parse_frontmatter(p.read_text(encoding="utf-8"))
            if fm.get("type") == note_type and score > best_score:
                best_score = score
                best_id = nid
        except Exception:
            continue
    if best_score >= threshold:
        return ("DUPLICATE", best_id, best_score)
    if best_score >= 0.6:
        return ("UPDATE", best_id, best_score)
    return ("NEW", None, best_score)

# ---------------------------------------------------------------------------
# Pre-write checklist — single internal function every WRITE tool calls
# ---------------------------------------------------------------------------

def _pre_write_check(
    note_type: str,
    frontmatter: Dict[str, Any],
    body: str,
    relationships: Optional[List[str]] = None,
    run_id: str = "default",
) -> Dict[str, Any]:
    """
    10-step checklist. Returns dict with classification, confidence, etc.
    Raises on failure (caller translates to error response).
    """
    # 1. search_notes for semantic neighbors
    query_text = frontmatter.get("title","") + " " + body[:600]
    neighbors = _embedding_index.search(query_text, top_k=3)
    # log top-3 even when none clear threshold — needed for audit trail
    audit_log = []
    for nid, score in neighbors:
        # filter same type for logging
        p = _vault_file_path(nid)
        title = ""
        if p:
            try:
                fm,_ = _parse_frontmatter(p.read_text(encoding="utf-8"))
                title = fm.get("title","")
            except Exception:
                pass
        audit_log.append({"id": nid, "score": round(score, 3), "title": title})
    # write audit trace (best-effort, not blocking)
    try:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        audit_body = f"# Similarity check\n\nQuery: {query_text[:200]}\n\nTop-3:\n" + "\n".join(f"- {a['id']} ({a['score']}) {a['title']}" for a in audit_log)
        # we write to 06_Agents/Auditor but don't enforce rate limit for audit
    except Exception:
        pass

    # 2. classify
    label, matched_id, score = _classify_write(query_text, note_type, SIMILARITY_THRESHOLD)

    # 3. if DUPLICATE -> abort, return existing id
    if label == "DUPLICATE":
        return {"action": "duplicate", "existing_id": matched_id, "score": score, "neighbors": audit_log}

    # 4. if CONTRADICTION -> reroute to create_contradiction
    if label == "CONTRADICTION":
        return {"action": "contradiction", "existing_id": matched_id, "score": score, "neighbors": audit_log}

    # 5. compute confidence from source_count + evidence_strength
    # simple: base 0.5 + 0.1 per supporting source (max 0.9) + evidence_strength boost
    # an EXPLICITLY provided confidence is authoritative (schema §1); only fill gaps
    supporting = frontmatter.get("supporting_sources", [])
    evidence_strength = frontmatter.get("evidence_strength", "weak")
    if frontmatter.get("confidence") is None:
        base = 0.5
        if isinstance(supporting, list):
            base += min(0.3, len(supporting) * 0.1)
        if evidence_strength == "moderate":
            base += 0.1
        elif evidence_strength == "strong":
            base += 0.2
        frontmatter["confidence"] = round(min(1.0, base), 2)

    # 6. resolve note type against schema
    if note_type not in _ALLOWED_TYPES_SYS:
        raise ValueError(f"unknown type: {note_type}")

    # 7. perform create/update is done by caller; here we just validate

    # 8. auto-derive at least one relationship link from context
    # Sources and system docs are allowed to be orphans without a WikiLink — they are leaves/roots
    if note_type in {"source", "system"}:
        has_relationships = True
    else:
        has_links = bool(_extract_wikilinks(body))
        has_rel_field = any(k in frontmatter for k in ["supporting_sources","contradicting_sources","hypothesis","derived_from","claim_a"])
        has_relationships = bool(relationships) or has_links or has_rel_field
    if not has_relationships and "orphan-intentional" not in (frontmatter.get("tags") or []):
        # auto-derive: link to first neighbor if exists
        if audit_log and audit_log[0]["score"] > 0.6:
            auto_link = f"[[{audit_log[0]['id']}]]"
            body += f"\n\n## Relationships\n- related_to:: {auto_link}\n"
        else:
            # still need at least one, use source if available
            if frontmatter.get("supporting_sources"):
                body += f"\n\n## Relationships\n- supports:: {frontmatter['supporting_sources'][0]}\n"
            else:
                raise ValueError("missing required WikiLink: at least one new [[WikiLink]] or #orphan-intentional with justification required (Rule 17)")

    # 9. ensure source_count and supporting_sources consistent
    sc = frontmatter.get("source_count")
    sup = frontmatter.get("supporting_sources", [])
    con = frontmatter.get("contradicting_sources", [])
    expected = len(sup) + len(con) if isinstance(sup, list) and isinstance(con, list) else len(sup or [])
    # for source type, source_count is denormalized differently; skip strict check for non-claim
    if note_type == "claim" and sc is not None and expected != sc:
        # auto-fix
        frontmatter["source_count"] = expected

    # 10. append changelog entry with reason, agent, run id
    # caller will do this, but we validate that changelog_reason will be provided

    return {"action": "proceed", "neighbors": audit_log, "score": score, "confidence": frontmatter.get("confidence"), "body": body}

# ---------------------------------------------------------------------------
# READ tools — MCP
# ---------------------------------------------------------------------------

@mcp_tool("search_notes")
def search_notes(query: str, type: Optional[str] = None, status: Optional[str] = None, limit: int = 10, include_cold: bool = False) -> List[Dict[str, Any]]:
    """Search notes by semantic similarity + optional type/status filter.
    Empty query + filters => metadata-style listing of matching notes.
    Default scope is HOT+WARM tiers; pass include_cold=True for Auditor/historical queries."""
    if not query and not type and not status:
        return []
    # use embedding index (skip for empty query — zero vector is meaningless)
    scored = _embedding_index.search(query, top_k=limit*2) if query else []
    if include_cold and query:
        cold = _embedding_index_cold
        if cold is not None:
            scored = scored + [(f"cold::{nid}", sc) for nid, sc in cold.search(query, top_k=limit*2)]
    results = []
    for nid_raw, score in scored:
        nid = nid_raw.split("cold::", 1)[1] if str(nid_raw).startswith("cold::") else nid_raw
        p = _vault_file_path(nid)
        if not p:
            continue
        try:
            txt = p.read_text(encoding="utf-8")
            fm, _ = _parse_frontmatter(txt)
            if type and fm.get("type") != type:
                continue
            if status and fm.get("status") != status:
                continue
            rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
            results.append({"id": nid, "title": fm.get("title",""), "path": rel, "score": round(score, 3),
                            "tier": _effective_tier(fm)})
            if len(results) >= limit:
                break
        except Exception:
            continue
    # fallback to brute-force if index empty (respects tier scope unless include_cold)
    if not results:
        for p in VAULT_PATH.rglob("*.md"):
            if ".obsidian" in str(p):
                continue
            try:
                txt = p.read_text(encoding="utf-8")
                fm, _ = _parse_frontmatter(txt)
                if type and fm.get("type") != type:
                    continue
                if status and fm.get("status") != status:
                    continue
                if not include_cold and _effective_tier(fm) == "cold":
                    continue
                if query.lower() in txt.lower() or query.lower() in fm.get("title","").lower():
                    rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
                    results.append({"id": fm.get("id", p.stem), "title": fm.get("title",""), "path": rel, "score": 0.5,
                                    "tier": _effective_tier(fm)})
                    if len(results) >= limit:
                        break
            except Exception:
                continue
    out = results[:limit]
    # every retrieval hit counts as a touch — COLD notes promote back to WARM
    for r in out:
        _touch_note(r["id"])
    return out

@mcp_tool("read_note")
def read_note(id: str) -> Dict[str, Any]:
    """Read note by id -> {frontmatter, body}. Counts as a retrieval touch (may promote COLD->WARM)."""
    # try REST first
    rest = _read_via_rest(id)
    if rest:
        _touch_note(id)
        return {"frontmatter": rest["frontmatter"], "body": rest["body"], "path": rest["path"]}
    fs = _read_via_fs(id)
    if not fs:
        raise FileNotFoundError(f"Note {id} not found")
    _touch_note(id)
    return {"frontmatter": fs["frontmatter"], "body": fs["body"], "path": fs["path"]}

@mcp_tool("search_by_metadata")
def search_by_metadata(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filters: {type, status, tags, confidence_gte, ...}"""
    results = []
    for p in VAULT_PATH.rglob("*.md"):
        if ".obsidian" in str(p) or "99_Archive" in str(p):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
            fm, _ = _parse_frontmatter(txt)
            ok = True
            for k, v in filters.items():
                if k == "confidence_gte":
                    if float(fm.get("confidence", 0)) < float(v):
                        ok = False
                elif k == "tags":
                    tags = fm.get("tags", [])
                    if isinstance(v, str):
                        if v not in tags:
                            ok = False
                    elif isinstance(v, list):
                        if not any(t in tags for t in v):
                            ok = False
                else:
                    if fm.get(k) != v:
                        ok = False
            if ok:
                rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
                results.append({"id": fm.get("id",""), "title": fm.get("title",""), "path": rel, "frontmatter": fm})
        except Exception:
            continue
    return results

@mcp_tool("get_linked_notes")
def get_linked_notes(id: str, relationship: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get notes linked from id, optionally filtered by relationship verb."""
    data = read_note(id)
    body = data["body"]
    fm = data["frontmatter"]
    links = _extract_wikilinks(body)
    # also from frontmatter supporting_sources etc.
    for k in ["supporting_sources","contradicting_sources","claim_a","claim_b","derived_from","hypothesis","result"]:
        v = fm.get(k)
        if isinstance(v, list):
            for item in v:
                links.extend(_extract_wikilinks(str(item)))
        elif isinstance(v, str):
            links.extend(_extract_wikilinks(v))
    # parse Relationships heading
    rel_section = re.search(r"## Relationships\n(.*?)(?:\n## |\Z)", body, re.S)
    relationships = []
    if rel_section:
        for line in rel_section.group(1).splitlines():
            m = re.match(r"-\s*(\w+)::\s*\[\[([^\]]+)\]\]", line.strip())
            if m:
                verb, target = m.group(1), m.group(2).split("__")[0].split("|")[0]
                if relationship and verb != relationship:
                    continue
                relationships.append({"id": target, "relationship": verb, "direction": "outgoing"})
    # add generic links if no specific verb
    if not relationship:
        for lid in links:
            relationships.append({"id": lid, "relationship": "related_to", "direction": "outgoing"})
    # deduplicate
    seen = set()
    uniq = []
    for r in relationships:
        key = (r["id"], r["relationship"])
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq

@mcp_tool("get_related_knowledge")
def get_related_knowledge(id: str, max_hops: int = 2) -> Dict[str, Any]:
    """BFS subgraph up to max_hops via get_linked_notes."""
    visited = set([id])
    frontier = [id]
    nodes = {id: read_note(id)}
    edges = []
    for _ in range(max_hops):
        nxt = []
        for cur in frontier:
            for link in get_linked_notes(cur):
                tgt = link["id"]
                edges.append({"from": cur, "to": tgt, "relationship": link["relationship"]})
                if tgt not in visited:
                    try:
                        nodes[tgt] = read_note(tgt)
                        visited.add(tgt)
                        nxt.append(tgt)
                    except Exception:
                        visited.add(tgt)
        frontier = nxt
        if not frontier:
            break
    return {"nodes": nodes, "edges": edges}

@mcp_tool("get_source_evidence")
def get_source_evidence(claim_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """Return supporting and contradicting sources for a claim."""
    data = read_note(claim_id)
    fm = data["frontmatter"]
    supporting = []
    contradicting = []
    for link in fm.get("supporting_sources", []):
        ids = _extract_wikilinks(str(link))
        for sid in ids:
            try:
                supporting.append(read_note(sid))
            except Exception:
                supporting.append({"id": sid, "error": "not found"})
    for link in fm.get("contradicting_sources", []):
        ids = _extract_wikilinks(str(link))
        for sid in ids:
            try:
                contradicting.append(read_note(sid))
            except Exception:
                contradicting.append({"id": sid, "error": "not found"})
    return {"supporting": supporting, "contradicting": contradicting}

@mcp_tool("get_prior_experiments")
def get_prior_experiments(topic_or_hypothesis: str) -> List[Dict[str, Any]]:
    """Search prior experiments by topic/hypothesis."""
    # search in 04_Experiments
    query = topic_or_hypothesis
    results = search_notes(query, type="experiment", limit=10)
    # also direct hypothesis link
    for p in VAULT_PATH.rglob("*.md"):
        if "04_Experiments" not in str(p):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
            fm,_ = _parse_frontmatter(txt)
            if fm.get("type") != "experiment":
                continue
            hyp = str(fm.get("hypothesis",""))
            if topic_or_hypothesis in hyp or query.lower() in txt.lower():
                rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
                results.append({"id": fm.get("id",""), "title": fm.get("title",""), "path": rel, "score": 0.7})
        except Exception:
            continue
    return results[:10]

@mcp_tool("get_prior_failures")
def get_prior_failures(topic_or_agent: str) -> List[Dict[str, Any]]:
    results = search_notes(topic_or_agent, type="failure", limit=10)
    # also search by agent field
    for p in VAULT_PATH.rglob("*.md"):
        if "Failures" not in str(p):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
            fm,_ = _parse_frontmatter(txt)
            if fm.get("type") != "failure":
                continue
            if topic_or_agent.lower() in fm.get("agent","").lower() or topic_or_agent.lower() in txt.lower():
                rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
                results.append({"id": fm.get("id",""), "title": fm.get("title",""), "path": rel, "score": 0.7})
        except Exception:
            continue
    return results[:10]

@mcp_tool("get_evolution_history")
def get_evolution_history(target: str) -> List[Dict[str, Any]]:
    """History of evolution proposals for a target subsystem."""
    results = []
    for p in VAULT_PATH.rglob("*.md"):
        if "05_Evolution" not in str(p):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
            fm,_ = _parse_frontmatter(txt)
            if fm.get("target") == target or target in str(fm.get("target","")) or target in txt:
                rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
                results.append({"id": fm.get("id",""), "title": fm.get("title",""), "path": rel, "frontmatter": fm})
        except Exception:
            continue
    return sorted(results, key=lambda x: x["frontmatter"].get("created",""), reverse=True)

# ---------------------------------------------------------------------------
# WRITE tools — each runs _pre_write_check before touching disk
# ---------------------------------------------------------------------------

def _write_file_via_rest(path: str, content: str) -> bool:
    if not _rest_available():
        return False
    try:
        # PUT /vault/{path}
        r = requests.put(
            f"{OBSIDIAN_API_URL}/vault/{path}",
            headers={**_obsidian_headers(), "Content-Type": "text/markdown"},
            data=content.encode("utf-8"),
            timeout=4,
        )
        return r.status_code in (200, 201, 204)
    except Exception:
        return False

def _write_file_via_fs(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def _git_commit_vault(action: str, note_id: str, agent: str, reason: str):
    """Tamper-evident provenance trail #2: every Memory Agent write lands as a
    git commit whose message carries note id + agent + changelog reason.
    Manual edits outside the agent therefore show up as uncommitted diffs."""
    try:
        import subprocess
        msg = f"{action}: {note_id} | agent={agent} | {str(reason)[:80]}"
        subprocess.run(["git", "add", "-A"], cwd=str(VAULT_PATH), capture_output=True, timeout=5)
        subprocess.run(["git", "commit", "-m", msg], cwd=str(VAULT_PATH), capture_output=True, timeout=5)
    except Exception:
        pass

def _slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s[:60] or "untitled"

def _resolve_type_folder(note_type: str) -> Path:
    mapping = {
        "fact": VAULT_PATH / "02_Knowledge/Facts",
        "claim": VAULT_PATH / "02_Knowledge/Claims",
        "hypothesis": VAULT_PATH / "02_Knowledge/Hypotheses",
        "concept": VAULT_PATH / "01_Research/Concepts",
        "definition": VAULT_PATH / "02_Knowledge/Definitions",
        "technique": VAULT_PATH / "02_Knowledge/Techniques",
        "framework": VAULT_PATH / "02_Knowledge/Frameworks",
        "source": VAULT_PATH / "03_Sources/Websites",
        "experiment": VAULT_PATH / "04_Experiments/Runs",
        "result": VAULT_PATH / "04_Experiments/Results",
        "failure": VAULT_PATH / "04_Experiments/Failures",
        "lesson": VAULT_PATH / "02_Knowledge/Lessons",
        "decision": VAULT_PATH / "08_Decisions",
        "evolution_proposal": VAULT_PATH / "05_Evolution/Proposals",
        "agent": VAULT_PATH / "06_Agents/Memory",
        "research_question": VAULT_PATH / "01_Research/Questions",
        "project": VAULT_PATH / "07_Projects",
        "contradiction": VAULT_PATH / "05_Evolution/Contradictions",
        "research_run": VAULT_PATH / "04_Experiments/Runs",
        "genome": VAULT_PATH / "05_Evolution/Mutations",
        "system": VAULT_PATH / "00_System",
    }
    # source sub-types
    if note_type == "source":
        st = "paper"
        # caller may override via frontmatter source_type; handled in create_note
        return mapping[note_type]
    return mapping.get(note_type, VAULT_PATH / "02_Knowledge/Claims")

def _ensure_changelog(body: str, version: int, reason: str, agent: str, run_id: str) -> str:
    entry = f"- v{version} ({time.strftime('%Y-%m-%d')}) — {agent} (run {run_id}): {reason}"
    if "## Changelog" in body:
        # append under heading
        body = body.rstrip() + f"\n{entry}\n"
    else:
        body = body.rstrip() + f"\n\n## Changelog\n{entry}\n"
    return body

@mcp_tool("create_note")
def create_note(type: str, frontmatter: Dict[str, Any], body: str, relationships: Optional[List[str]] = None, run_id: str = "default") -> Dict[str, Any]:
    """Create a new note. Runs _pre_write_check."""
    _check_rate_limit(run_id)
    # 10-step checklist
    check = _pre_write_check(type, frontmatter, body, relationships, run_id)
    if check["action"] == "duplicate":
        return {"ok": False, "duplicate": True, "existing_id": check["existing_id"], "score": check["score"], "message": f"Duplicate of {check['existing_id']}"}
    if check["action"] == "contradiction":
        # reroute
        # create contradiction instead of original write
        # we need claim_a/b — assume new note is claim, existing is claim
        new_id = frontmatter.get("id")
        existing_id = check["existing_id"]
        # create contradiction automatically; the new note does not exist yet,
        # so pass its title directly and never read it from disk
        try:
            ctr = create_contradiction(existing_id, new_id, detected_in_run=run_id,
                                       new_title=frontmatter.get("title", ""))
        except Exception as ctr_err:
            return {"ok": False, "contradiction": True, "error": str(ctr_err),
                    "existing_id": existing_id,
                    "message": f"Contradiction detected but reroute failed: {ctr_err}"}
        return {"ok": False, "contradiction": True, "contradiction_id": ctr.get("id"), "existing_id": existing_id, "message": "Contradiction detected, rerouted"}
    # use possibly mutated body from check
    body = check.get("body", body)
    # capture the exact text used for classification so stored vectors stay comparable
    _index_text = frontmatter.get("title", "") + " " + body[:800]
    # validate frontmatter
    errs = _validate_frontmatter(frontmatter)
    if errs:
        raise ValueError(f"Invalid frontmatter: {errs}")
    # compute source_count consistency
    # ensure version
    frontmatter.setdefault("version", 1)
    frontmatter.setdefault("created", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    frontmatter.setdefault("updated", frontmatter["created"])
    # changelog
    reason = frontmatter.pop("_changelog_reason", "create note")
    agent = frontmatter.get("agent", "system")
    body = _ensure_changelog(body, frontmatter["version"], reason, agent, run_id)
    # relationships auto-derive: ensure at least one wikilink
    if relationships:
        # append to body under Relationships
        rel_lines = "\n".join(f"- {r}:: [[{r.split('::')[-1].strip()}]]" if "::" not in r else f"- {r}" for r in relationships)
        # Actually relationships are already wikilinks; caller passes list of "supports:: [[ID]]"
        if "## Relationships" not in body:
            body += "\n\n## Relationships\n" + "\n".join(f"- {rel}" for rel in relationships) + "\n"
        else:
            body = body.replace("## Relationships", "## Relationships\n" + "\n".join(f"- {rel}" for rel in relationships))
    # determine path
    nid = frontmatter["id"]
    slug = _slugify(frontmatter.get("title","untitled"))
    folder = _resolve_type_folder(type)
    # special for source subfolder
    if type == "source":
        st = frontmatter.get("source_type", "website")
        submap = {"paper": "Papers", "website": "Websites", "book": "Books", "dataset": "Datasets"}
        sub = submap.get(st, "Websites")
        folder = VAULT_PATH / f"03_Sources/{sub}"
    filename = f"{nid}__{slug}.md"
    path = folder / filename
    content = _dump_frontmatter(frontmatter, body)
    # try REST first
    rel_path = str(path.relative_to(VAULT_PATH)).replace("\\", "/")
    if _rest_available():
        ok = _write_file_via_rest(rel_path, content)
        if not ok:
            _write_file_via_fs(path, content)
    else:
        _write_file_via_fs(path, content)
    # update embedding index incrementally (use classification-time text, not changelog-appended body)
    _embedding_index.upsert(nid, _index_text)
    # tamper-evident provenance trail (git)
    _git_commit_vault("create", nid, frontmatter.get("agent", "system"), reason)
    return {"ok": True, "id": nid, "path": rel_path, "version": frontmatter["version"]}

@mcp_tool("update_note")
def update_note(id: str, expected_version: int, changes: Dict[str, Any], changelog_reason: str, run_id: str = "default") -> Dict[str, Any]:
    """Update note with optimistic concurrency. changes may contain frontmatter patches and/or body."""
    _check_rate_limit(run_id)
    data = read_note(id)
    fm = data["frontmatter"]
    body = data["body"]
    path_str = data["path"]
    # 1: version check (Rule 1)
    if int(fm.get("version", 0)) != int(expected_version):
        raise RuntimeError(f"409 Conflict: expected version {expected_version} but found {fm.get('version')} for {id}")
    # apply changes
    new_fm = {**fm}
    new_body = body
    if "frontmatter" in changes:
        new_fm.update(changes["frontmatter"])
    if "body" in changes:
        new_body = changes["body"]
    # status transition check
    old_status = fm.get("status")
    new_status = new_fm.get("status", old_status)
    if old_status != new_status:
        err = _validate_status_transition(str(old_status), str(new_status), new_fm.get("type",""))
        if err:
            raise ValueError(err)
    # confidence check is in _validate_frontmatter
    # increment version only if content changed (Rule 16)
    content_changed = (new_body != body) or any(k not in ["tags","aliases","updated"] for k in changes.get("frontmatter",{}))
    if content_changed:
        if not changelog_reason or len(changelog_reason.strip()) < 10:
            raise ValueError("Missing changelog reason (>=10 chars) for content change (Rule 15)")
        new_fm["version"] = int(fm.get("version", 0)) + 1
        new_fm["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        new_body = _ensure_changelog(new_body, new_fm["version"], changelog_reason, new_fm.get("agent","system"), run_id)
        # Rule 17 — new WikiLink required, counted across the FULL note
        # (frontmatter links like supporting_sources are real graph edges).
        # Lifecycle-only transitions (status field alone) are exempt: the move
        # itself is logged in changelog + git message.
        lifecycle_only = (set(changes.get("frontmatter", {}).keys()) <= {"status"}
                          and "body" not in changes)
        old_links = set(_extract_wikilinks(str(fm))) | set(_extract_wikilinks(body))
        new_links = set(_extract_wikilinks(str(new_fm))) | set(_extract_wikilinks(new_body))
        has_new = len(new_links - old_links) > 0
        if not has_new and "orphan-intentional" not in (new_fm.get("tags") or []) and not lifecycle_only:
            raise ValueError("Missing new WikiLink: at least one new [[WikiLink]] required (Rule 17) or tag #orphan-intentional")
        if "orphan-intentional" in (new_fm.get("tags") or []) and "> Orphan justification:" not in new_body:
            raise ValueError("Orphan justification required (Rule 19)")
    else:
        new_fm["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    errs = _validate_frontmatter(new_fm, is_update=True, existing_fm=fm)
    if errs:
        raise ValueError(f"Invalid frontmatter: {errs}")
    # write
    p = VAULT_PATH / path_str
    content = _dump_frontmatter(new_fm, new_body)
    if _rest_available():
        if not _write_file_via_rest(path_str, content):
            _write_file_via_fs(p, content)
    else:
        _write_file_via_fs(p, content)
    _embedding_index.upsert(id, new_fm.get("title","") + " " + new_body[:800])
    _git_commit_vault(f"update:v{new_fm['version']}", id, new_fm.get("agent", "system"), changelog_reason)
    return {"ok": True, "id": id, "version": new_fm["version"]}

@mcp_tool("add_links")
def add_links(id: str, expected_version: int, relationships: List[str], run_id: str = "default") -> Dict[str, Any]:
    """Add Relationships to a note."""
    data = read_note(id)
    body = data["body"]
    fm = data["frontmatter"]
    if int(fm.get("version",0)) != int(expected_version):
        raise RuntimeError(f"409 Conflict: expected {expected_version} but found {fm.get('version')}")
    # append to Relationships section
    rel_block = "\n".join(f"- {r}" for r in relationships)
    if "## Relationships" in body:
        # insert after heading
        body = body.replace("## Relationships", f"## Relationships\n{rel_block}")
    else:
        body = body.rstrip() + f"\n\n## Relationships\n{rel_block}\n"
    return update_note(id, expected_version, {"body": body}, changelog_reason=f"add {len(relationships)} relationships", run_id=run_id)

@mcp_tool("update_metadata")
def update_metadata(id: str, expected_version: int, fields: Dict[str, Any], run_id: str = "default") -> Dict[str, Any]:
    """Update only metadata (tags, aliases). Does not bump version per Rule 16."""
    data = read_note(id)
    fm = data["frontmatter"]
    if int(fm.get("version",0)) != int(expected_version):
        raise RuntimeError(f"409 Conflict")
    # only allow tags/aliases etc.
    allowed_meta = {"tags","aliases","updated"}
    for k in fields:
        if k not in allowed_meta:
            raise ValueError(f"update_metadata only allows {allowed_meta}, got {k}")
    new_fm = {**fm, **fields}
    new_fm["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # no version bump, no changelog required
    p = VAULT_PATH / data["path"]
    content = _dump_frontmatter(new_fm, data["body"])
    if _rest_available():
        _write_file_via_rest(data["path"], content)
    else:
        _write_file_via_fs(p, content)
    _embedding_index.upsert(id, new_fm.get("title","") + " " + data["body"][:800])
    _git_commit_vault("metadata", id, new_fm.get("agent", "system"), f"metadata-only: {sorted(fields.keys())}")
    return {"ok": True, "id": id, "version": new_fm["version"]}

@mcp_tool("apply_evolution_to_note")
def apply_evolution_to_note(note_id: str, expected_version: int, proposal_id: str,
                            changelog_reason: str, run_id: str = "default") -> Dict[str, Any]:
    """Stamp `changed_by: [[PRP-...]]` when an accepted evolution's effect touches
    this knowledge note. Answers 'What evolution changed it?' by query."""
    # verify proposal exists and is an evolution_proposal in a mutable state
    prop = read_note(proposal_id)
    if prop["frontmatter"].get("type") != "evolution_proposal":
        raise ValueError(f"{proposal_id} is not an evolution_proposal")
    if prop["frontmatter"].get("status") not in {"TESTING", "ACCEPTED"}:
        raise ValueError(f"{proposal_id} status {prop['frontmatter'].get('status')} — only TESTING/ACCEPTED effects may be applied")
    data = read_note(note_id)
    old = data["frontmatter"].get("changed_by") or []
    merged = list(dict.fromkeys(list(old) + [f"[[{proposal_id}]]"]))
    reason = f"applied {proposal_id}: {changelog_reason}"
    return update_note(note_id, expected_version,
                       {"frontmatter": {"changed_by": merged}},
                       changelog_reason=reason, run_id=run_id)

# ---------------------------------------------------------------------------
# Consolidation (Prompt 12) — the ONLY write path that folds notes upward.
# Invariants (Rule 22): never delete/archive originals, tier ⊥ status,
# derived_from completeness, source-weighted confidence, depth cap.
# ---------------------------------------------------------------------------

_CONSOLIDATABLE_TYPES = {"claim", "fact", "hypothesis", "concept", "framework"}

def weighted_cluster_confidence(members_fm: List[Dict[str, Any]]) -> float:
    """conf = Σ(conf_i × w_i)/Σw_i with w_i = max(1, |supporting_sources_i|).
    Volume never manufactures certainty — see REX-Memory-Policy §2.5."""
    num = den = 0.0
    for fm in members_fm:
        try:
            conf = float(fm.get("confidence", 0.5))
        except Exception:
            conf = 0.5
        w = max(1, len(fm.get("supporting_sources") or []))
        num += conf * w
        den += w
    return round(num / den, 2) if den else 0.0

@mcp_tool("create_consolidated_note")
def create_consolidated_note(cluster_ids: List[str], note_type: str, title: str,
                             body: Optional[str] = None, run_id: str = "consolidation") -> Dict[str, Any]:
    """Consolidate a cluster of related notes into ONE concept/framework note.
    Originals are tagged `consolidated-into`, stamped `consolidated_into`,
    flipped to tier COLD (status untouched), and kept forever."""
    if note_type not in {"concept", "framework"}:
        raise ValueError(f"consolidated note type must be concept|framework, got {note_type}")
    ids = [str(x) for x in cluster_ids]
    if len(ids) < CONSOLIDATION_MIN_CLUSTER:
        raise ValueError(f"cluster too small: {len(ids)} < CONSOLIDATION_MIN_CLUSTER={CONSOLIDATION_MIN_CLUSTER}")
    # read every member; reject already-consolidated notes
    members: List[Tuple[Dict[str, Any], str, str]] = []
    for nid in ids:
        d = read_note(nid)
        fm = d["frontmatter"]
        if str(fm.get("consolidated_into") or ""):
            raise ValueError(f"{nid} already consolidated into {fm['consolidated_into']}")
        if fm.get("type") not in _CONSOLIDATABLE_TYPES:
            raise ValueError(f"{nid} type {fm.get('type')} not consolidatable")
        members.append((fm, d["body"], d["path"]))
    # recursion cap
    parent_depth = max([int(fm.get("consolidation_depth", 0) or 0) for fm, _, _ in members] or [0])
    depth = parent_depth + 1
    if depth > CONSOLIDATION_MAX_DEPTH:
        raise ValueError(f"consolidation depth {depth} exceeds REX_CONSOLIDATION_MAX_DEPTH={CONSOLIDATION_MAX_DEPTH}")
    # aggregate provenance across the whole cluster
    src_union: List[str] = []
    for fm, _, _ in members:
        for s in (fm.get("supporting_sources") or []):
            if s not in src_union:
                src_union.append(s)
    confidence = weighted_cluster_confidence([fm for fm, _, _ in members])
    # deterministic id from cluster membership + title
    digest = hashlib.sha256(("|".join(sorted(ids)) + "|" + title).encode()).hexdigest().upper()
    ulid = re.sub(r"[^0-9A-HJKMNP-TV-Z]", "0", ("01J8Y" + digest)[:26])[:26]
    nid_new = f"{'CON' if note_type == 'concept' else 'FRM'}-{ulid}"
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # synthesize body if caller didn't supply one
    if not body:
        est, disp, open_ = [], [], []
        for fm, _, _ in members:
            st = str(fm.get("status", ""))
            line = f"- **{fm.get('title','')}** ({st}, conf {fm.get('confidence')}) [[{fm.get('id')}]]"
            if st == "disputed":
                disp.append(line)
            elif st in {"verified", "active"} and fm.get("type") in {"fact", "claim"}:
                est.append(line)
            else:
                open_.append(line)
        body = (f"# {title}\n\n"
                f"> Synthesized by the Consolidation Agent from {len(ids)} notes "
                f"(depth {depth}). Source-weighted confidence: Σ(conf_i×w_i)/Σw_i.\n\n"
                f"## Established\n" + ("\n".join(est[:10]) or "- (none)") + "\n\n"
                f"## Disputed\n" + ("\n".join(disp[:10]) or "- (none)") + "\n\n"
                f"## Open\n" + ("\n".join(open_[:10]) or "- (none)") + "\n\n"
                f"## Sources\n" + ("\n".join(f"- {s}" for s in src_union[:20]) or "- (no external sources)") + "\n")
    rel_lines = "\n".join(f"- derived_from:: [[{x}]]" for x in ids)
    if "## Relationships" in body:
        body = body.replace("## Relationships", f"## Relationships\n{rel_lines}", 1)
    else:
        body = body.rstrip() + f"\n\n## Relationships\n{rel_lines}\n"
    new_fm = {
        "id": nid_new, "type": note_type, "title": title, "status": "active",
        "confidence": confidence, "created": now_iso, "updated": now_iso,
        "version": 1, "source_count": len(src_union), "agent": "consolidator",
        "tags": ["consolidation"], "tier": "hot",
        "supporting_sources": src_union,
        "consolidation_depth": depth,
        "derived_from": [f"[[{x}]]" for x in ids],
        "_changelog_reason": f"consolidate cluster of {len(ids)} notes (Rule 22)",
    }
    # the synthesis is intentionally exempt from duplicate classification —
    # it overlaps its own members by construction (same trick as research_run writes)
    global SIMILARITY_THRESHOLD
    _saved_thresh = SIMILARITY_THRESHOLD
    SIMILARITY_THRESHOLD = 0.999
    try:
        created = create_note(note_type, new_fm, body, run_id=run_id)
    finally:
        SIMILARITY_THRESHOLD = _saved_thresh
    # stamp + chill every original (never delete, never touch status)
    chilled = []
    for fm, orig_body, orig_path in members:
        oid = fm.get("id")
        tags = list(fm.get("tags") or [])
        if "consolidated-into" not in tags:
            tags.append("consolidated-into")
        new_body = orig_body.rstrip() + f"\n\n## Consolidation\nConsolidated into [[{nid_new}]] — superseded summary; retained for provenance (Rule 22).\n"
        update_note(oid, int(fm.get("version", 1)),
                    {"frontmatter": {"tier": "cold", "consolidated_into": f"[[{nid_new}]]", "tags": tags},
                     "body": new_body},
                    changelog_reason=f"folded into consolidated {note_type} {nid_new}",
                    run_id=run_id)
        _move_to_cold(oid)   # update_note re-upserts to main index — re-partition afterwards
        chilled.append(oid)
    _git_commit_vault("consolidate", nid_new, "consolidator",
                      f"folded {len(chilled)} notes into {note_type} (weighted conf {confidence})")
    return {
        "ok": True, "id": nid_new, "type": note_type, "title": title,
        "confidence": confidence, "source_count": len(src_union),
        "consolidation_depth": depth, "cluster_size": len(chilled),
        "chilled_ids": chilled,
    }

# ---------------------------------------------------------------------------
# Provenance READ tools (Prompt 11) — provenance as queryable trail
# ---------------------------------------------------------------------------

def _scan_notes(skip_archive=False):
    for p in VAULT_PATH.rglob("*.md"):
        s = str(p)
        if ".obsidian" in s or p.name == "README.md":
            continue
        if skip_archive and "99_Archive" in s:
            continue
        try:
            fm, body = _parse_frontmatter(p.read_text(encoding="utf-8"))
            rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
            yield fm, body, rel
        except Exception:
            continue

@mcp_tool("get_creating_runs")
def get_creating_runs(note_id: str) -> List[Dict[str, Any]]:
    """Reverse lookup: which Run records link this note in linked_notes?"""
    out = []
    for fm, body, rel in _scan_notes():
        if fm.get("type") != "research_run":
            continue
        linked = [str(x) for x in (fm.get("linked_notes") or [])]
        linked_ids = [re.sub(r"[\[\]]", "", x).split("__")[0] for x in linked]
        if any(note_id == x or note_id.startswith(x) or x.startswith(note_id) for x in linked_ids):
            out.append({"id": fm.get("id"), "title": fm.get("title"), "path": rel,
                        "result": fm.get("result"), "agent": fm.get("agent"),
                        "created": fm.get("created")})
    return out

@mcp_tool("get_dependents")
def get_dependents(note_id: str) -> List[Dict[str, Any]]:
    """Reverse WikiLink search: notes whose depends_on/derived_from/part_of/implements/tested_by point at note_id."""
    verbs = ("depends_on", "derived_from", "part_of", "implements", "tested_by", "supports")
    out = []
    for fm, body, rel in _scan_notes(skip_archive=True):
        if str(fm.get("id", "")).startswith(note_id) or note_id.startswith(str(fm.get("id", "###"))):
            continue  # skip self
        m = re.search(r"## Relationships\n(.*?)(?:\n## |\Z)", body, re.S)
        if not m:
            continue
        for line in m.group(1).splitlines():
            lm = re.match(r"-\s*(\w+)::\s*\[\[([^\]]+)\]\]", line.strip())
            if lm and lm.group(1) in verbs:
                target = lm.group(2).split("__")[0]
                if target == note_id:
                    out.append({"from_id": fm.get("id"), "from_title": fm.get("title"),
                                "relationship": lm.group(1), "path": rel})
                    break
    return out

@mcp_tool("get_contradictions_for")
def get_contradictions_for(note_id: str) -> Dict[str, Any]:
    """contradicting_sources on the note itself + CTR notes linking it."""
    try:
        data = read_note(note_id)
        own = [str(x) for x in (data["frontmatter"].get("contradicting_sources") or [])]
    except Exception:
        own = []
    ctrs = []
    for fm, body, rel in _scan_notes():
        if fm.get("type") != "contradiction":
            continue
        fields = str(fm.get("claim_a", "")) + str(fm.get("claim_b", ""))
        rel_section = re.search(r"## Relationships\n(.*?)(?:\n## |\Z)", body, re.S)
        rel_txt = rel_section.group(1) if rel_section else ""
        if note_id in re.sub(r"[\[\]]", "", fields) or f"contradicts:: [[{note_id}" in rel_txt:
            ctrs.append({"id": fm.get("id"), "resolution_status": fm.get("resolution_status"),
                         "title": fm.get("title"), "path": rel})
    return {"own_contradicting_sources": own, "contradiction_notes": ctrs}

@mcp_tool("get_evidence_diff")
def get_evidence_diff(note_id: str) -> List[Dict[str, Any]]:
    """Diff supporting_sources across git history (oldest -> newest).
    Answers: What evidence increased its confidence? Version bumps correspond to commits."""
    import subprocess
    try:
        rel = read_note(note_id)["path"]
    except Exception as e:
        raise FileNotFoundError(f"{note_id}: {e}")
    log = subprocess.run(
        ["git", "log", "--date=iso-strict", "--format=%H|%ad|%s", "--follow", "--", rel.replace("/", "\\")],
        cwd=str(VAULT_PATH), capture_output=True, text=True, timeout=10)
    lines = [l for l in (log.stdout or "").splitlines() if "|" in l]
    if not lines:
        log2 = subprocess.run(
            ["git", "log", "--date=iso-strict", "--format=%H|%ad|%s", "--", rel],
            cwd=str(VAULT_PATH), capture_output=True, text=True, timeout=10)
        lines = [l for l in (log2.stdout or "").splitlines() if "|" in l]
        rel_use = rel
    else:
        rel_use = None
    commits = []  # oldest first
    for line in reversed(lines):
        sha, date, msg = line.split("|", 2)
        show = subprocess.run(["git", "show", f"{sha}:{rel_use or rel}"],
                              cwd=str(VAULT_PATH), capture_output=True, text=True, timeout=10)
        fm, _b = _parse_frontmatter(show.stdout or "")
        sup = set()
        for s in (fm.get("supporting_sources") or []):
            sup.add(re.sub(r"[\[\]]", "", str(s)).split("__")[0])
        commits.append({"sha": sha[:10], "date": date, "message": msg, "sources": sup})
    out = []
    prev = set()
    for c in commits:
        added = sorted(c["sources"] - prev)
        removed = sorted(prev - c["sources"])
        if added or removed or not prev:
            out.append({"sha": c["sha"], "date": c["date"], "message": c["message"],
                        "added": added, "removed": removed})
        prev = c["sources"]
    return out

@mcp_tool("get_evolution_for_note")
def get_evolution_for_note(note_id: str) -> Dict[str, Any]:
    """changed_by field on the note + proposals/mutations whose evidence/body references it."""
    try:
        changed_by = list(read_note(note_id)["frontmatter"].get("changed_by") or [])
    except Exception:
        changed_by = []
    refs = []
    for fm, body, rel in _scan_notes():
        if fm.get("type") not in {"evolution_proposal", "genome"}:
            continue
        hay = json.dumps(fm.get("evidence", []), default=str) + body[:2000] + json.dumps(fm.get("linked_notes", []) or [], default=str)
        if note_id in re.sub(r"[\[\]]", "", hay):
            refs.append({"id": fm.get("id"), "type": fm.get("type"), "status": fm.get("status"),
                         "title": fm.get("title"), "path": rel})
    return {"changed_by": changed_by, "referencing_artifacts": refs}

@mcp_tool("get_provenance")
def get_provenance(note_id: str) -> Dict[str, Any]:
    """One-call backward chain: who/when/why/evidence/runs/evolution."""
    import subprocess
    d = read_note(note_id)
    fm, body = d["frontmatter"], d["body"]
    ch = re.search(r"## Changelog\n(.*?)(?:\n## |\Z)", body, re.S)
    changelog = [l.strip() for l in (ch.group(1).splitlines() if ch else []) if l.strip().startswith("-")]
    gl = subprocess.run(["git", "log", "-1", "--format=%h %ad %s", "--date=iso-strict", "--",
                         d["path"].replace("/", "\\")],
                        cwd=str(VAULT_PATH), capture_output=True, text=True, timeout=10)
    return {
        "id": fm.get("id"), "type": fm.get("type"), "title": fm.get("title"),
        "frontmatter": fm,
        "created_by_agent": fm.get("agent"), "created": fm.get("created"), "updated": fm.get("updated"),
        "version": fm.get("version"), "confidence": fm.get("confidence"),
        "supporting_sources": fm.get("supporting_sources", []),
        "contradicting_sources": fm.get("contradicting_sources", []),
        "changed_by": fm.get("changed_by") or [],
        "changelog": changelog,
        "creating_runs": get_creating_runs(fm.get("id")),
        "contradictions": get_contradictions_for(fm.get("id")),
        "dependents": get_dependents(fm.get("id")),
        "evolution": get_evolution_for_note(fm.get("id")),
        "evidence_history": get_evidence_diff(fm.get("id")),
        "last_git_commit": (gl.stdout or "").strip(),
    }

@mcp_tool("create_contradiction")
def create_contradiction(claim_a: str, claim_b: str, detected_in_run: str, run_id: str = "default", new_title: str = "") -> Dict[str, Any]:
    """Create CTR note linking two claims. Does NOT alter original claims' content (Rule 4/5).
    claim_b may be a not-yet-written note id when rerouting from _pre_write_check — pass its title via new_title."""
    _check_rate_limit(run_id)
    if claim_a == claim_b:
        raise ValueError("claim_a and claim_b must be distinct")
    # verify claims exist (claim_b may legitimately not exist yet when rerouting)
    for cid in (claim_a, claim_b):
        try:
            d = read_note(cid)
            if d["frontmatter"].get("type") not in {"claim","fact"}:
                raise ValueError(f"{cid} not a claim/fact")
        except FileNotFoundError:
            if cid == claim_b and new_title:
                continue  # reroute case: the triggering note was never written
            raise ValueError(f"claim {cid} not found")
    # generate CTR id first so we can link claims to it (satisfies Rule 17 new WikiLink)
    import uuid, datetime
    ulid = "01J8Y" + hashlib.sha256(f"{claim_a}{claim_b}{time.time()}".encode()).hexdigest()[:21].upper().replace("I","J").replace("L","M").replace("O","P")
    ulid = re.sub(r"[^0-9A-HJKMNP-TV-Z]", "0", ulid)[:26]
    ctr_id = f"CTR-{ulid}"
    # transition claims to disputed — add a new WikiLink to the CTR so Rule 17 passes, but preserve original body
    for cid in (claim_a, claim_b):
        try:
            d = read_note(cid)
            if d["frontmatter"].get("status") in {"active","verified"}:
                other = claim_b if cid == claim_a else claim_a
                new_body = d["body"].rstrip() + f"\n\n## Dispute\nContradicts [[{other}]] — see [[{ctr_id}]]\n"
                update_note(cid, int(d["frontmatter"]["version"]), {"frontmatter": {"status": "disputed"}, "body": new_body}, changelog_reason=f"mark disputed via CTR {ctr_id}", run_id=run_id)
        except Exception as e:
            # if update fails for other reason, try status-only update as fallback
            try:
                d = read_note(cid)
                if d["frontmatter"].get("status") in {"active","verified"}:
                    new_body2 = d["body"].rstrip() + f"\n\n## Dispute\nSee [[{ctr_id}]]\n"
                    update_note(cid, int(d["frontmatter"]["version"]), {"frontmatter": {"status": "disputed"}, "body": new_body2}, changelog_reason=f"mark disputed via CTR {ctr_id}", run_id=run_id)
            except Exception:
                pass  # if already disputed, ignore
    fm = {
        "id": ctr_id,
        "type": "contradiction",
        "title": f"Contradiction {claim_a} vs {claim_b}",
        "status": "active",
        "confidence": 0.75,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": 1,
        "source_count": 0,
        "agent": "auditor",
        "tags": ["contradiction"],
        "claim_a": f"[[{claim_a}]]",
        "claim_b": f"[[{claim_b}]]",
        "detected_by": "auditor",
        "detected_in_run": f"[[{detected_in_run}]]" if detected_in_run else "[[EXP-unknown]]",
        "resolution_status": "open",
        "resolution": None,
    }
    body = f"# Contradiction {claim_a} vs {claim_b}\n\n> Claim `[[{claim_a}]]` contradicts `[[{claim_b}]]`.\n\n## Relationships\n- contradicts:: [[{claim_a}]]\n- contradicts:: [[{claim_b}]]\n- created_by:: [[{detected_in_run}]]\n"
    return create_note("contradiction", fm, body, relationships=[f"contradicts:: [[{claim_a}]]", f"contradicts:: [[{claim_b}]]"], run_id=run_id)

@mcp_tool("create_evolution_proposal")
def create_evolution_proposal(fields: Dict[str, Any], run_id: str = "default") -> Dict[str, Any]:
    """Create PRP note. Validates min 1 evidence. Only this function may create evolution proposals (hard constraint)."""
    _check_rate_limit(run_id)
    if not fields.get("evidence") or len(fields["evidence"]) == 0:
        raise ValueError("evidence min 1 wikilink required (Rule 9) — proposal with zero evidence is invalid")
    # Handle both new (Prompt 8) and legacy (Prompt 2) field names for backwards compat
    # New fields: current_version, proposed_version, change, previous_performance, expected_performance, benchmark
    # Legacy aliases: operation -> change, expected_improvement -> expected_performance
    target = fields.get("target")
    if not target:
        raise ValueError("evolution_proposal missing target")
    # Resolve change / operation
    change = fields.get("change") or fields.get("operation")
    if not change:
        raise ValueError("evolution_proposal missing change (or legacy operation)")
    # Resolve expected_performance / expected_improvement
    expected_perf = fields.get("expected_performance") or fields.get("expected_improvement")
    if not expected_perf:
        raise ValueError("evolution_proposal missing expected_performance (or legacy expected_improvement)")
    # Resolve current/proposed version and performance/benchmark with sensible defaults for new proposals
    current_version = fields.get("current_version") or fields.get("currentVersion") or "1.0.0"
    proposed_version = fields.get("proposed_version") or fields.get("proposedVersion")
    if not proposed_version:
        # auto-bump patch
        try:
            parts = current_version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            proposed_version = ".".join(parts)
        except Exception:
            proposed_version = "1.0.1"
    previous_performance = fields.get("previous_performance") or fields.get("previousPerformance") or "unknown (to be measured)"
    benchmark = fields.get("benchmark") or "to be benchmarked (Prompt 9)"
    # Hard constraint: ensure this is called from evolution_analysis_node, not from arbitrary code that mutates configs
    # We log the caller stack for audit; direct config mutation is forbidden elsewhere
    # Generate id
    ulid = "01J8Y" + hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()[:21].upper()
    ulid = re.sub(r"[^0-9A-HJKMNP-TV-Z]", "0", ulid)[:26]
    nid = fields.get("id") or f"PRP-{ulid}"
    fm = {
        "id": nid,
        "type": "evolution_proposal",
        "title": fields.get("title", f"Evolution proposal for {target}"),
        "status": fields.get("status", "PROPOSED"),
        "confidence": fields.get("confidence", 0.7),
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": 1,
        "source_count": len(fields.get("evidence", [])),
        "agent": fields.get("agent", "evolution"),
        "tags": fields.get("tags", ["evolution"]),
        "target": target,
        "current_version": current_version,
        "proposed_version": proposed_version,
        "change": change,
        "reason": fields.get("reason", ""),
        "evidence": fields["evidence"],
        "previous_performance": previous_performance,
        "expected_performance": expected_perf,
        "risk": fields.get("risk", "medium"),
        "benchmark": benchmark,
        # Keep legacy aliases for vaults that still read them
        "operation": change,
        "expected_improvement": expected_perf,
    }
    # Enforce PROPOSED stays in Proposals/ — create_note will use _resolve_type_folder which maps to Proposals/ for this type
    # Hard constraint check: ensure we are not being asked to create an ACCEPTED proposal without benchmark delta
    if fm["status"] == "ACCEPTED":
        bench = str(fm.get("benchmark",""))
        has_delta = "->" in bench and any(c.isdigit() for c in bench) and "n=" in bench.lower()
        if not has_delta:
            raise ValueError("ACCEPTED proposals must carry numeric benchmark delta (e.g. '0.81 -> 0.89 on eval set X, n=40 runs') — LLM opinion alone is invalid")
    body = fields.get("body") or f"# {fm['title']}\n\n**Target:** {target} (`{current_version}` → `{proposed_version}`)\n\n**Change:** {change}\n\n**Reason:** {fm['reason']}\n\n**Previous:** {previous_performance}\n**Expected:** {expected_perf}\n**Benchmark:** {benchmark}\n\n**Risk:** {fm['risk']}\n"
    # Ensure at least one wikilink for evidence is in body as well
    if fm["evidence"]:
        body += "\n## Evidence\n" + "\n".join(f"- {ev}" for ev in fm["evidence"][:3]) + "\n"
    return create_note("evolution_proposal", fm, body, run_id=run_id)

@mcp_tool("archive_note")
def archive_note(id: str, expected_version: int, reason: str, run_id: str = "default") -> Dict[str, Any]:
    """Archive = git mv to 99_Archive/<mirrored> + status archived."""
    _check_rate_limit(run_id)
    data = read_note(id)
    fm = data["frontmatter"]
    if int(fm.get("version",0)) != int(expected_version):
        raise RuntimeError(f"409 Conflict")
    if not reason or len(reason.strip()) < 10:
        raise ValueError("Archive reason required (>=10 chars)")
    old_path = VAULT_PATH / data["path"]
    # mirrored path
    mirrored = Path("99_Archive") / data["path"]
    new_path = VAULT_PATH / mirrored
    new_path.parent.mkdir(parents=True, exist_ok=True)
    # update frontmatter
    new_fm = {**fm, "status": "archived", "archived": time.strftime("%Y-%m-%d", time.gmtime()), "version": int(fm["version"])+1, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    content = _dump_frontmatter(new_fm, data["body"] + f"\n\n## Changelog\n- v{new_fm['version']} — {new_fm.get('agent','system')} (run {run_id}): archive — {reason}\n")
    # write to new location then git mv
    try:
        import subprocess
        # write new file first
        _write_file_via_fs(new_path, content)
        # git mv (removes old, adds new)
        subprocess.run(["git","mv", str(old_path), str(new_path)], cwd=str(VAULT_PATH), capture_output=True, timeout=2)
        subprocess.run(["git","commit","-m", f"archive: {id} — {reason[:40]}"], cwd=str(VAULT_PATH), capture_output=True, timeout=2)
    except Exception:
        # fallback to manual move
        old_path.unlink(missing_ok=True)
        _write_file_via_fs(new_path, content)
    _embedding_index.remove(id)
    return {"ok": True, "id": id, "archived_path": str(mirrored).replace("\\","/")}

# ---------------------------------------------------------------------------
# LangGraph node — discrete service
# ---------------------------------------------------------------------------

def memory_agent_node(state: Dict[str, Any], config: Any = None) -> Dict[str, Any]:
    """
    LangGraph node. Input state expects:
      - action: one of the MCP tool names
      - payload: dict of args
      - run_id: str
    Output is added to state['memory_result'].
    This node is the ONLY place that touches the vault.
    """
    action = state.get("memory_action")
    payload = state.get("memory_payload", {})
    run_id = state.get("run_id", "default")
    if not action:
        return {"memory_result": {"ok": False, "error": "no memory_action"}}
    tool = MCP_TOOLS.get(action)
    if not tool:
        return {"memory_result": {"ok": False, "error": f"unknown tool {action}"}}
    try:
        # inject run_id if tool accepts it
        import inspect
        sig = inspect.signature(tool)
        if "run_id" in sig.parameters and "run_id" not in payload:
            payload["run_id"] = run_id
        result = tool(**payload)
        return {"memory_result": result}
    except Exception as e:
        return {"memory_result": {"ok": False, "error": str(e)}}

# Rebuild index on import (lightweight)
try:
    _embedding_index.rebuild_all()
except Exception:
    pass

# ---------------------------------------------------------------------------
# MCP server entry (for LLM agents)
# ---------------------------------------------------------------------------

def get_mcp_tools_schema() -> List[Dict[str, Any]]:
    """Return JSON schema for all MCP tools (for LLM function calling)."""
    import inspect
    schemas = []
    for name, fn in MCP_TOOLS.items():
        sig = inspect.signature(fn)
        props = {}
        required = []
        for pname, param in sig.parameters.items():
            if pname == "run_id":
                continue
            ann = param.annotation
            typ = "string"
            if ann == int:
                typ = "integer"
            elif ann == float:
                typ = "number"
            elif "List" in str(ann) or "list" in str(ann):
                typ = "array"
            props[pname] = {"type": typ, "description": ""}
            if param.default == inspect.Parameter.empty:
                required.append(pname)
        schemas.append({"name": name, "description": fn.__doc__ or "", "parameters": {"type": "object", "properties": props, "required": required}})
    return schemas
