"""
test_metrics_accuracy.py
--------------------------
Comprehensive test suite to verify that all metrics are REAL and ACCURATE.

Tests:
1. Quality scorer (LLM + heuristics) — validates score validity and ordering
2. Timing accuracy — verifies wall-clock timing is used, not fake formulas
3. Token counting — verifies counts are based on actual text, not magic numbers
4. LLM call counting — verifies call counts match section structure
5. Proof-of-improvement — verifies history tracking works across multiple runs
6. End-to-end integration test via the build_comprehensive_report function

Run with:
    cd backend
    python test_metrics_accuracy.py
"""

import sys
import os
import time
import json
import io

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load env vars
from dotenv import load_dotenv
load_dotenv()

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"  {status}  {name}" + (f"\n         {detail}" if detail else ""))
    return condition

def run_metrics_tests():
    # ===========================================================================
    # TEST 1: Quality Scorer Module
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST 1: real_quality_scorer.py — Heuristic Scoring")
    print("="*65)

    try:
        from real_quality_scorer import (
            score_with_heuristics, score_with_llm,
            compute_quality_scores, compute_overall
        )

        GOOD_QUERY = "What are the environmental impacts of lithium-ion battery production?"
        GOOD_REPORT = """
# Deep Research Report: Environmental Impacts of Lithium-Ion Battery Production

**Metadata:** Generated July 2025 · 38 sources consulted

## Executive Summary

Lithium-ion battery production creates significant environmental challenges, particularly in mining lithium [^1], cobalt [^3], and nickel [^5]. Studies from Nature Energy (2023) found that producing 1 kWh of battery capacity generates 60-70 kg CO2e [^7]. However, lifecycle analyses show electric vehicles still emit 50-70% less CO2 than combustion vehicles over their lifetime [^12].

## Key Findings & Thematic Analysis

### Mining and Resource Extraction

Lithium extraction from brine aquifers in Chile's Atacama Desert consumes approximately 2,000 liters of water per kilogram of lithium produced [^15]. This has displaced indigenous communities and reduced local water tables by 5-10 meters since 2000 [^18]. Congo provides 70% of global cobalt, with documented human rights violations in artisanal mining [^21].

The environmental footprint varies significantly by extraction method. Hard-rock mining in Australia generates 15 tonnes of CO2 per tonne of lithium, compared to 5 tonnes for brine extraction [^24]. Novel direct lithium extraction (DLE) technologies could reduce water use by 90% [^27].

### Manufacturing Process Impacts

Battery cell manufacturing requires highly controlled environments consuming 100-200 kWh per kWh of battery capacity produced [^30]. A 100 GWh gigafactory emits approximately 2-3 million tonnes of CO2 annually when powered by the average global grid [^33].

### End-of-Life and Recycling

Only 5% of lithium-ion batteries are currently recycled globally [^35]. Hydrometallurgical recycling recovers 95% of cobalt and 80% of lithium [^36], but requires significant acid and water inputs. New solid-state and sodium-ion alternatives may reduce critical material dependency by 60% [^37].

### Additional Environmental Context & Analysis

Lithium slag disposal represents an emerging challenge. Chemical processing of spodumene concentrate produces large volumes of waste material, which must be carefully managed to avoid leaching of heavy metals [^15]. Furthermore, regional air pollution from mining activities impacts adjacent communities, triggering localized respiratory health concerns.

Gigafactory operations also place strain on local electricity grids. Powering clean rooms and drying rooms requires constant, high-load energy input. Transitioning these facilities to 100% renewable power sources is critical to achieving net-zero manufacturing targets [^30].

Finally, global policy frameworks are beginning to mandate minimum recycled content requirements. The EU Battery Regulation, for instance, sets progressive collection and recovery targets for critical minerals, which aims to drive industrial-scale hydrometallurgical facility deployments over the next decade [^35].

## References

[^1]: USGS Mineral Resources Program - usgs.gov
[^3]: Cobalt Institute Annual Report 2023 - cobaltinstitute.org
[^5]: International Energy Agency Critical Minerals Report - iea.org
[^7]: Nature Energy - Vol. 4, 2023, pp. 446-455 - nature.com
[^12]: Transport & Environment EV Lifecycle Analysis - transportenvironment.org
[^15]: CONICET Water Study Chile - conicet.gov.ar
[^18]: IPBES Biodiversity Assessment - ipbes.net
[^21]: Amnesty International DRC Report - amnesty.org
[^24]: CSIRO Mining Comparison Study - csiro.au
[^27]: Energy & Environmental Science - rsc.org
[^30]: Rocky Mountain Institute Manufacturing Study - rmi.org
[^33]: BloombergNEF Gigafactory Analysis - bnef.com
[^35]: IRENA Recycling Status Report - irena.org
[^36]: Retriev Technologies Hydrometallurgy - retrievtech.com
[^37]: MIT Energy Initiative Report - energy.mit.edu
"""

        POOR_QUERY = "AI"
        POOR_REPORT = "AI is important and many companies use it."

        SOURCES_GOOD = [{"url": f"https://src{i}.org", "domain": f"src{i}.org", "content": "research content " * 20} for i in range(38)]
        SOURCES_POOR = []

        print("\n--- Testing good report heuristics ---")
        good_h = score_with_heuristics(GOOD_QUERY, GOOD_REPORT, SOURCES_GOOD)
        print(f"  Scores: {good_h}")
        overall_good = compute_overall(good_h)
        print(f"  Overall: {overall_good}/10")

        check("Good report has all 5 dimensions",
              set(good_h.keys()) == {"relevance", "depth", "novelty", "coherence", "citation_accuracy"})
        check("All scores in [0,10] range",
              all(0 <= v <= 10 for v in good_h.values()),
              str(good_h))
        check("Good report overall >= 6.0",
              overall_good >= 6.0,
              f"Got {overall_good}/10")

        print("\n--- Testing poor report heuristics ---")
        poor_h = score_with_heuristics(POOR_QUERY, POOR_REPORT, SOURCES_POOR)
        print(f"  Scores: {poor_h}")
        overall_poor = compute_overall(poor_h)
        print(f"  Overall: {overall_poor}/10")

        check("Poor report scores lower than good report",
              overall_poor < overall_good,
              f"Poor={overall_poor} vs Good={overall_good}")
        check("Poor report overall < 6.0",
              overall_poor < 6.0,
              f"Got {overall_poor}/10")

        print("\n--- Testing score differentiates quality levels ---")
        check("Relevance higher in good report",
              good_h["relevance"] > poor_h["relevance"],
              f"Good={good_h['relevance']} vs Poor={poor_h['relevance']}")
        check("Depth higher in good report",
              good_h["depth"] > poor_h["depth"],
              f"Good={good_h['depth']} vs Poor={poor_h['depth']}")
        check("Citation accuracy higher in good report",
              good_h["citation_accuracy"] > poor_h["citation_accuracy"],
              f"Good={good_h['citation_accuracy']} vs Poor={poor_h['citation_accuracy']}")

    except Exception as e:
        print(f"  {FAIL}  Module import failed: {e}")
        results.append(("Quality Scorer Import", False, str(e)))


    # ===========================================================================
    # TEST 2: Weighted Overall Computation
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST 2: compute_overall() — Weighted Average Accuracy")
    print("="*65)

    try:
        from real_quality_scorer import compute_overall

        # Test known values
        test_scores = {"relevance": 8.0, "depth": 7.0, "novelty": 6.0, "coherence": 9.0, "citation_accuracy": 5.0}
        # Expected: 8.0*0.30 + 7.0*0.25 + 6.0*0.15 + 9.0*0.15 + 5.0*0.15
        # = 2.40 + 1.75 + 0.90 + 1.35 + 0.75 = 7.15 → half-up to 1dp = 7.2
        expected = 7.2
        got = compute_overall(test_scores)
        check("Weighted average is correct",
              abs(got - expected) < 0.05,
              f"Expected ~{expected}, got {got}")

        # Edge cases
        perfect = {"relevance": 10, "depth": 10, "novelty": 10, "coherence": 10, "citation_accuracy": 10}
        check("Perfect scores give 10.0", compute_overall(perfect) == 10.0)

        zero = {"relevance": 0, "depth": 0, "novelty": 0, "coherence": 0, "citation_accuracy": 0}
        check("Zero scores give 0.0", compute_overall(zero) == 0.0)

    except Exception as e:
        print(f"  {FAIL}  {e}")
        results.append(("compute_overall", False, str(e)))


    # ===========================================================================
    # TEST 3: Real Timing in build_comprehensive_report
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST 3: Real Wall-Clock Timing Measurement")
    print("="*65)

    result = None
    try:
        # Mock web search + LLM so timing tests stay local and fast
        import main as main_mod
        import unittest.mock as mock

        MOCK_SOURCES = [
            {
                "url": f"https://example{i}.com/research",
                "title": f"Research Article {i} on AI",
                "domain": f"example{i}.com",
                "content": "This is detailed research content about artificial intelligence and machine learning. " * 15
            }
            for i in range(38)
        ]

        def mock_fetch(*args, **kwargs):
            time.sleep(0.010)
            return MOCK_SOURCES

        def mock_llm(prompt, system_prompt=""):
            # Minimal structured responses so the pipeline stays deterministic
            if "sub_questions" in prompt.lower() or "sub-questions" in prompt.lower() or "Generate exactly" in prompt:
                return json.dumps({"sub_questions": [
                    "What is the historical background of AI?",
                    "What are key modern developments in AI?",
                    "What challenges and future directions exist for AI?",
                ]})
            return (
                "Artificial intelligence has evolved through several generations of research [1]. "
                "Modern systems combine statistical learning with large-scale data [2]. "
                "Open challenges include reliability, evaluation, and deployment constraints [3]."
            )

        with mock.patch.object(main_mod, 'search_all_sources', side_effect=mock_fetch), \
             mock.patch.object(main_mod, 'call_llm', side_effect=mock_llm):
            t_before = time.perf_counter()
            result = main_mod.build_report_autonomously(
                "artificial intelligence history",
                depth=1,
                complexity=1,
                target_sub_questions=3,
            )
            t_after = time.perf_counter()

        actual_elapsed_ms = (t_after - t_before) * 1000
        reported_ms = result["_metrics"]["execution"]["total_duration_ms"]

        print(f"  Actual wall time: {actual_elapsed_ms:.1f}ms")
        print(f"  Reported time:    {reported_ms}ms")
        print(f"  Difference:       {abs(actual_elapsed_ms - reported_ms):.1f}ms")

        check("Reported time is within 20% of actual time",
              abs(actual_elapsed_ms - reported_ms) < max(50.0, actual_elapsed_ms * 0.20),
              f"Actual={actual_elapsed_ms:.0f}ms, Reported={reported_ms}ms")
        check("Reported time > 0",
              reported_ms > 0)
        check("Reported time is NOT a round number (not fake)",
              reported_ms % 1000 != 0,
              f"Got {reported_ms}ms (round 1000s would be fake)")

        # Verify node timings are all positive
        node_timings = result["_metrics"]["execution"]["node_timings_ms"]
        print(f"\n  Node timings: {node_timings}")
        check("All node timings are >= 0",
              all(v >= 0 for v in node_timings.values()),
              str(node_timings))
        check("Searcher timing > 0 (real fetch time)",
              node_timings.get("searcher", 0) > 0)
        check("Planner timing > 0 (real section build time)",
              node_timings.get("planner", 0) > 0)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  {FAIL}  {e}")
        results.append(("Timing Test", False, str(e)))


    # ===========================================================================
    # TEST 4: Token Count Accuracy
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST 4: Token Count Accuracy")
    print("="*65)

    try:
        if result is None:
            raise RuntimeError("No result from timing test — cannot validate tokens")

        metrics = result["_metrics"]
        efficiency = metrics["efficiency"]

        input_tokens = efficiency["estimated_input_tokens"]
        output_tokens = efficiency["estimated_output_tokens"]
        report_len = len(result["report"])

        print(f"  Report length:          {report_len} chars")
        print(f"  Estimated output tokens: {output_tokens}")
        print(f"  Estimated input tokens:  {input_tokens}")
        print(f"  Token ratio (chars/tok): {report_len/max(1,output_tokens):.1f}")

        check("Output tokens ~ report_chars/4 (±50%)",
              0.5 <= (output_tokens * 4 / max(1, report_len)) <= 2.0,
              f"Got ratio {report_len/max(1,output_tokens):.1f} chars/token (expected ~4)")
        check("Input tokens > output tokens (report always shorter than inputs)",
              input_tokens > output_tokens,
              f"Input={input_tokens}, Output={output_tokens}")
        check("Input tokens is NOT exactly 85000 (old hardcoded value)",
              input_tokens != 85000,
              f"Got {input_tokens}")
        check("Output tokens is NOT exactly 18000 (old hardcoded value)",
              output_tokens != 18000,
              f"Got {output_tokens}")

    except Exception as e:
        print(f"  {FAIL}  {e}")
        results.append(("Token Count", False, str(e)))


    # ===========================================================================
    # TEST 5: LLM Call Count Accuracy
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST 5: LLM Call Count Accuracy")
    print("="*65)

    try:
        if result is None:
            raise RuntimeError("No result from timing test — cannot validate LLM calls")

        metrics = result["_metrics"]
        efficiency = metrics["efficiency"]
        breadth = metrics["breadth"]

        total_calls = efficiency["total_llm_calls"]
        per_stage = efficiency["llm_calls_per_stage"]
        sub_q_count = breadth["sub_questions"]

        print(f"  Sub-questions: {sub_q_count}")
        print(f"  LLM calls per stage: {per_stage}")
        print(f"  Total LLM calls: {total_calls}")

        check("Total calls = sum of per-stage calls",
              total_calls == sum(per_stage.values()),
              f"Sum={sum(per_stage.values())}, Total={total_calls}")
        check("Synthesis calls == sub_questions count",
              per_stage.get("synthesis", 0) == sub_q_count,
              f"Synthesis={per_stage.get('synthesis')}, sub_q={sub_q_count}")
        check("Filter calls == sub_questions count",
              per_stage.get("filter", 0) == sub_q_count,
              f"Filter={per_stage.get('filter')}, sub_q={sub_q_count}")
        check("Total calls is NOT old hardcoded formula (4 + sub_q*2)",
              total_calls != (4 + sub_q_count * 2 + 0),
              f"Got {total_calls}, old formula would give {4 + sub_q_count * 2}")
        check("All 7 pipeline stages have call counts",
              all(s in per_stage for s in ["planner","filter","synthesis","gap_detector","citation_mapper","report_node_id","evaluator"]),
              str(list(per_stage.keys())))

    except Exception as e:
        print(f"  {FAIL}  {e}")
        results.append(("LLM Call Count", False, str(e)))


    # ===========================================================================
    # TEST 6: Quality Score Range and Non-Hardcoded Values
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST 6: Quality Scores — Non-Hardcoded, In-Range, Plausible")
    print("="*65)

    try:
        if result is None:
            raise RuntimeError("No result from timing test — cannot validate quality scores")

        quality = result["_metrics"]["quality"]
        scores = quality["scores"]
        overall = quality["overall"]

        print(f"  Scores: {scores}")
        print(f"  Overall: {overall}/10")

        check("Has all 5 quality dimensions",
              set(scores.keys()) == {"relevance", "depth", "novelty", "coherence", "citation_accuracy"})
        check("Overall is between 0 and 10",
              0 <= overall <= 10)
        check("All dimension scores in [0, 10]",
              all(0 <= v <= 10 for v in scores.values()))

        OLD_HARDCODED_SCORES = {"relevance": 9, "depth": 9, "novelty": 8, "coherence": 9, "citation_accuracy": 9}
        check("Scores are NOT the old hardcoded values",
              scores != OLD_HARDCODED_SCORES,
              f"Actual scores: {scores}")

        check("Overall is NOT 8.8 (old hardcoded formula result for depth=1,complexity=1)",
              overall != 8.8,
              f"Got {overall}")

        # Scores should be reasonable for a comprehensive report on a well-known topic
        check("Overall quality >= 5.0 (reasonable minimum for structured report)",
              overall >= 5.0,
              f"Got {overall}/10")

    except Exception as e:
        print(f"  {FAIL}  {e}")
        results.append(("Quality Scores", False, str(e)))


    # ===========================================================================
    # TEST 7: Proof of Improvement — History Tracking
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST 7: Proof of Improvement — Cross-Run History Tracking")
    print("="*65)

    try:
        TEST_QUERY = "test query for history tracking verification abc123"
        # Clear any prior history for this topic
        topic_key = main_mod._normalize_topic(TEST_QUERY)
        main_mod._quality_history.pop(topic_key, None)

        with mock.patch.object(main_mod, 'search_all_sources', return_value=MOCK_SOURCES), \
             mock.patch.object(main_mod, 'call_llm', side_effect=mock_llm):
            # First run — should have no history
            r1 = main_mod.build_report_autonomously(TEST_QUERY, depth=1, complexity=1, target_sub_questions=3)
            poi1 = r1["_metrics"]["proof_of_improvement"]
            print(f"\n  Run 1 proof_of_improvement: {json.dumps(poi1, indent=4)}")

            check("Run 1 has NO prior history",
                  "history_count" not in poi1 or poi1.get("history_count", 0) == 0,
                  f"history_count={poi1.get('history_count', 'not set')}")

            overall1 = r1["_metrics"]["quality"]["overall"]

            # Second run on same topic — should see run 1 as history
            r2 = main_mod.build_report_autonomously(TEST_QUERY, depth=1, complexity=1, target_sub_questions=3)
            poi2 = r2["_metrics"]["proof_of_improvement"]
            print(f"\n  Run 2 proof_of_improvement: {json.dumps(poi2, indent=4)}")
            overall2 = r2["_metrics"]["quality"]["overall"]

            check("Run 2 HAS history_count = 1",
                  poi2.get("history_count", 0) == 1,
                  f"history_count={poi2.get('history_count')}")
            check("Run 2 average_prior_quality = Run 1 overall",
                  abs(poi2.get("average_prior_quality", -99) - overall1) < 0.01,
                  f"Expected {overall1}, got {poi2.get('average_prior_quality')}")
            check("Run 2 quality_delta = Run2 - Run1",
                  abs(poi2.get("quality_delta", -99) - (overall2 - overall1)) < 0.05,
                  f"Expected {overall2 - overall1:.1f}, got {poi2.get('quality_delta')}")

            # Third run
            r3 = main_mod.build_report_autonomously(TEST_QUERY, depth=1, complexity=1, target_sub_questions=3)
            poi3 = r3["_metrics"]["proof_of_improvement"]
            check("Run 3 HAS history_count = 2",
                  poi3.get("history_count", 0) == 2,
                  f"history_count={poi3.get('history_count')}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  {FAIL}  {e}")
        results.append(("Proof of Improvement", False, str(e)))


    # ===========================================================================
    # TEST 8: Prior Lessons from Real Knowledge Base
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST 8: Prior Lessons from Real In-Memory Knowledge")
    print("="*65)

    try:
        from db import in_memory_knowledge

        # Inject a test lesson
        test_lesson = {
            "content": "Always verify source credibility before including in reports.",
            "content_hash": "testhash001",
            "source": "Test",
            "relevance_tags": ["lesson_learned"],
            "embedding": [0.0] * 768,
            "created_at": "2025-07-03T12:00:00"
        }
        in_memory_knowledge.append(test_lesson)

        with mock.patch.object(main_mod, 'search_all_sources', return_value=MOCK_SOURCES), \
             mock.patch.object(main_mod, 'call_llm', side_effect=mock_llm):
            r_lesson = main_mod.build_report_autonomously(
                "test lesson injection xyz", depth=1, complexity=1, target_sub_questions=3
            )

        poi = r_lesson["_metrics"]["proof_of_improvement"]
        print(f"  prior_lessons_count: {poi.get('prior_lessons_count')}")
        print(f"  prior_lessons: {poi.get('prior_lessons', [])[:2]}")

        check("prior_lessons_count > 0 when lessons exist",
              poi.get("prior_lessons_count", 0) > 0,
              f"Got {poi.get('prior_lessons_count')}")
        check("prior_lessons is not hardcoded list",
              poi.get("prior_lessons", ["HARDCODED"]) != [
                  "Classify queries to generate custom report structures matching topic requirements.",
                  "Ensure minimum 35 sources covering academic, industry, and policy domains.",
                  "Verify live search citations return real, active search links for high query relevance.",
              ],
              "Old hardcoded lessons detected!")
        check("Actual lesson content found in prior_lessons",
              any("verify source" in l.lower() for l in poi.get("prior_lessons", [])),
              f"Lessons: {poi.get('prior_lessons', [])}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  {FAIL}  {e}")
        results.append(("Prior Lessons", False, str(e)))


    # ===========================================================================
    # SUMMARY
    # ===========================================================================
    print("\n" + "="*65)
    print("TEST SUMMARY")
    print("="*65)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    total = len(results)

    print(f"\n  Total:  {total}")
    print(f"  Passed: {passed} [OK]")
    print(f"  Failed: {failed} [FAILED]")
    print()

    if failed > 0:
        print("FAILED TESTS:")
        for name, ok, detail in results:
            if not ok:
                print(f"  [FAIL] {name}")
                if detail:
                    print(f"     {detail}")
        print()

    if failed == 0:
        print("ALL TESTS PASSED! Metrics are real, accurate, and verified.")
    else:
        print(f"WARNING: {failed} tests failed. Review above for details.")

    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    run_metrics_tests()
