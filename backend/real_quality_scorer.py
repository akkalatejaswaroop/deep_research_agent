"""
real_quality_scorer.py
-----------------------
Computes REAL quality scores for a research report using an LLM-as-Judge approach.

Dimensions scored (each 0-10):
  - relevance:         How well the report answers the original query
  - depth:             Comprehensiveness and analytical depth
  - novelty:           Insightfulness beyond surface-level facts
  - coherence:         Logical structure and narrative flow
  - citation_accuracy: Degree to which claims are supported by cited sources

The scorer uses Ollama (phi3:mini by default) locally — no external API needed.
Fallback: If Ollama is unavailable, uses heuristic scoring based on measurable
text properties (word count, citation density, section diversity, etc.).
"""

import re
import time
import json
import os
import math
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# LLM-as-Judge (Ollama phi3:mini)
# ---------------------------------------------------------------------------

def _ollama_available() -> bool:
    """Quick check if Ollama is running (2s timeout)."""
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def score_with_llm(query: str, report: str, sources: list) -> Optional[Dict[str, float]]:
    """
    Ask the local LLM to score the report on 5 dimensions.
    Returns a dict like {"relevance": 8.5, "depth": 7.2, ...} or None on failure.
    """
    try:
        import requests

        # Quick health check before attempting scoring
        if not _ollama_available():
            print("[QualityScorer] Ollama not available, skipping LLM scoring")
            return None

        # Truncate report for the prompt to stay within context window
        report_excerpt = report[:4000] if len(report) > 4000 else report
        src_count = len(sources) if sources else 0

        prompt = f"""You are an expert research quality evaluator. Critically evaluate the research report below.

ORIGINAL QUERY: {query}

REPORT (excerpt):
{report_excerpt}

SOURCES CITED: {src_count} sources

Score each dimension from 0 to 10 (decimals allowed, be critical and honest):
- relevance: Does the report directly answer the query with specific evidence?
- depth: Is the analysis comprehensive, multi-layered, and substantive?  
- novelty: Does it provide insights beyond obvious/surface-level information?
- coherence: Is the structure logical, well-organized, and easy to follow?
- citation_accuracy: Are claims well-supported by the cited sources?

SCORING GUIDANCE:
- 9-10: Exceptional, publication-quality
- 7-8: Good, thorough analysis with minor gaps
- 5-6: Adequate but lacks depth or specificity
- 3-4: Superficial, missing key aspects
- 1-2: Poor, largely irrelevant or incoherent

Return ONLY valid JSON (no markdown, no explanation):
{{"relevance": <float>, "depth": <float>, "novelty": <float>, "coherence": <float>, "citation_accuracy": <float>}}"""

        payload = {
            "model": os.getenv("REPORT_MODEL", "qwen2.5:3b"),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 128,
            }
        }

        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            raw = result.get("response", "").strip()
            # Try to extract JSON from the response
            json_match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                scores = {}
                for dim in ["relevance", "depth", "novelty", "coherence", "citation_accuracy"]:
                    val = parsed.get(dim)
                    if isinstance(val, (int, float)):
                        scores[dim] = round(min(10.0, max(0.0, float(val))), 1)
                if len(scores) == 5:
                    return scores

    except Exception as e:
        print(f"[QualityScorer] LLM scoring failed: {e}, falling back to heuristics")

    return None


# ---------------------------------------------------------------------------
# Heuristic Fallback Scorer
# ---------------------------------------------------------------------------

