"""REX-Brain test suite harness (Tests A-J companion).

Runs the production LangGraph pipeline directly and captures evidence artifacts
into rex_test_evidence/<label>/.

Usage (from repo root):
    python rex_tests/harness.py run --label A_baseline --query "..." [--depth 1 ...]
    python rex_tests/harness.py hashes            # sha256 of production agent files
    python rex_tests/harness.py vault-head        # current vault git HEAD
"""
import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VAULT = ROOT / "REX-Brain"
TEST_VAULT = Path(os.environ.get("REX_TEST_VAULT", str(ROOT / "rex_test_vault")))
EVIDENCE = ROOT / "rex_test_evidence"

sys.path.insert(0, str(BACKEND))

PROD_FILES = [
    "backend/agents/graph.py",
    "backend/agents/memory_agent.py",
    "backend/agents/ga_workflow.py",
    "backend/agents/consolidation_agent.py",
    "backend/agents/state.py",
]

SPEC_NODE_ORDER = [
    "memory_retrieval", "planner", "searcher", "filter", "synthesis",
    "gap_detector", "citation_mapper", "report_node_id", "evaluator",
    "memory_update", "evolution_analysis",
]


def load_env():
    env_path = BACKEND / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def prod_file_hashes():
    out = {}
    for rel in PROD_FILES:
        p = ROOT / rel
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def vault_head(vault_path=None):
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=vault_path or TEST_VAULT,
                       capture_output=True, text=True)
    return r.stdout.strip()


def vault_log(n=10, vault_path=None):
    r = subprocess.run(["git", "log", "--oneline", f"-{n}"], cwd=vault_path or TEST_VAULT,
                       capture_output=True, text=True)
    return r.stdout.strip()


class Tee:
    def __init__(self, primary, mirror):
        self.primary, self.mirror = primary, mirror

    def write(self, s):
        self.primary.write(s)
        try:
            self.mirror.write(s)
        except Exception:
            pass

    def flush(self):
        self.primary.flush()
        try:
            self.mirror.flush()
        except Exception:
            pass


def run_research(query, label, depth=1, complexity=1, paragraphs=3,
                 subquestions=8, timeout_s=1500, budget=None):
    """Run one full research pass through the production graph."""
    load_env()
    os.environ["LLM_TIMEOUT"] = "300"  # local-model headroom; .env default is 180
    if budget is not None:
        os.environ["REX_MEMORY_BUDGET_TOKENS"] = str(budget)
    else:
        os.environ.pop("REX_MEMORY_BUDGET_TOKENS", None)
    # Isolate all vault writes in the test-vault clone (never the live REX-Brain/
    # vault, which the running backend server may write to concurrently).
    os.environ["REX_VAULT_PATH"] = str(TEST_VAULT)
    from agents.graph import app_graph

    outdir = EVIDENCE / label
    outdir.mkdir(parents=True, exist_ok=True)

    sid = f"rextest-{label}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    config = {"configurable": {"thread_id": sid}}
    initial_state = {
        "messages": [], "query": query, "depth": depth, "complexity": complexity,
        "target_paragraphs": paragraphs, "target_sub_questions": subquestions,
        "current_depth": 0, "sub_questions": [], "search_queries": [],
        "raw_pages": {}, "source_urls": [], "scored_chunks": [],
        "synthesis_results": [], "gap_results": [], "gap_iteration": 0,
        "cited_report": "", "report": "", "findings": [], "sub_tasks": [],
        "feedback": "", "is_valid": False, "prior_lessons": [],
        "retrieved_memory": [], "structured_refs": [], "metrics": {},
        "logs": [], "active_node": "",
    }

    log_fh = open(outdir / "run_stdout.log", "w", encoding="utf-8")
    node_seq = []
    errors = []
    t0 = time.time()
    code = 0
    try:
        with contextlib.redirect_stdout(Tee(sys.__stdout__, log_fh)):
            for output in app_graph.stream(initial_state, config=config):
                node_name = list(output.keys())[0]
                node_seq.append(node_name)
                print(f"[HARNESS] node completed: {node_name}", flush=True)
    except Exception as e:  # noqa: BLE001
        errors.append(f"{type(e).__name__}: {e}")
        code = 1
    finally:
        log_fh.close()
    wall = round(time.time() - t0, 1)

    snap = app_graph.get_state(config)
    values = snap.values if snap else {}

    def _safe(key, default=None):
        v = values.get(key, default)
        return v

    evidence = {
        "label": label,
        "session_id": sid,
        "vault_path": str(TEST_VAULT),
        "query": query,
        "wall_clock_seconds": wall,
        "node_sequence": node_seq,
        "spec_node_order": SPEC_NODE_ORDER,
        "order_matches_spec_linear": node_seq == SPEC_NODE_ORDER,
        "errors": errors,
        "exit_code": code,
        "vault_head_before": None,
        "run_id": _safe("run_id"),
        "linked_notes": _safe("linked_notes", []),
        "classification_table": _safe("classification_table", []),
        "memory_context_meta": (_safe("memory_context") or {}).get("_meta"),
        "memory_context_items": {
            k: [{"id": i.get("id"), "title": i.get("title"), "bucket": i.get("bucket"),
                 "score": i.get("score"), "tokens": i.get("tokens")}
                for i in (v if isinstance(v, list) else [])]
            for k, v in (_safe("memory_context") or {}).items() if k != "_meta"
        },
        "source_urls": _safe("source_urls", []),
        "sub_questions": _safe("sub_questions", []),
        "structured_refs_count": len(_safe("structured_refs", []) or []),
        "feedback": _safe("feedback"),
        "is_valid_gap": _safe("is_valid"),
        "gap_iterations": _safe("gap_iteration"),
        "prod_hashes_after": prod_file_hashes(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }

    (outdir / "evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    report = _safe("report", "") or ""
    (outdir / "report.md").write_text(report, encoding="utf-8")
    cited = _safe("cited_report", "") or ""
    (outdir / "cited_report.md").write_text(cited, encoding="utf-8")
    refs = _safe("structured_refs", []) or []
    (outdir / "structured_refs.json").write_text(
        json.dumps(refs, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    cls = _safe("classification_table", []) or []
    (outdir / "classification_table.json").write_text(
        json.dumps(cls, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(json.dumps({
        "label": label, "session_id": sid, "wall_s": wall,
        "nodes": node_seq, "errors": errors,
        "report_chars": len(report), "refs": len(refs),
        "linked_notes": evidence["linked_notes"],
    }, indent=2))
    return evidence


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--label", required=True)
    r.add_argument("--query", required=True)
    r.add_argument("--depth", type=int, default=1)
    r.add_argument("--complexity", type=int, default=1)
    r.add_argument("--paragraphs", type=int, default=3)
    r.add_argument("--subquestions", type=int, default=8)
    r.add_argument("--budget", type=int, default=None)
    h = sub.add_parser("hashes")
    v = sub.add_parser("vault-head")
    args = ap.parse_args()

    if args.cmd == "run":
        run_research(args.query, args.label, args.depth, args.complexity,
                     args.paragraphs, args.subquestions, budget=args.budget)
    elif args.cmd == "hashes":
        print(json.dumps(prod_file_hashes(), indent=2))
    elif args.cmd == "vault-head":
        print(vault_head())


if __name__ == "__main__":
    main()
