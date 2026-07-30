"""Tests for the metrics collector."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.metrics_collector import (
    start_session, record_node_entry, record_node_exit,
    record_llm_call, record_quality_scores, record_prior_lessons,
    record_graph_state, compute, clear
)


def test_full_metrics_flow():
    sid = "test-session-1"
    start_session(sid, "test query", depth=2)

    # Simulate planner
    record_node_entry(sid, "planner")
    time.sleep(0.005)
    record_node_exit(sid, "planner")

    # Simulate searcher
    record_node_entry(sid, "searcher")
    time.sleep(0.01)
    record_graph_state(sid, {
        "sub_questions": ["Q1", "Q2"],
        "search_queries": [["q1"], ["q2"]],
        "source_urls": ["http://a.com", "http://b.com", "http://c.com"],
        "gap_iteration": 1
    })
    record_node_exit(sid, "searcher")

    # Simulate synthesis
    record_node_entry(sid, "synthesis")
    record_llm_call(sid, "synthesis", 500, 1500)
    record_llm_call(sid, "synthesis", 300, 1200)
    time.sleep(0.005)
    record_node_exit(sid, "synthesis")

    # Simulate evaluator
    record_node_entry(sid, "evaluator")
    record_quality_scores(sid, {
        "relevance": 8.5,
        "depth": 7.0,
        "novelty": 6.5,
        "coherence": 9.0,
        "citation_accuracy": 8.0
    })
    record_prior_lessons(sid, ["Search Wikipedia first", "Use academic sources"])
    record_node_exit(sid, "evaluator")

    # Compute metrics
    metrics = compute(sid)
    clear(sid)

    assert metrics is not None, "compute() should return metrics dict"

    # Check structure
    assert "execution" in metrics
    assert "breadth" in metrics
    assert "efficiency" in metrics
    assert "quality" in metrics
    assert "proof_of_improvement" in metrics

    # Check execution
    ex = metrics["execution"]
    assert ex["total_duration_ms"] > 0
    assert "planner" in ex["node_timings_ms"]
    assert "searcher" in ex["node_timings_ms"]
    assert "synthesis" in ex["node_timings_ms"]

    # Check breadth
    br = metrics["breadth"]
    assert br["depth"] == 2
    assert br["sub_questions"] == 2
    assert br["sources_found"] == 3
    assert br["gap_iterations"] == 1

    # Check efficiency
    ef = metrics["efficiency"]
    assert ef["total_llm_calls"] == 2
    assert ef["llm_calls_per_stage"]["synthesis"] == 2

    # Check quality
    ql = metrics["quality"]
    assert ql["scores"]["relevance"] == 8.5
    assert ql["overall"] == 7.8  # (8.5+7+6.5+9+8)/5

    # Check proof
    pi = metrics["proof_of_improvement"]
    assert pi["prior_lessons_count"] == 2
    assert len(pi["prior_lessons"]) == 2

    print("All metrics_collector tests passed!")


def test_empty_session():
    sid = "empty-session"
    start_session(sid, "", 1)
    result = compute(sid)
    clear(sid)
    assert result is not None
    assert result["execution"]["total_duration_ms"] >= 0
    assert result["quality"]["overall"] is None
    print("Empty session test passed!")


if __name__ == "__main__":
    test_full_metrics_flow()
    test_empty_session()
