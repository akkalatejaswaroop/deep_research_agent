import json
import os
import sys
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from benchmark_queries import BENCHMARK


MOCK_REPORT = "# Deep Research Report: Test\n\n## Executive Summary\n\nTest summary with citation [1].\n\n## Key Findings\n\nTest findings with data from 2026 showing 50% improvement [2].\n\n## References\n\n[1] https://example.com\n[2] https://test.org\n"

MOCK_SOURCES = [
    {"url": "https://example.com", "domain": "example.com", "title": "Example", "content": "Example content with factual data showing 50% improvement in 2026."},
    {"url": "https://test.org", "domain": "test.org", "title": "Test", "content": "Test content with results from 2025."},
]

MOCK_SOURCE_URLS = ["https://example.com", "https://test.org"]

MOCK_STRUCTURED_REFS = [
    {"id": 1, "url": "https://example.com", "domain": "example.com", "title": "Example"},
    {"id": 2, "url": "https://test.org", "domain": "test.org", "title": "Test"},
]

MOCK_SCORES = {"relevance": 7.5, "depth": 6.0, "novelty": 5.5, "coherence": 8.0, "citation_accuracy": 7.0}


def make_mock_result(report=MOCK_REPORT, sources=None, scores=None):
    if sources is None:
        sources = MOCK_SOURCES
    if scores is None:
        scores = MOCK_SCORES
    overall = round(sum(scores.values()) / len(scores), 1)
    return {
        "report": report,
        "structured_refs": MOCK_STRUCTURED_REFS,
        "source_urls": MOCK_SOURCE_URLS,
        "query": "test query",
        "synthesis_results": [{"sub_question": "Q1", "answer": "Test answer [1].", "source_refs": [{"url": "https://example.com"}]}],
        "_metrics": {
            "quality": {"scores": scores, "overall": overall},
            "execution": {"total_duration_ms": 1500, "node_timings_ms": {"planner": 200, "searcher": 500}},
            "breadth": {"sources_found": 2, "sub_questions": 1},
        },
        "feedback": "Research completed.",
    }


class TestBenchmarkQueries:
    def test_benchmark_has_queries(self):
        assert len(BENCHMARK) > 0

    def test_all_queries_have_required_fields(self):
        required = {"id", "query", "topic", "min_citations", "min_sub_questions"}
        for item in BENCHMARK:
            missing = required - set(item.keys())
            assert not missing, f"Query {item.get('id', '?')} missing fields: {missing}"

    def test_all_queries_have_unique_ids(self):
        ids = [item["id"] for item in BENCHMARK]
        assert len(ids) == len(set(ids)), "Duplicate benchmark IDs found"

    def test_queries_cover_all_topic_types(self):
        topics = {item["topic"] for item in BENCHMARK}
        expected = {"stable_technical", "emerging_trend", "company_product", "policy_debate"}
        assert topics == expected, f"Missing topics: {expected - topics}"

    def test_each_topic_has_at_least_3_queries(self):
        from collections import Counter
        counts = Counter(item["topic"] for item in BENCHMARK)
        for topic, count in counts.items():
            assert count >= 3, f"Topic '{topic}' only has {count} queries (min 3)"

    def test_queries_are_reasonably_long(self):
        for item in BENCHMARK:
            assert len(item["query"]) > 15, f"Query '{item['id']}' is too short"

    def test_queries_end_with_question_marks(self):
        for item in BENCHMARK:
            assert item["query"].strip().endswith("?"), f"Query '{item['id']}' must end with ?"

    def test_queries_have_no_duplicate_text(self):
        texts = [item["query"].strip().lower() for item in BENCHMARK]
        assert len(texts) == len(set(texts)), "Duplicate query texts found"


class TestRunSingle:
    def test_run_single_with_mock_success(self):
        from run_benchmark import run_single, _get_main
        mock_result = make_mock_result()
        with patch.object(_get_main(), "build_report_autonomously", return_value=mock_result):
            result = run_single("test query")
        assert result["success"] is True, f"Failed: {result.get('error')}"
        assert result["overall"] > 0
        assert result["word_count"] > 0
        assert result["sources"] > 0

    def test_run_single_scores_in_range(self):
        from run_benchmark import run_single, _get_main
        with patch.object(_get_main(), "build_report_autonomously", return_value=make_mock_result()):
            result = run_single("test query")
        for dim in ["relevance", "depth", "novelty", "coherence", "citation_accuracy"]:
            assert dim in result["scores"], f"Missing {dim}"
            assert 0 <= result["scores"][dim] <= 10, f"{dim}={result['scores'][dim]} out of range"

    def test_run_single_all_required_keys(self):
        from run_benchmark import run_single, _get_main
        with patch.object(_get_main(), "build_report_autonomously", return_value=make_mock_result()):
            result = run_single("test query")
        for key in ["query", "label", "timestamp", "duration_ms", "word_count", "scores", "overall", "qa_issues", "qa_passed"]:
            assert key in result, f"Missing key: {key}"

    def test_run_single_handles_failure(self):
        from run_benchmark import run_single, _get_main
        with patch.object(_get_main(), "build_report_autonomously", side_effect=RuntimeError("API failed")):
            result = run_single("test query")
        assert result["success"] is False
        assert "error" in result
        assert "API failed" in result["error"]
        assert result["overall"] == 0

    def test_run_single_empty_query(self):
        from run_benchmark import run_single, _get_main
        with patch.object(_get_main(), "build_report_autonomously", return_value=make_mock_result()):
            result = run_single("")
        assert isinstance(result, dict)
        assert "scores" in result


