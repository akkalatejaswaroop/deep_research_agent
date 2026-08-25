"""Prompt 11 tests — provenance as queryable trail."""
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

import pytest

os.environ.setdefault("PREFER_LLM", "false")

import backend.agents.memory_agent as ma
import math as _math
import re as _re
import hashlib as _hashlib


def _fast_embed(text):
    vec = [0.0] * 384
    for tok in _re.findall(r"[a-z0-9]{3,}", text.lower()):
        h = int(_hashlib.sha256(tok.encode()).hexdigest()[:8], 16) % 384
        vec[h] += 1.0
    n = _math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


ma.LocalVectorIndex._embed = lambda self, text: _fast_embed(text)
ma.LocalVectorIndex._embed_ollama = lambda self, text: None


@pytest.fixture
def vault(tmp_path):
    for d in ["02_Knowledge/Claims", "03_Sources/Websites", "04_Experiments/Runs",
              "05_Evolution/Proposals"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    old = ma.VAULT_PATH
    ma.VAULT_PATH = tmp_path
    ma._embedding_index = ma.LocalVectorIndex()
    ma._write_counts.clear()
    for cmd in (["git", "init"], ["git", "config", "user.name", "t"],
                ["git", "config", "user.email", "t@t.t"]):
        subprocess.run(cmd, cwd=str(tmp_path), capture_output=True)
    yield tmp_path
    ma.VAULT_PATH = old


def _source(vault, nid="SRC-01J8Y000000000000000000008"):
    ma.create_note("source", {
        "id": nid, "type": "source", "title": "Test source", "status": "active",
        "confidence": 0.9, "created": "2026-08-25T10:00:00Z", "updated": "2026-08-25T10:00:00Z",
        "version": 1, "source_count": 0, "agent": "searcher", "tags": ["test"],
        "authors": ["A"], "publication": "J", "year": 2024, "url": "https://e.com",
        "doi": None, "source_type": "website", "retrieved": "2026-08-25T10:00:00Z",
        "access_note": "open",
    }, "# src\n", run_id="t")


class TestClaimProvenanceGate:
    def test_unsourced_claim_without_tag_rejected(self, vault):
        _source(vault)
        with pytest.raises(ValueError, match="no-claim-without-provenance"):
            ma.create_note("claim", {
                "id": "CLM-01J8Y0000000000000000000A1", "type": "claim",
                "title": "Unsourced no tag", "status": "draft", "confidence": 0.5,
                "created": "2026-08-25T10:00:00Z", "updated": "2026-08-25T10:00:00Z",
                "version": 1, "source_count": 0, "agent": "synthesizer", "tags": [],
                "evidence_strength": "weak", "supporting_sources": [],
                "contradicting_sources": [], "claim_class": "speculation",
            }, "# c\n", run_id="t")

    def test_exactly_one_exempt_tag_passes(self, vault):
        ma.create_note("claim", {
            "id": "CLM-01J8Y0000000000000000000A2", "type": "claim",
            "title": "Generated claim ok", "status": "draft", "confidence": 0.5,
            "created": "2026-08-25T10:00:00Z", "updated": "2026-08-25T10:00:00Z",
            "version": 1, "source_count": 0, "agent": "synthesizer",
            "tags": ["generated"], "evidence_strength": "weak",
            "supporting_sources": [], "contradicting_sources": [],
            "claim_class": "hypothesis",
        }, "# c\n> Orphan justification: generated internally by design.\n", run_id="t")
        assert ma.read_note("CLM-01J8Y0000000000000000000A2")["frontmatter"]["id"]

    def test_two_exempt_tags_rejected(self, vault):
        with pytest.raises(ValueError, match="EXACTLY ONE"):
            ma.create_note("claim", {
                "id": "CLM-01J8Y0000000000000000000A3", "type": "claim",
                "title": "Ambiguous", "status": "draft", "confidence": 0.5,
                "created": "2026-08-25T10:00:00Z", "updated": "2026-08-25T10:00:00Z",
                "version": 1, "source_count": 0, "agent": "synthesizer",
                "tags": ["generated", "unverified"], "evidence_strength": "weak",
                "supporting_sources": [], "contradicting_sources": [],
                "claim_class": "speculation",
            }, "# c\n", run_id="t")


class TestGitTrail:
    def test_update_commits_with_id_agent_reason(self, vault):
        _source(vault)
        cid = "CLM-01J8Y0000000000000000000B1"
        ma.create_note("claim", {
            "id": cid, "type": "claim", "title": "Sourced claim trail",
            "status": "active", "confidence": 0.7,
            "created": "2026-08-25T10:00:00Z", "updated": "2026-08-25T10:00:00Z",
            "version": 1, "source_count": 1, "agent": "evaluator", "tags": [],
            "evidence_strength": "moderate",
            "supporting_sources": ["[[SRC-01J8Y000000000000000000008__test-source]]"],
            "contradicting_sources": [], "claim_class": "interpretation",
        }, "# c\n## Relationships\n- supports:: [[SRC-01J8Y000000000000000000008__test-source]]\n", run_id="t")

        # Rule 17: content change must add a new WikiLink — add a corroborating run link
        d = ma.read_note(cid)
        new_body = d["body"].rstrip() + "\n- supports:: [[RUN-01J8Y0000000000000000000B2]]\n"
        ma.update_note(cid, 1,
                       {"frontmatter": {"confidence": 0.85}, "body": new_body},
                       changelog_reason="raised after replication check passed",
                       run_id="t")
        log = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=str(vault),
                             capture_output=True, text=True).stdout
        assert cid in log and "agent=evaluator" in log and "replication check" in log


