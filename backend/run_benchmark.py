"""
run_benchmark.py
----------------
Benchmark runner for REX deep research agent.
Usage:
    python run_benchmark.py                  # runs full benchmark
    python run_benchmark.py --quick           # runs 2 queries per topic
    python run_benchmark.py --query "..."     # runs a single custom query
    python run_benchmark.py --compare baseline.json  # compares with previous run
"""
import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_main_loaded = False
def _get_main():
    global _main_loaded
    # Lazy-load to avoid heavy imports until first use
    import main as _m
    _main_loaded = True
    return _m

from benchmark_queries import BENCHMARK


def run_single(query: str, label: str = "") -> dict:
    t0 = time.perf_counter()
    try:
        main = _get_main()
        result = main.build_report_autonomously(
            query,
            depth=1,
            complexity=1,
            target_paragraphs=3,
            target_sub_questions=6,
        )
        elapsed = round((time.perf_counter() - t0) * 1000, 1)

        report = result.get("report", "")
        source_urls = result.get("source_urls", [])
        structured_refs = result.get("structured_refs", [])
        synthesis = result.get("synthesis_results", [])
        section_texts = [s.get("answer", "") for s in synthesis]
        metrics = result.get("_metrics", {})

        scores = main.generate_quality_scores(query, report, source_urls)
        overall = main.compute_overall(scores)
        # Build source dicts with content field for run_qa_pass
        qa_sources = []
        for ref in structured_refs:
            qa_sources.append({
                "url": ref.get("url", ""),
                "domain": ref.get("domain", ""),
                "title": ref.get("title", ""),
                "content": "",
            })
        qa_result = main.run_qa_pass(report, section_texts, qa_sources, query)
        word_count = len(report.split())
        citation_count = report.count("[^") + report.count("[")
        sub_q_count = len(synthesis)

        return {
            "query": query,
            "label": label or query[:60],
            "timestamp": datetime.now().isoformat(),
            "duration_ms": elapsed,
            "word_count": word_count,
            "sub_questions": sub_q_count,
            "sources": len(source_urls),
            "citation_count": citation_count,
            "scores": scores,
            "overall": overall,
            "qa_issues": len(qa_result.get("issues", [])),
            "qa_passed": qa_result.get("passed", False),
            "qa_issues_list": qa_result.get("issues", []),
            "metrics": metrics,
            "success": True,
            "error": None,
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        print(f"  ERROR: {e}")
        return {
            "query": query,
            "label": label or query[:60],
            "timestamp": datetime.now().isoformat(),
            "duration_ms": elapsed,
            "success": False,
            "error": str(e),
            "word_count": 0,
            "sub_questions": 0,
            "sources": 0,
            "citation_count": 0,
            "scores": {"relevance": 0, "depth": 0, "novelty": 0, "coherence": 0, "citation_accuracy": 0},
            "overall": 0,
            "qa_issues": 999,
            "qa_passed": False,
            "qa_issues_list": [f"Run failed: {e}"],
            "metrics": {},
        }


def run_benchmark(queries: list) -> dict:
    results = []
    total = len(queries)
    passed = 0
    failed = 0

    print(f"\n{'='*60}")
    print(f"RUNNING BENCHMARK: {total} queries")
    print(f"{'='*60}\n")

    for i, item in enumerate(queries):
        q = item.get("query", "")
        label = f"[{item.get('id', f'Q{i+1}')}] ({item.get('topic', '?')})"
        print(f"  {i+1}/{total} {label}: {q[:70]}...")

        result = run_single(q, label)
        result["benchmark_id"] = item.get("id", f"Q{i+1}")
        result["topic"] = item.get("topic", "unknown")
        results.append(result)

        status = "PASS" if result["success"] else "FAIL"
        score_str = f"score={result['overall']:.1f}" if result["success"] else f"error={result['error'][:50]}"
        print(f"    -> {status} {score_str} ({result['duration_ms']:.0f}ms, {result['word_count']}w, {result['sources']}src)")
        if result["success"]:
            passed += 1
        else:
            failed += 1

    scores = [r["scores"] for r in results if r["success"]]
    avg_scores = {}
    for dim in ["relevance", "depth", "novelty", "coherence", "citation_accuracy"]:
        vals = [s.get(dim, 0) for s in scores]
        avg_scores[dim] = round(sum(vals) / max(1, len(vals)), 1)

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "passed": passed,
        "failed": failed,
        "avg_scores": avg_scores,
        "avg_overall": round(sum(r["overall"] for r in results if r["success"]) / max(1, passed), 1),
        "avg_duration_ms": round(sum(r["duration_ms"] for r in results) / max(1, total), 1),
        "avg_word_count": round(sum(r["word_count"] for r in results) / max(1, passed), 1),
        "avg_sources": round(sum(r["sources"] for r in results) / max(1, passed), 1),
        "avg_qa_issues": round(sum(r["qa_issues"] for r in results) / max(1, total), 1),
        "total_qa_issues": sum(r["qa_issues"] for r in results),
        "total_passed_qa": sum(1 for r in results if r["qa_passed"]),
    }

    return {
        "summary": summary,
        "results": results,
        "config": {
            "depth": 1,
            "complexity": 1,
            "target_paragraphs": 3,
            "target_sub_questions": 6,
        }
    }


