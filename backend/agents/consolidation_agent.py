"""Consolidation Agent (Prompt 12) — folds raw granular memory upward into
fewer, higher-level, higher-confidence notes. Never deletes the originals.

Runs periodically: after every REX_CONSOLIDATION_EVERY_N_RUNS research runs
(triggered from graph.memory_update_node) or nightly via:
    python -m backend.agents.consolidation_agent

Hard constraint (mirrors Prompt 8): this agent may only WRITE through
memory_agent.create_consolidated_note / demote_to_cold / promote_to_warm.
No direct vault mutation, no production config changes.
"""
import os
import sys
import re
from typing import List, Dict, Any, Optional, Tuple

from . import memory_agent as ma


# ---------------------------------------------------------------------------
# Clustering — embedding similarity + shared tags, never folder alone
# ---------------------------------------------------------------------------

_SYSTEM_TAGS = {"test", "consolidated-into", "orphan-intentional", "consolidation",
                "dashboard", "dataview", "navigation", "policy", "memory", "tiers",
                "evolution", "contradiction"}

def _meaningful_tags(fm: Dict[str, Any]) -> set:
    tags = fm.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    return {str(t).strip().lower() for t in tags if t and str(t).strip().lower() not in _SYSTEM_TAGS}

def _cluster_candidates(candidates: List[Dict[str, Any]],
                        sim_threshold: float = ma.CLUSTER_SIM_THRESHOLD) -> List[List[Dict[str, Any]]]:
    """Union-find over edges: cosine >= sim_threshold OR shared meaningful tag."""
    n = len(candidates)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    vecs = {}
    for i, c in enumerate(candidates):
        v = ma._embedding_index._vectors.get(c["id"])
        if v is not None:
            vecs[i] = v

    for i in range(n):
        for j in range(i + 1, n):
            linked = False
            vi, vj = vecs.get(i), vecs.get(j)
            if vi and vj:
                dot = sum(a * b for a, b in zip(vi, vj))
                ni = sum(x * x for x in vi) ** 0.5 or 1.0
                nj = sum(x * x for x in vj) ** 0.5 or 1.0
                if dot / (ni * nj) >= sim_threshold:
                    linked = True
            if not linked:
                shared = candidates[i]["tags"] & candidates[j]["tags"]
                # require a real shared topic tag (not just one note's generic tag)
                if shared:
                    linked = True
            if linked:
                union(i, j)

    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [[candidates[i] for i in idxs] for idxs in groups.values()]


# ---------------------------------------------------------------------------
# Synthesis body — deterministic template (LLM optional garnish, never required)
# ---------------------------------------------------------------------------

def _synthesize_title(cluster: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Pick dominant topic tag + highest-confidence member title."""
    tag_counts: Dict[str, int] = {}
    for c in cluster:
        for t in c["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top_tag = max(tag_counts.items(), key=lambda kv: kv[1])[0] if tag_counts else "misc"
    best = max(cluster, key=lambda c: float(c["fm"].get("confidence", 0)))
    depth_word = "Framework" if any(int(c["fm"].get("consolidation_depth", 0) or 0) > 0 for c in cluster) else "Concept"
    return f"{depth_word}: {best['fm'].get('title', '')[:70]} ({top_tag})", top_tag

def _llm_synthesis_intro(topic_tag: str, titles: List[str]) -> Optional[str]:
    """Optional 2-sentence LLM intro; returns None on any failure — template is canonical."""
    try:
        import requests
        model = os.getenv("REPORT_MODEL", "qwen2.5:3b")
        prompt = ("Summarize in exactly two sentences what these related research notes "
                  f"(topic: {topic_tag}) jointly establish:\n- " + "\n- ".join(titles[:8]))
        r = requests.post(f"{ma.OLLAMA_HOST}/api/generate",
                          json={"model": model, "prompt": prompt, "stream": False},
                          timeout=20)
        if r.status_code == 200:
            text = (r.json().get("response") or "").strip()
            if 20 < len(text) < 600 and "as an ai" not in text.lower():
                return text
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# The pass
# ---------------------------------------------------------------------------

def run_consolidation_pass(run_id: str = "consolidation", dry_run: bool = False) -> Dict[str, Any]:
    """One full pass: decay -> gather eligible notes -> cluster -> consolidate."""
    report: Dict[str, Any] = {"clusters_found": 0, "consolidations": [], "skipped": [],
                              "decay": None, "index_sizes": {}}
    # 1. decay first so stale low-confidence notes leave the candidate pool
    report["decay"] = ma.decay_pass(dry_run=not dry_run)

    # 2. gather eligible candidates (HOT/WARM raw granular + sub-cap synthesized notes)
    candidates: List[Dict[str, Any]] = []
    for fm, body, rel in ma._scan_notes(skip_archive=True):
        nid = str(fm.get("id", ""))
        if not nid or fm.get("type") not in ma._CONSOLIDATABLE_TYPES:
            continue
        if str(fm.get("consolidated_into") or ""):
            continue
        try:
            depth = int(fm.get("consolidation_depth", 0) or 0)
        except Exception:
            depth = 0
        if depth >= ma.CONSOLIDATION_MAX_DEPTH:
            continue
        if ma._effective_tier(fm) == "cold":
            continue
        candidates.append({"id": nid, "fm": fm, "body": body,
                           "tags": _meaningful_tags(fm)})
    if not candidates:
        return report

    # 3. cluster
    clusters = [c for c in _cluster_candidates(candidates) if len(c) >= ma.CONSOLIDATION_MIN_CLUSTER]
    report["clusters_found"] = len(clusters)
    report["index_sizes"] = {"main": len(ma._embedding_index._vectors),
                             "cold": len(ma._get_cold_index()._vectors) if ma._embedding_index_cold else 0}
    if not clusters or dry_run:
        return report

    # 4. consolidate each qualifying cluster (rate-limit headroom for batch writes)
    saved_limit = ma.MAX_WRITES_PER_RUN
    ma.MAX_WRITES_PER_RUN = max(saved_limit, 500)
    try:
        for cluster in clusters:
            ids = [c["id"] for c in cluster]
            title, top_tag = _synthesize_title(cluster)
            intro = _llm_synthesis_intro(top_tag, [c["fm"].get("title", "") for c in cluster])
            body = None
            if intro:
                est_lines = "\n".join(f"- [[{c['id']}]] {c['fm'].get('title','')}" for c in cluster[:10])
                body = (f"# {title}\n\n{intro}\n\n## Members\n{est_lines}\n")
            try:
                note_type = "framework" if any(
                    int(c["fm"].get("consolidation_depth", 0) or 0) > 0 for c in cluster) else "concept"
                res = ma.create_consolidated_note(ids, note_type, title, body=body, run_id=run_id)
                report["consolidations"].append(res)
            except Exception as e:
                report["skipped"].append({"ids": ids[:3], "error": str(e)})
    finally:
        ma.MAX_WRITES_PER_RUN = saved_limit

    report["index_sizes"] = {"main": len(ma._embedding_index._vectors),
                             "cold": len(ma._get_cold_index()._vectors) if ma._embedding_index_cold else 0}
    return report


def nightly() -> Dict[str, Any]:
    """Nightly entry point."""
    print("[ConsolidationAgent] starting nightly pass...")
    rep = run_consolidation_pass(run_id="consolidation-nightly", dry_run=False)
    print(f"[ConsolidationAgent] clusters={rep['clusters_found']} "
          f"consolidations={len(rep['consolidations'])} skipped={len(rep['skipped'])} "
          f"decay={rep['decay']} index={rep['index_sizes']}")
    return rep


if __name__ == "__main__":
    nightly()