class TestProvenanceReads:
    def _seed_run_and_claim(self, vault):
        _source(vault)
        cid = "CLM-01J8Y0000000000000000000C1"
        ma.create_note("claim", {
            "id": cid, "type": "claim", "title": "Run-linked claim",
            "status": "active", "confidence": 0.7,
            "created": "2026-08-25T10:00:00Z", "updated": "2026-08-25T10:00:00Z",
            "version": 1, "source_count": 1, "agent": "synthesizer", "tags": [],
            "evidence_strength": "moderate",
            "supporting_sources": ["[[SRC-01J8Y000000000000000000008__test-source]]"],
            "contradicting_sources": [], "claim_class": "interpretation",
        }, "# c\n## Relationships\n- supports:: [[SRC-01J8Y000000000000000000008__test-source]]\n", run_id="t")
        rid = "RUN-01J8Y0000000000000000000C2"
        (vault / "04_Experiments/Runs" / f"{rid}__run.md").write_text(
            "---\nid: %s\ntype: research_run\ntitle: R\nstatus: active\nconfidence: 0.7\n"
            "created: 2026-08-25T10:00:00Z\nupdated: 2026-08-25T10:00:00Z\nversion: 1\n"
            "source_count: 1\nagent: memory\ntags: []\nquery: q\nsub_questions: []\n"
            'report: "r"\ncitations: []\nresult: success\nagent_outcomes: {}\n'
            "linked_notes:\n  - \"[[%s]]\"\n"
            "classification_table: []\ntoken_counts: {}\n---\n# run\n" % (rid, cid),
            encoding="utf-8")
        return cid, rid

    def test_get_creating_runs_reverse_lookup(self, vault):
        cid, rid = self._seed_run_and_claim(vault)
        runs = ma.get_creating_runs(cid)
        assert any(r["id"] == rid for r in runs)
        assert runs[0]["result"] == "success"

    def test_get_evidence_diff_tracks_sources(self, vault):
        cid, rid = self._seed_run_and_claim(vault)
        # v2: add a second supporting source (Rule 17 satisfied by the new link itself)
        d = ma.read_note(cid)
        new_fm = {"supporting_sources": d["frontmatter"]["supporting_sources"]
                  + ["[[SRC-01J8Y000000000000000000009__second-source]]"],
                  "confidence": 0.85}
        ma.update_note(cid, 1, {"frontmatter": new_fm},
                       changelog_reason="added second corroborating source link", run_id="t")
        diffs = ma.get_evidence_diff(cid)
        assert len(diffs) >= 2
        added_all = [s for d0 in diffs for s in d0["added"]]
        assert any("SRC-01J8Y000000000000000000009" in s for s in added_all)
        assert any("SRC-01J8Y000000000000000000008" in s for s in added_all)

    def test_apply_evolution_stamps_changed_by(self, vault):
        cid, rid = self._seed_run_and_claim(vault)
        pid = "PRP-01J8Y0000000000000000000D1"
        res = ma.create_evolution_proposal({
            "target": "searcher", "change": "x", "reason": "why not",
            "expected_performance": "+5%", "risk": "low",
            "benchmark": "b, n=10", "title": "P",
            "evidence": ["[[%s]]" % rid],
        }, run_id="t")
        pid = res["id"]
        # move proposal PROPOSED -> TESTING (legal transition) before applying
        pd = ma.read_note(pid)
        ma.update_note(pid, int(pd["frontmatter"]["version"]),
                       {"frontmatter": {"status": "TESTING"}},
                       changelog_reason="promoted to testing for apply check", run_id="t")
        d = ma.read_note(cid)
        ma.apply_evolution_to_note(cid, int(d["frontmatter"]["version"]), pid,
                                   changelog_reason="applied searcher change", run_id="t")
        ev = ma.get_evolution_for_note(cid)
        assert any(pid in str(x) for x in ev["changed_by"])
        prov = ma.get_provenance(cid)
        assert prov["changed_by"] and prov["last_git_commit"]