class TestRunBenchmark:
    def test_run_benchmark_produces_summary(self):
        from run_benchmark import run_benchmark
        with patch("run_benchmark.run_single") as mock_run:
            mock_run.return_value = {
                "success": True, "query": "test", "label": "test",
                "timestamp": "now", "duration_ms": 100, "word_count": 500,
                "sub_questions": 2, "sources": 3, "citation_count": 5,
                "scores": {"relevance": 7, "depth": 6, "novelty": 5, "coherence": 8, "citation_accuracy": 7},
                "overall": 6.6, "qa_issues": 0, "qa_passed": True,
                "qa_issues_list": [], "metrics": {}, "success": True, "error": None,
                "benchmark_id": "test_001", "topic": "stable_technical",
            }
            data = run_benchmark([{"id": "test_001", "query": "test", "topic": "stable_technical"}])
        assert data["summary"]["total"] == 1
        assert data["summary"]["passed"] == 1
        assert data["summary"]["avg_overall"] > 0
        assert len(data["results"]) == 1

    def test_run_benchmark_counts_failures(self):
        from run_benchmark import run_benchmark
        with patch("run_benchmark.run_single") as mock_run:
            mock_run.return_value = {
                "success": False, "query": "test", "label": "test",
                "timestamp": "now", "duration_ms": 100, "word_count": 0,
                "sub_questions": 0, "sources": 0, "citation_count": 0,
                "scores": {"relevance": 0, "depth": 0, "novelty": 0, "coherence": 0, "citation_accuracy": 0},
                "overall": 0, "qa_issues": 999, "qa_passed": False,
                "qa_issues_list": ["Error"], "metrics": {}, "success": False,
                "error": "Something broke", "benchmark_id": "fail_001", "topic": "stable_technical",
            }
            data = run_benchmark([{"id": "fail_001", "query": "test", "topic": "stable_technical"}])
        assert data["summary"]["failed"] == 1
        assert data["summary"]["passed"] == 0

    def test_run_benchmark_aggregates_scores(self):
        from run_benchmark import run_benchmark
        with patch("run_benchmark.run_single") as mock_run:
            mock_run.return_value = {
                "success": True, "query": "test", "label": "test",
                "timestamp": "now", "duration_ms": 100, "word_count": 500,
                "sub_questions": 2, "sources": 3, "citation_count": 5,
                "scores": {"relevance": 8.0, "depth": 7.0, "novelty": 6.0, "coherence": 9.0, "citation_accuracy": 8.0},
                "overall": 7.6, "qa_issues": 0, "qa_passed": True,
                "qa_issues_list": [], "metrics": {}, "success": True, "error": None,
                "benchmark_id": "test_001", "topic": "stable_technical",
            }
            data = run_benchmark([{"id": "test_001", "query": "test", "topic": "stable_technical"}])
        assert data["summary"]["avg_scores"]["relevance"] == 8.0
        assert data["summary"]["avg_overall"] == 7.6

    def test_results_serialize_to_json(self):
        from run_benchmark import run_benchmark
        with patch("run_benchmark.run_single") as mock_run:
            mock_run.return_value = {
                "success": True, "query": "test", "label": "test",
                "timestamp": "now", "duration_ms": 100, "word_count": 500,
                "sub_questions": 2, "sources": 3, "citation_count": 5,
                "scores": {"relevance": 7, "depth": 6, "novelty": 5, "coherence": 8, "citation_accuracy": 7},
                "overall": 6.6, "qa_issues": 0, "qa_passed": True,
                "qa_issues_list": [], "metrics": {}, "success": True, "error": None,
                "benchmark_id": "t1", "topic": "stable_technical",
            }
            data = run_benchmark([{"id": "t1", "query": "test", "topic": "stable_technical"}])
        dumped = json.dumps(data)
        reloaded = json.loads(dumped)
        assert reloaded["summary"]["total"] == 1

    def test_print_report_does_not_crash(self, capsys):
        from run_benchmark import run_benchmark, print_report
        with patch("run_benchmark.run_single") as mock_run:
            mock_run.return_value = {
                "success": True, "query": "test", "label": "test",
                "timestamp": "now", "duration_ms": 100, "word_count": 500,
                "sub_questions": 2, "sources": 3, "citation_count": 5,
                "scores": {"relevance": 7, "depth": 6, "novelty": 5, "coherence": 8, "citation_accuracy": 7},
                "overall": 6.6, "qa_issues": 0, "qa_passed": True,
                "qa_issues_list": [], "metrics": {}, "success": True, "error": None,
                "benchmark_id": "t1", "topic": "stable_technical",
            }
            data = run_benchmark([{"id": "t1", "query": "test", "topic": "stable_technical"}])
        print_report(data)
        captured = capsys.readouterr()
        assert "BENCHMARK RESULTS" in captured.out