def score_with_heuristics(query: str, report: str, sources: list) -> Dict[str, float]:
    """
    Compute quality scores using measurable heuristics when LLM is unavailable.
    These are grounded in real report properties — NOT hardcoded numbers.
    """
    query_lower = query.lower()
    report_lower = report.lower()

    # === RELEVANCE ===
    # Measure how many query terms appear in the report (split hyphens/punctuation with spaces)
    query_terms = [w for w in re.sub(r'[^a-z0-9 ]', ' ', query_lower).split() if len(w) > 2]
    if query_terms:
        matched = sum(1 for t in query_terms if t in report_lower)
        term_coverage = matched / len(query_terms)
    else:
        term_coverage = 0.5

    # Check if query (minus conversational prefixes) appears verbatim in report
    clean_query = re.sub(r'^(what (is|are|were|was)|explain|research|describe|how (does|do|can|to))\s+', '', query_lower).strip()
    direct_mention = 1 if (clean_query[:30] in report_lower) else 0
    relevance = 4.0 + term_coverage * 4.0 + direct_mention * 2.0
    
    # Penalty for extremely short reports (cannot be a fully relevant report if it is just a stub)
    word_count = len(report.split())
    if word_count < 100:
        relevance -= 3.0
    elif word_count < 300:
        relevance -= 1.5
        
    relevance = round(min(10.0, max(1.0, relevance)), 1)

    # === DEPTH ===
    # Measure word count, section count, avg paragraph length
    word_count = len(report.split())
    section_count = len(re.findall(r'^#{1,3}\s', report, re.MULTILINE))
    paragraphs = [p.strip() for p in report.split('\n\n') if len(p.strip()) > 100]
    avg_para_len = sum(len(p.split()) for p in paragraphs) / max(1, len(paragraphs))

    depth_score = 0.0
    # Word count contribution (cap at 6000 words = max score)
    depth_score += min(4.0, word_count / 1500.0)
    # Section richness
    depth_score += min(2.0, section_count / 5.0)
    # Paragraph depth
    depth_score += min(2.0, avg_para_len / 100.0)
    # Bonus for long reports
    if word_count > 3000:
        depth_score += 1.0
    if word_count > 5000:
        depth_score += 0.5
    depth = round(min(10.0, depth_score), 1)

    # === NOVELTY ===
    # Check for specific data: numbers, percentages, dates, proper nouns
    numbers = len(re.findall(r'\b\d+[\.,]?\d*\s*(%|billion|million|trillion|thousand|year|ms|kb|mb|gb)\b', report_lower))
    dates = len(re.findall(r'\b(19|20)\d{2}\b', report))
    proper_nouns = len(re.findall(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b', report))
    bold_terms = len(re.findall(r'\*\*[^*]+\*\*', report))

    novelty_score = 3.0  # base
    novelty_score += min(2.0, numbers * 0.2)
    novelty_score += min(1.5, dates * 0.15)
    novelty_score += min(1.5, (proper_nouns / max(1, word_count)) * 500)
    novelty_score += min(1.0, bold_terms * 0.05)
    novelty = round(min(10.0, novelty_score), 1)

    # === COHERENCE ===
    # Measure structural markers: headings hierarchy, transitions, lists
    h1_count = len(re.findall(r'^# ', report, re.MULTILINE))
    h2_count = len(re.findall(r'^## ', report, re.MULTILINE))
    h3_count = len(re.findall(r'^### ', report, re.MULTILINE))
    list_items = len(re.findall(r'^\s*[-*•]\s', report, re.MULTILINE))
    has_summary = any(kw in report_lower for kw in ['executive summary', 'summary', 'conclusion', 'overview'])
    has_refs = any(kw in report_lower for kw in ['references', 'sources', 'bibliography', '[^'])

    coherence_score = 3.0
    coherence_score += min(1.5, h2_count * 0.3)
    coherence_score += min(1.0, h3_count * 0.2)
    coherence_score += min(1.0, list_items * 0.05)
    coherence_score += 1.0 if has_summary else 0.0
    coherence_score += 1.0 if has_refs else 0.0
    # Penalty for no structure
    if h2_count == 0 and h3_count == 0:
        coherence_score -= 2.0
    coherence = round(min(10.0, max(0.0, coherence_score)), 1)

    # === CITATION ACCURACY ===
    # Measure citation density and source coverage
    citation_patterns = re.findall(r'\[\^?\d+\]|\[(?:\d+(?:,\s*\d+)*)\]', report)
    inline_citations = len(citation_patterns)
    source_count = len(sources) if sources else 0

    # Count unique citations referenced
    unique_cited = len(set(re.findall(r'\d+', ' '.join(citation_patterns))))

    citation_score = 2.0  # base
    # Citations per 1000 words
    cit_density = (inline_citations / max(1, word_count)) * 1000
    citation_score += min(3.0, cit_density * 0.6)
    # Source count coverage
    citation_score += min(2.5, source_count * 0.07)
    # Unique references used
    citation_score += min(1.5, unique_cited * 0.1)
    # Has reference section
    citation_score += 0.5 if has_refs else 0.0
    citation_accuracy = round(min(10.0, citation_score), 1)

    return {
        "relevance": relevance,
        "depth": depth,
        "novelty": novelty,
        "coherence": coherence,
        "citation_accuracy": citation_accuracy,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_quality_scores(
    query: str,
    report: str,
    sources: list,
    prefer_llm: bool = False
) -> Dict[str, float]:
    """
    Compute real quality scores for a research report.

    1. Tries LLM-as-Judge (phi3:mini via Ollama) if prefer_llm=True
    2. Falls back to heuristic scoring if LLM fails or is unavailable

    Returns a dict with keys: relevance, depth, novelty, coherence, citation_accuracy
    All values are floats in [0, 10].
    """
    t0 = time.time()

    scores = score_with_llm(query, report, sources)
    method = "llm_judge"
    if scores is None:
        scores = score_with_heuristics(query, report, sources)
        method = "heuristic"

    elapsed = round((time.time() - t0) * 1000, 1)
    print(f"[QualityScorer] Scores computed via {method} in {elapsed}ms: {scores}")

    return scores


def compute_overall(scores: Dict[str, float]) -> float:
    """Compute overall quality as weighted average (half-up to 1 decimal)."""
    weights = {
        "relevance": 0.30,
        "depth": 0.25,
        "novelty": 0.15,
        "coherence": 0.15,
        "citation_accuracy": 0.15,
    }
    total = sum(float(scores.get(k, 0) or 0) * w for k, w in weights.items())
    return int(total * 10 + 0.5) / 10.0


# ---------------------------------------------------------------------------
# Verification / Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    print("=" * 60)
    print("QUALITY SCORER VERIFICATION TEST")
    print("=" * 60)

    # Test with a synthetic report
    test_query = "What is quantum computing and how does it work?"
    test_report = """# Deep Research Report: Quantum Computing

**Metadata:** Generated 2025-07-03 · Sources: 38

## Executive Summary

Quantum computing leverages quantum mechanical phenomena—superposition, entanglement, and interference—to perform computations that classical computers cannot efficiently solve. IBM's 1000-qubit Eagle processor [^1] demonstrated error rates below 0.01% in 2023. Google's Sycamore processor achieved quantum advantage in 2019, completing a task in 200 seconds that would take classical supercomputers 10,000 years [^3].

## Key Findings & Thematic Analysis

### Quantum Superposition

Unlike classical bits (0 or 1), quantum bits (qubits) exist in superposition states simultaneously. This enables parallel computation of 2^n states with n qubits [^5]. Recent advances from MIT have shown 99.9% fidelity single-qubit gates [^7].

The leading hardware platforms include superconducting qubits (IBM, Google), trapped ions (IonQ, Honeywell), and photonic systems (PsiQuantum). As of 2024, superconducting systems lead with 1,121 qubits [^12].

### Error Correction

Quantum error correction requires logical qubits encoded across physical qubits. The surface code [^15] requires approximately 1,000 physical qubits per logical qubit. IBM projects fault-tolerant quantum computing by 2033 [^18].

## References

[^1]: IBM Research 2023 - eagle.ibm.com
[^3]: Google AI Quantum Supremacy Paper - nature.com
[^5]: MIT Quantum Lab - mit.edu
[^7]: Physical Review Letters - journals.aps.org
[^12]: IEEE Quantum Week 2024 - ieee.org
[^15]: Fowler et al. Surface Codes - arxiv.org
[^18]: IBM Quantum Roadmap - research.ibm.com
"""

    test_sources = [{"url": f"https://source{i}.com", "domain": f"source{i}.com"} for i in range(35)]

    print("\n1. Testing heuristic scorer...")
    h_scores = score_with_heuristics(test_query, test_report, test_sources)
    print(f"   Heuristic scores: {h_scores}")
    overall_h = compute_overall(h_scores)
    print(f"   Overall (weighted): {overall_h}/10")

    print("\n2. Testing LLM scorer (if Ollama available)...")
    llm_scores = score_with_llm(test_query, test_report, test_sources)
    if llm_scores:
        print(f"   LLM scores: {llm_scores}")
        overall_l = compute_overall(llm_scores)
        print(f"   Overall (weighted): {overall_l}/10")
    else:
        print("   Ollama not available — LLM scoring skipped (heuristic fallback will be used)")

    print("\n3. Full compute_quality_scores test...")
    final = compute_quality_scores(test_query, test_report, test_sources)
    overall = compute_overall(final)
    print(f"   Final scores: {final}")
    print(f"   Overall: {overall}/10")

    # Validation assertions
    print("\n4. Assertions...")
    assert isinstance(final, dict), "Scores must be a dict"
    assert set(final.keys()) == {"relevance", "depth", "novelty", "coherence", "citation_accuracy"}, "All 5 dimensions required"
    for k, v in final.items():
        assert 0 <= v <= 10, f"Score {k}={v} out of [0,10] range"
    assert 0 <= overall <= 10, f"Overall {overall} out of range"
    print("   [OK] All assertions passed!")

    # Test empty/poor report
    print("\n5. Testing edge case: minimal report...")
    poor_scores = compute_quality_scores("AI safety", "AI is important.", [])
    poor_overall = compute_overall(poor_scores)
    print(f"   Poor report scores: {poor_scores}")
    print(f"   Poor report overall: {poor_overall}/10")
    assert poor_overall < overall, "Poor report should score lower than good report"
    print("   [OK] Score ordering correct (good > poor)!")

    print("\n" + "=" * 60)
    print("ALL QUALITY SCORER TESTS PASSED")
    print("=" * 60)