def print_report(data: dict):
    s = data["summary"]
    print(f"\n{'='*60}")
    print(f"BENCHMARK RESULTS")
    print(f"{'='*60}")
    print(f"  Total queries:  {s['total']}")
    print(f"  Passed:         {s['passed']}")
    print(f"  Failed:         {s['failed']}")
    print(f"  Avg overall:    {s['avg_overall']:.1f}/10")
    print(f"  Avg duration:   {s['avg_duration_ms']:.0f}ms")
    print(f"  Avg word count: {s['avg_word_count']:.0f}")
    print(f"  Avg sources:    {s['avg_sources']:.0f}")
    print(f"  Avg QA issues:  {s['avg_qa_issues']:.1f}")
    print(f"  QA passed:      {s['total_passed_qa']}/{s['total']}")
    print(f"\n  Dimension scores:")
    for dim, val in s["avg_scores"].items():
        print(f"    {dim:20s}: {val:.1f}/10")

    print(f"\n  Per-query results:")
    for r in data["results"]:
        status = "PASS" if r["success"] else "FAIL"
        print(f"    {status}  {r['benchmark_id']:15s} overall={r['overall']:.1f}  "
              f"qa={r['qa_issues']}  {r['word_count']:5d}w  {r['sources']}src  {r['duration_ms']:.0f}ms"
              + (f"  ERR: {r['error'][:60]}" if not r["success"] else ""))


def compare_runs(baseline_path: str, current: dict):
    with open(baseline_path) as f:
        baseline = json.load(f)

    b_scores = baseline.get("summary", {}).get("avg_scores", {})
    c_scores = current["summary"]["avg_scores"]

    print(f"\n{'='*60}")
    print(f"COMPARISON: {baseline_path} vs current")
    print(f"{'='*60}")
    for dim in ["relevance", "depth", "novelty", "coherence", "citation_accuracy"]:
        b = b_scores.get(dim, 0)
        c = c_scores.get(dim, 0)
        delta = c - b
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "─")
        print(f"  {dim:20s}: {b:.1f} → {c:.1f}  {arrow} {delta:+.1f}")

    b_overall = baseline["summary"].get("avg_overall", 0)
    c_overall = current["summary"]["avg_overall"]
    delta_overall = c_overall - b_overall
    arrow = "▲" if delta_overall > 0 else ("▼" if delta_overall < 0 else "─")
    print(f"  {'OVERALL':20s}: {b_overall:.1f} → {c_overall:.1f}  {arrow} {delta_overall:+.1f}")

    b_qa = baseline["summary"].get("total_qa_issues", 0)
    c_qa = current["summary"]["total_qa_issues"]
    delta_qa = b_qa - c_qa
    arrow = "▲" if delta_qa > 0 else ("▼" if delta_qa < 0 else "─")
    print(f"  {'QA issues':20s}: {b_qa} → {c_qa}  {arrow} {delta_qa:+.0f}")

    return {
        "baseline": baseline_path,
        "current_timestamp": current["timestamp"],
        "deltas": {
            dim: {
                "before": b_scores.get(dim, 0),
                "after": c_scores.get(dim, 0),
                "delta": round(c_scores.get(dim, 0) - b_scores.get(dim, 0), 1),
            }
            for dim in ["relevance", "depth", "novelty", "coherence", "citation_accuracy"]
        },
        "overall_delta": round(c_overall - b_overall, 1),
        "qa_issues_delta": delta_qa,
    }


def main():
    parser = argparse.ArgumentParser(description="REX Benchmark Runner")
    parser.add_argument("--quick", action="store_true", help="Run 2 queries per topic (quick check)")
    parser.add_argument("--query", type=str, help="Run a single custom query")
    parser.add_argument("--compare", type=str, help="Compare with a previous results JSON file")
    parser.add_argument("--output", type=str, default="", help="Output file path (default: auto-named)")
    parser.add_argument("--tag", type=str, default="", help="Tag for the run (e.g., 'baseline', 'after_self_consistency')")
    args = parser.parse_args()

    if args.query:
        queries = [{"id": "custom", "query": args.query, "topic": "custom"}]
    elif args.quick:
        topics_seen = {}
        queries = []
        for item in BENCHMARK:
            t = item["topic"]
            if topics_seen.get(t, 0) < 2:
                queries.append(item)
                topics_seen[t] = topics_seen.get(t, 0) + 1
    else:
        queries = BENCHMARK

    data = run_benchmark(queries)
    print_report(data)

    tag = args.tag or "benchmark"
    output_path = args.output or f"benchmark_results_{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    if args.compare:
        compare_runs(args.compare, data)

    return 0 if data["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
