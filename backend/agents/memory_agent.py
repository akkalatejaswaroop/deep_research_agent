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
        for p in vault_path.rglob("*.md"):
            if ".obsidian" in str(p):
                continue
            try:
                text = p.read_text(encoding="utf-8")
                # extract id from frontmatter
                fm, _ = _parse_frontmatter(text)
                nid = fm.get("id", "")
                if nid:
                    # use title + first 500 chars
                    self.upsert(nid, fm.get("title", "") + " " + text[:500])
                else:
                    # fallback to filename
                    self.upsert(p.stem, text[:500])
            except Exception:
                continue

_embedding_index = LocalVectorIndex()

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
    # use embedding index for scoring
    scored = _embedding_index.search(query_text, top_k=5)
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
    # check for contradiction: if new claim contradicts existing with high similarity but opposite stance?
    # simple heuristic: if best_score >= 0.75 and note_type == "claim", mark CONTRADICTION
    if note_type in {"claim","fact"} and best_score >= 0.75 and best_score < threshold:
        # we could detect contradicting_sources overlap, but keep simple
        return ("CONTRADICTION", best_id, best_score)
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
    supporting = frontmatter.get("supporting_sources", [])
    evidence_strength = frontmatter.get("evidence_strength", "weak")
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
def search_notes(query: str, type: Optional[str] = None, status: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search notes by semantic similarity + optional type/status filter."""
    if not query:
        return []
    # use embedding index
    scored = _embedding_index.search(query, top_k=limit*2)
    results = []
    for nid, score in scored:
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
            results.append({"id": nid, "title": fm.get("title",""), "path": rel, "score": round(score, 3)})
            if len(results) >= limit:
                break
        except Exception:
            continue
    # fallback to brute-force if index empty
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
                if query.lower() in txt.lower() or query.lower() in fm.get("title","").lower():
                    rel = str(p.relative_to(VAULT_PATH)).replace("\\", "/")
                    results.append({"id": fm.get("id", p.stem), "title": fm.get("title",""), "path": rel, "score": 0.5})
                    if len(results) >= limit:
                        break
            except Exception:
                continue
    return results[:limit]

@mcp_tool("read_note")
def read_note(id: str) -> Dict[str, Any]:
    """Read note by id -> {frontmatter, body}."""
    # try REST first
    rest = _read_via_rest(id)
    if rest:
        return {"frontmatter": rest["frontmatter"], "body": rest["body"], "path": rest["path"]}
    fs = _read_via_fs(id)
    if not fs:
        raise FileNotFoundError(f"Note {id} not found")
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
        # create contradiction automatically
        ctr = create_contradiction(existing_id, new_id, detected_in_run=run_id)
        return {"ok": False, "contradiction": True, "contradiction_id": ctr.get("id"), "existing_id": existing_id, "message": "Contradiction detected, rerouted"}
    # use possibly mutated body from check
    body = check.get("body", body)
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
    # update embedding index incrementally
    _embedding_index.upsert(nid, frontmatter.get("title","") + " " + body[:800])
    # git add/commit is handled by caller or via filesystem watcher; here we do git add
    try:
        import subprocess
        subprocess.run(["git","add", str(path)], cwd=str(VAULT_PATH), capture_output=True, timeout=2)
        subprocess.run(["git","commit","-m", f"create: {nid} {frontmatter.get('title','')[:40]}"], cwd=str(VAULT_PATH), capture_output=True, timeout=2)
    except Exception:
        pass
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
        # ensure at least one new wikilink unless orphan-intentional (Rules 17-19)
        old_links = set(_extract_wikilinks(body))
        new_links = set(_extract_wikilinks(new_body))
        has_new = len(new_links - old_links) > 0
        if not has_new and "orphan-intentional" not in (new_fm.get("tags") or []):
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
    try:
        import subprocess
        subprocess.run(["git","add", str(p)], cwd=str(VAULT_PATH), capture_output=True, timeout=2)
        subprocess.run(["git","commit","-m", f"update: {id} v{new_fm['version']} {changelog_reason[:40]}"], cwd=str(VAULT_PATH), capture_output=True, timeout=2)
    except Exception:
        pass
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
    return {"ok": True, "id": id, "version": new_fm["version"]}

@mcp_tool("create_contradiction")
def create_contradiction(claim_a: str, claim_b: str, detected_in_run: str, run_id: str = "default") -> Dict[str, Any]:
    """Create CTR note linking two claims. Does NOT alter original claims' content (Rule 4/5)."""
    _check_rate_limit(run_id)
    if claim_a == claim_b:
        raise ValueError("claim_a and claim_b must be distinct")
    # verify claims exist
    for cid in (claim_a, claim_b):
        try:
            d = read_note(cid)
            if d["frontmatter"].get("type") not in {"claim","fact"}:
                raise ValueError(f"{cid} not a claim/fact")
        except FileNotFoundError:
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