class TestComparison:
    def test_compare_runs_produces_deltas(self, tmp_path):
        from run_benchmark import run_benchmark, compare_runs
        baseline = {
            "summary": {"avg_scores": {"relevance": 6.0, "depth": 5.0, "novelty": 4.0, "coherence": 7.0, "citation_accuracy": 6.0}, "avg_overall": 5.6, "total_qa_issues": 10},
            "results": [], "config": {},
            "timestamp": "2024-01-01"
        }
        current = {
            "summary": {"avg_scores": {"relevance": 7.0, "depth": 6.0, "novelty": 5.0, "coherence": 8.0, "citation_accuracy": 7.0}, "avg_overall": 6.6, "total_qa_issues": 5},
            "results": [], "config": {},
            "timestamp": "2024-06-01"
        }
        baseline_path = tmp_path / "baseline.json"
        with open(baseline_path, "w") as f:
            json.dump(baseline, f)
        comparison = compare_runs(str(baseline_path), current)
        assert "baseline" in comparison
        assert "deltas" in comparison
        assert comparison["deltas"]["relevance"]["delta"] == 1.0
        assert comparison["overall_delta"] == 1.0
        assert comparison["qa_issues_delta"] == 5

    def test_compare_shows_regression(self, tmp_path):
        from run_benchmark import compare_runs
        baseline = {
            "summary": {"avg_scores": {"relevance": 7.0, "depth": 6.0, "novelty": 5.0, "coherence": 8.0, "citation_accuracy": 7.0}, "avg_overall": 6.6, "total_qa_issues": 2},
            "results": [], "config": {},
            "timestamp": "2024-01-01"
        }
        current = {
            "summary": {"avg_scores": {"relevance": 5.0, "depth": 4.0, "novelty": 3.0, "coherence": 6.0, "citation_accuracy": 5.0}, "avg_overall": 4.6, "total_qa_issues": 15},
            "results": [], "config": {},
            "timestamp": "2024-06-01"
        }
        baseline_path = tmp_path / "baseline.json"
        with open(baseline_path, "w") as f:
            json.dump(baseline, f)
        comparison = compare_runs(str(baseline_path), current)
        assert comparison["overall_delta"] == -2.0
        assert comparison["qa_issues_delta"] == -13

    def test_compare_no_change(self, tmp_path):
        from run_benchmark import compare_runs
        data = {
            "summary": {"avg_scores": {"relevance": 6.0, "depth": 5.0, "novelty": 4.0, "coherence": 7.0, "citation_accuracy": 6.0}, "avg_overall": 5.6, "total_qa_issues": 5},
            "results": [], "config": {},
            "timestamp": "2024-01-01"
        }
        baseline_path = tmp_path / "baseline.json"
        with open(baseline_path, "w") as f:
            json.dump(data, f)
        comparison = compare_runs(str(baseline_path), data)
        assert comparison["overall_delta"] == 0.0
        assert comparison["qa_issues_delta"] == 0


class TestCLI:
    def test_main_with_quick_flag(self):
        from run_benchmark import main
        with patch("run_benchmark.run_benchmark") as mock_bench:
            mock_bench.return_value = {
                "summary": {"total": 8, "passed": 8, "failed": 0, "avg_scores": {}, "avg_overall": 6.5, "avg_duration_ms": 500, "avg_word_count": 1000, "avg_sources": 5, "avg_qa_issues": 0, "total_qa_issues": 0, "total_passed_qa": 8},
                "results": [{"success": True, "benchmark_id": "t1", "overall": 6.5, "qa_issues": 0, "word_count": 1000, "sources": 5, "duration_ms": 500, "scores": {}, "query": "test", "label": "test", "timestamp": "now", "sub_questions": 2, "citation_count": 3, "qa_passed": True, "qa_issues_list": [], "metrics": {}, "success": True, "error": None, "topic": "stable_technical"}],
                "config": {},
                "timestamp": "now",
            }
            with patch("sys.argv", ["run_benchmark.py", "--quick"]):
                result = main()
            assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
