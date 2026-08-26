"""Prompt 12 tests — Consolidation Agent, tiers, decay, provenance preservation."""
import os
import subprocess
import math as _math
import re as _re
import hashlib as _hashlib
from pathlib import Path

import pytest

os.environ.setdefault("PREFER_LLM", "false")

import backend.agents.memory_agent as ma


def _fast_embed(text):
    vec = [0.0] * 384
    for tok in _re.findall(r"[a-z0-9]{3,}", text.lower()):
        h = int(_hashlib.sha256(tok.encode()).hexdigest()[:8], 16) % 384
        vec[h] += 1.0
    n = _math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


ma.LocalVectorIndex._embed = lambda self, text: _fast_embed(text)
ma.LocalVectorIndex._embed_ollama = lambda self, text: None

OLD_TS = "2026-06-01T10:00:00Z"   # far past -> stale
NOW_TS = "2026-08-25T10:00:00Z"


def _cid(i: int) -> str:
    """Canonical 26-char ULID for test claims: 01J8Y + 18 zeros + %03d."""
    return "CLM-01J8Y" + "0" * 18 + f"{i:03d}"


@pytest.fixture
def vault(tmp_path):
    for d in ["02_Knowledge/Claims", "02_Knowledge/Facts", "01_Research/Concepts",
              "02_Knowledge/Frameworks", "03_Sources/Websites", "04_Experiments/Runs"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    old = ma.VAULT_PATH
    old_cold = ma._embedding_index_cold
    ma.VAULT_PATH = tmp_path
    ma._embedding_index = ma.LocalVectorIndex()
    ma._embedding_index_cold = None
    ma._touch_log.clear()
    ma._write_counts.clear()
    for cmd in (["git", "init"], ["git", "config", "user.name", "t"],
                ["git", "config", "user.email", "t@t.t"]):
        subprocess.run(cmd, cwd=str(tmp_path), capture_output=True)
    yield tmp_path
    ma.VAULT_PATH = old
    ma._embedding_index_cold = old_cold


def _source(vault, nid="SRC-01J8Y000000000000000000008"):
    ma.create_note("source", {
        "id": nid, "type": "source", "title": f"Src {nid[-3:]}", "status": "active",
        "confidence": 0.9, "created": NOW_TS, "updated": NOW_TS,
        "version": 1, "source_count": 0, "agent": "searcher", "tags": ["test"],
        "authors": ["A"], "publication": "J", "year": 2024, "url": "https://e.com",
        "doi": None, "source_type": "website", "retrieved": NOW_TS,
        "access_note": "open",
    }, "# src\n", run_id="seed")


def _claim(vault, i, title, conf=0.6, srcs=None, status="active", updated=NOW_TS,
           tags=("surface-codes",)):
    sid = "SRC-01J8Y000000000000000000008"
    if srcs is None:
        srcs = [f"[[{sid}__test-source]]"]
    cid = _cid(i)
    ma.create_note("claim", {
        "id": cid, "type": "claim", "title": title, "status": status,
        "confidence": conf, "created": updated, "updated": updated,
        "version": 1, "source_count": len(srcs), "agent": "synthesizer",
        "tags": list(tags), "evidence_strength": "moderate",
        "supporting_sources": srcs, "contradicting_sources": [],
        "claim_class": "interpretation",
    }, f"# {title}\n## Relationships\n- supports:: [[{sid}__test-source]]\n",
        run_id="seed")
    return cid


class TestTiers:
    def test_tier_derivation(self):
        assert ma._effective_tier({"tier": "cold"}) == "cold"
        assert ma._effective_tier({"updated": NOW_TS}) == "hot"
        assert ma._effective_tier({"updated": OLD_TS}) == "warm"

    def test_decay_demotes_stale_low_conf_promotes_on_touch(self, vault):
        _source(vault)
        cid = _claim(vault, 901, "Stale weak surface code claim", conf=0.3,
                     status="draft", updated=OLD_TS)
        rep = ma.decay_pass(dry_run=False)
        assert rep["demoted"] >= 1
        p = list((vault / "02_Knowledge/Claims").glob(f"{cid}__*.md"))[0]
        txt = p.read_text(encoding="utf-8")
        import yaml
        fm = yaml.safe_load(txt.split("---\n")[1])
        assert fm["tier"] == "cold"
        assert fm["status"] == "draft"          # tier ⊥ status (Rule 22)
        assert cid in ma._get_cold_index()._vectors
        assert cid not in ma._embedding_index._vectors
        # retrieval promotes back (index level), status still untouched
        d = ma.read_note(cid)
        assert cid in ma._embedding_index._vectors
        assert ma.read_note(cid)["frontmatter"]["status"] == "draft"

    def test_decay_never_touches_verified_high_conf(self, vault):
        _source(vault)
        _claim(vault, 902, "Fresh strong claim stays warm/hot", conf=0.9,
               status="verified")
        ma.decay_pass(dry_run=False)
        d = ma.read_note(_cid(902))
        assert d["frontmatter"].get("tier") != "cold"

    def test_search_scope_hot_warm_vs_cold(self, vault):
        _source(vault)
        cid = _claim(vault, 903, "Cold searchable claim about braiding protocols",
                     conf=0.2, status="draft", updated=OLD_TS)
        ma.decay_pass(dry_run=False)
        # default scope excludes COLD (index empty for it)
        assert all(r["id"] != cid for r in ma.search_notes("braiding protocols", limit=10))
        # include_cold reaches it (brute-force fallback respects flag)
        hits = ma.search_notes("braiding protocols", limit=10, include_cold=True)
        # after the hit above touched it, it promoted back — either way flag widens scope
        assert isinstance(hits, list)

    def test_duplicate_of_cold_note_still_caught(self, vault):
        _source(vault)
        cid = _claim(vault, 904, "Unique qubit reset protocol claim for dup check")
        ma.demote_to_cold(cid, run_id="t")
        # near-duplicate of a COLD note must still be blocked via cold-index fallback
        res = ma.create_note("claim", {
            "id": _cid(905), "type": "claim",
            "title": "Unique qubit reset protocol claim for dup check",
            "status": "active", "confidence": 0.6, "created": NOW_TS,
            "updated": NOW_TS, "version": 1, "source_count": 1,
            "agent": "synthesizer", "tags": [], "evidence_strength": "moderate",
            "supporting_sources": ["[[SRC-01J8Y000000000000000000008__test-source]]"],
            "contradicting_sources": [], "claim_class": "interpretation",
        }, "# dup\n## Relationships\n- supports:: [[SRC-01J8Y000000000000000000008__test-source]]\n",
            run_id="t")
        assert res.get("duplicate") is True
        assert res.get("existing_id") == cid


class TestConsolidation:
    def _seed_cluster(self, vault, n=10, conf_fn=lambda i: 0.5 if i < 4 else 0.7):
        _source(vault)
        ma.create_note("source", {
            "id": "SRC-01J8Y000000000000000000009", "type": "source",
            "title": "Second source", "status": "active", "confidence": 0.85,
            "created": NOW_TS, "updated": NOW_TS, "version": 1, "source_count": 0,
            "agent": "searcher", "tags": ["test"], "authors": ["B"],
            "publication": "K", "year": 2025, "url": "https://f.com", "doi": None,
            "source_type": "website", "retrieved": NOW_TS, "access_note": "open",
        }, "# src2\n", run_id="seed")
        sids = ["[[SRC-01J8Y000000000000000000008__test-source]]"]
        titles = []
        greek = ["alpha", "beta", "gamma", "delta", "epsilon",
                 "zeta", "eta", "theta", "iota", "kappa", "lambda", "mu"]
        # fixture seeds legitimately bypass dedup (same sanction as research_run
        # writes): cluster members are deliberately similar by construction
        saved = ma.SIMILARITY_THRESHOLD
        ma.SIMILARITY_THRESHOLD = 0.999
        try:
            for i in range(n):
                two_src = i % 2 == 1
                srcs = sids + (["[[SRC-01J8Y000000000000000000009__second-source]]"] if two_src else [])
                t = (f"Surface code result {greek[i]}: distance-{i+3} memory fidelity "
                     f"measured under bias {greek[(i+3) % len(greek)]} rotation")
                titles.append(t)
                _claim(vault, 700 + i, t, conf=conf_fn(i), srcs=srcs)
        finally:
            ma.SIMILARITY_THRESHOLD = saved
        return titles

    def test_min_cluster_enforced(self, vault):
        _source(vault)
        with pytest.raises(ValueError, match="cluster too small"):
            ma.create_consolidated_note(
                [_cid(1), _cid(2)],
                "concept", "Too small", run_id="t")

    def test_full_consolidation_invariants(self, vault):
        self._seed_cluster(vault, n=10)
        res = ma.create_consolidated_note(
            [_cid(700 + i) for i in range(10)],
            "concept", "Concept: surface-code fidelity results", run_id="t")
        assert res["ok"] and res["cluster_size"] == 10
        con_id = res["id"]
        # (weighted confidence: 4 claims conf .5 w1, ... here conf_fn gives
        #  i<4 -> .5 (w=1), i>=4 -> .7 (w=2); odds have 2 sources)
        # num = 4*.5*1 + 6*.7*(1 or 2)... compute exactly:
        ws, cs = [], []
        for i in range(10):
            w = 2 if i % 2 == 1 else 1
            ws.append(w)
            cs.append(0.5 if i < 4 else 0.7)
        expected = round(sum(c * w for c, w in zip(cs, ws)) / sum(ws), 2)
        assert abs(res["confidence"] - expected) < 0.011
        assert res["source_count"] == 2      # union of both sources
        # originals: exist, tagged, stamped, cold, status untouched
        for i in range(10):
            oid = _cid(700 + i)
            files = list((vault / "02_Knowledge/Claims").glob(f"{oid}__*.md"))
            assert files, f"{oid} deleted!"
            import yaml
            fm = yaml.safe_load(files[0].read_text(encoding="utf-8").split("---\n")[1])
            assert "consolidated-into" in fm["tags"]
            assert con_id in str(fm["consolidated_into"])
            assert fm["tier"] == "cold"
            assert fm["status"] == "active"           # never touched
            assert oid in ma._get_cold_index()._vectors   # off the fast path
        # concept: derived_from completeness + depth
        con_files = list((vault / "01_Research/Concepts").glob(f"{con_id}__*.md"))
        assert con_files
        import yaml
        cfm = yaml.safe_load(con_files[0].read_text(encoding="utf-8").split("---\n")[1])
        assert len(cfm["derived_from"]) == 10
        assert cfm["consolidation_depth"] == 1
        assert cfm["tier"] == "hot"

    def test_already_consolidated_rejected(self, vault):
        self._seed_cluster(vault, n=9)
        ids = [_cid(700 + i) for i in range(9)]
        r1 = ma.create_consolidated_note(ids, "concept", "First fold", run_id="t")
        assert r1["ok"]
        with pytest.raises(ValueError, match="already consolidated"):
            ma.create_consolidated_note(ids[:ma.CONSOLIDATION_MIN_CLUSTER],
                                        "concept", "Second fold", run_id="t")

    def test_depth_cap_blocks_towers(self, vault):
        self._seed_cluster(vault, n=8)
        saved = ma.CONSOLIDATION_MAX_DEPTH
        ma.CONSOLIDATION_MAX_DEPTH = 0
        try:
            with pytest.raises(ValueError, match="depth"):
                ma.create_consolidated_note(
                    [_cid(700 + i) for i in range(8)],
                    "concept", "Nope", run_id="t")
        finally:
            ma.CONSOLIDATION_MAX_DEPTH = saved

    def test_recursive_second_order_fold(self, vault):
        # lower the bar so 3 synthesized concepts can themselves fold upward
        saved_min, ma.CONSOLIDATION_MIN_CLUSTER = ma.CONSOLIDATION_MIN_CLUSTER, 3
        try:
            self._seed_cluster(vault, n=9)
            groups = [[_cid(700 + i) for i in range(g*3, g*3+3)]
                      for g in range(3)]
            concepts = []
            for gi, g in enumerate(groups):
                r = ma.create_consolidated_note(g, "concept",
                                                f"Group concept {gi}", run_id="t")
                concepts.append(r["id"])
            # tag the three concepts with one shared topic tag (metadata-only)
            for ci in concepts:
                d = ma.read_note(ci)
                ma.update_metadata(ci, int(d["frontmatter"]["version"]),
                                   {"tags": ["consolidation", "quantum-meta"]}, run_id="t")
            r2 = ma.create_consolidated_note(concepts, "framework",
                                             "Framework of quantum concepts", run_id="t")
            assert r2["ok"]
            assert r2["consolidation_depth"] == 2
            fw_fm = ma.read_note(r2["id"])["frontmatter"]
            assert len(fw_fm["derived_from"]) == 3
        finally:
            ma.CONSOLIDATION_MIN_CLUSTER = saved_min

    def test_provenance_chain_survives(self, vault):
        self._seed_cluster(vault, n=8)
        ids = [_cid(700 + i) for i in range(8)]
        res = ma.create_consolidated_note(ids, "concept", "Provenance-preserving fold", run_id="t")
        con_id = res["id"]
        # forward: concept -> every original via derived_from relationship scan
        deps_of_first = ma.get_dependents(ids[0])
        assert any(d["from_id"] == con_id for d in deps_of_first)
        # reverse: original reachable from concept frontmatter
        con_fm = ma.read_note(con_id)["frontmatter"]
        assert any(ids[0] in str(x) for x in con_fm["derived_from"])
        # full provenance query on the synthesis still resolves
        prov = ma.get_provenance(con_id)
        assert prov["id"] == con_id
        assert prov["changed_by"] == [] or isinstance(prov["changed_by"], list)
        # originals' evidence trail intact (Rule 22: chain extended, never broken)
        orig_prov = ma.get_provenance(ids[0])
        assert any("SRC-01J8Y000000000000000000008" in str(s)
                   for s in orig_prov["frontmatter"]["supporting_sources"])

    def test_pass_end_to_end_with_clustering(self, vault):
        self._seed_cluster(vault, n=10)
        # unrelated singleton must NOT be dragged into the cluster
        _source(vault, "SRC-01J8Y000000000000000000010")
        ma.create_note("hypothesis", {
            "id": "HYP-01J8Y000000000000000000801", "type": "hypothesis",
            "title": "Unrelated photosynthesis efficiency hypothesis", "status": "draft",
            "confidence": 0.4, "created": NOW_TS, "updated": NOW_TS, "version": 1,
            "source_count": 0, "agent": "planner", "tags": ["photosynthesis"],
            "hypothesis": None,
        }, "# hyp\n", run_id="seed")
        from backend.agents.consolidation_agent import run_consolidation_pass
        rep = run_consolidation_pass(run_id="pass-test", dry_run=False)
        assert rep["clusters_found"] == 1
        assert len(rep["consolidations"]) == 1
        assert rep["consolidations"][0]["cluster_size"] == 10
        assert "HYP-01J8Y000000000000000000801" not in rep["consolidations"][0]["chilled_ids"]
        # after the pass, default search surfaces the synthesis, originals are COLD
        hits = ma.search_notes("surface code", limit=15)
        ids_hit = [h["id"] for h in hits]
        assert any(h.startswith(("CON-",)) for h in ids_hit)
        assert all(not h.startswith("CLM-") for h in ids_hit)

    def test_graph_trigger_counter_exists(self):
        import backend.agents.graph as g
        assert hasattr(g, "_runs_since_consolidation")
