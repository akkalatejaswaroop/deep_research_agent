"""Tests for backend.agents.claude_obsidian_integration module.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
import pytest

from backend.agents.claude_obsidian_integration import (
    get_doctor_status,
    lint_vault,
    save_finding,
    query_vault,
    ingest_source,
    DEFAULT_VAULT_PATH,
)


def test_doctor_status_rex_brain():
    """Verify doctor check succeeds on adopted REX-Brain vault."""
    res = get_doctor_status(str(DEFAULT_VAULT_PATH))
    assert isinstance(res, dict)
    assert res.get("ok") is True
    assert res.get("checks", {}).get("vault_exists") is True
    assert res.get("checks", {}).get("wiki") is True


def test_doctor_status_knowledge_vault():
    """Verify doctor check succeeds on initialized knowledge_vault."""
    kv_path = DEFAULT_VAULT_PATH.parent / "knowledge_vault"
    res = get_doctor_status(str(kv_path))
    assert isinstance(res, dict)
    assert res.get("ok") is True
    assert res.get("checks", {}).get("vault_exists") is True


def test_save_finding_and_query():
    """Verify saving a finding and querying it from the vault."""
    title = "Test Quantum Majorana Research Note"
    content = "Majorana zero modes exhibit non-Abelian braiding statistics in 1D topological nanowires."

    save_res = save_finding(title, content, vault_path=str(DEFAULT_VAULT_PATH))
    assert save_res.get("status") == "success"
    assert os.path.exists(save_res["path"])

    query_res = query_vault("Majorana zero modes", vault_path=str(DEFAULT_VAULT_PATH))
    assert query_res.get("status") == "success"
    assert query_res.get("total_results", 0) > 0


def test_ingest_source_tempfile():
    """Verify ingesting a source document into the vault inbox."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Ingested Paper Source\n\nTitle: Topological Quantum Computation\nAuthors: Kitaev et al.\n")
        temp_path = f.name

    try:
        res = ingest_source(temp_path, vault_path=str(DEFAULT_VAULT_PATH))
        assert isinstance(res, dict)
        assert res.get("status") in ("success", "applied") or "items" in res or "raw" in res
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
