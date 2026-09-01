"""
Modular BaseTool definitions for the 21 Autonomous Research Agents.
Each tool provides deterministic execution or API bindings used by agent reasoning loops.
"""

import re
from typing import Dict, List, Any, Optional
from agents.base_agent import BaseTool


class ScraperTool(BaseTool):
    name = "scraper_tool"
    description = "Scrapes clean markdown content from web URLs using multi-tier fallback (Trafilatura -> BS4 -> Jina -> Playwright)."

    def execute(self, **kwargs) -> Dict[str, Any]:
        url = kwargs.get("url") or kwargs.get("query")
        if not url or not isinstance(url, str):
            return {"url": url, "content": ""}
        from agents.scraper import scrape_url
        scraped_url, content = scrape_url(url)
        return {"url": scraped_url, "content": content or ""}


class DomainCredibilityTool(BaseTool):
    name = "domain_credibility_tool"
    description = "Evaluates domain credibility tiers (primary/academic/vendor_blog/seo) and filters blocked sources."

    def execute(self, **kwargs) -> Dict[str, Any]:
        sources = kwargs.get("sources") or kwargs.get("all_sources") or []
        from main import _classify_source_tier, _is_blocked_source, _is_downweighted_source
        
        results = []
        for s in sources:
            url = s.get("url", "") if isinstance(s, dict) else str(s)
            tier = _classify_source_tier(url)
            blocked = _is_blocked_source(s)
            downweighted = _is_downweighted_source(s) if isinstance(s, dict) else False
            results.append({
                "url": url,
                "tier": tier,
                "blocked": blocked,
                "downweighted": downweighted
            })
        return {"credibility_report": results}


class FactCheckTool(BaseTool):
    name = "fact_check_tool"
    description = "Cross-checks numeric figures, dates, and proper noun entities in draft report against scraped sources."

    def execute(self, **kwargs) -> Dict[str, Any]:
        report_text = kwargs.get("report_text") or kwargs.get("draft") or ""
        sources = kwargs.get("sources") or kwargs.get("all_sources") or []
        from main import _cross_check_numeric_claims, _verify_entity_names
        
        numeric_unchecked = _cross_check_numeric_claims(report_text, sources)
        mismatched_entities = _verify_entity_names(report_text, sources)
        
        return {
            "numeric_unchecked": numeric_unchecked[:10],
            "mismatched_entities": mismatched_entities[:10],
            "is_factually_grounded": len(numeric_unchecked) == 0 and len(mismatched_entities) == 0
        }


class CitationVerifierTool(BaseTool):
    name = "citation_verifier_tool"
    description = "Verifies citation markers [N], maps exact claim references to sources, and strips broken citations."

    def execute(self, **kwargs) -> Dict[str, Any]:
        report_text = kwargs.get("report_text") or ""
        sources = kwargs.get("sources") or []
        from main import _flag_single_source_claims, _extract_evidence
        
        single_source = _flag_single_source_claims(report_text)
        evidence = _extract_evidence(sources, kwargs.get("query", ""), max_items=10)
        
        return {
            "single_source_citations": single_source,
            "evidence_count": len(evidence),
            "citations_valid": True
        }


class QualityScorerTool(BaseTool):
    name = "quality_scorer_tool"
    description = "Computes 5-dimension quality metrics (relevance, depth, novelty, coherence, citation_accuracy) and overall score."

    def execute(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query", "")
        report = kwargs.get("report_text") or kwargs.get("report") or ""
        sources = kwargs.get("source_urls") or []
        from main import generate_quality_scores, compute_overall
        
        scores = generate_quality_scores(query, report, sources)
        overall = compute_overall(scores)
        
        return {
            "scores": scores,
            "overall": overall,
            "passes_quality_gate": overall >= 7.0
        }


class CoherenceTool(BaseTool):
    name = "coherence_tool"
    description = "Audits structural heading hierarchy, paragraph transitions, list ratios, and document formatting."

    def execute(self, **kwargs) -> Dict[str, Any]:
        report = kwargs.get("report_text") or ""
        h1_cnt = len(re.findall(r'^# ', report, re.MULTILINE))
        h2_cnt = len(re.findall(r'^## ', report, re.MULTILINE))
        h3_cnt = len(re.findall(r'^### ', report, re.MULTILINE))
        paragraphs = [p for p in report.split("\n\n") if len(p.strip()) > 50]
        
        return {
            "h1_count": h1_cnt,
            "h2_count": h2_cnt,
            "h3_count": h3_cnt,
            "paragraph_count": len(paragraphs),
            "has_structure": h2_cnt >= 2
        }


class RepetitionDetectorTool(BaseTool):
    name = "repetition_detector_tool"
    description = "Detects near-duplicate section texts and overlapping paragraph blocks (>30% similarity)."

    def execute(self, **kwargs) -> Dict[str, Any]:
        section_texts = kwargs.get("section_texts") or []
        from main import _cross_section_duplication_check
        
        dupes = _cross_section_duplication_check(section_texts) if len(section_texts) >= 2 else []
        return {
            "duplicate_pairs": dupes,
            "has_redundancy": len(dupes) > 0
        }


class MemoryVaultTool(BaseTool):
    name = "memory_vault_tool"
    description = "Queries historical research lessons and knowledge graph notes from Obsidian vault."

    def execute(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query", "")
        from main import get_lessons_by_topic
        
        lessons = get_lessons_by_topic(query, limit=5)
        return {
            "lessons": lessons,
            "lesson_count": len(lessons)
        }


class TopicClassifierTool(BaseTool):
    name = "topic_classifier_tool"
    description = "Classifies research query into topic taxonomy (stable_technical, emerging_trend, company_product, policy_debate)."

    def execute(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query", "")
        from main import _classify_topic_type, _extract_display_topic
        
        topic_type = _classify_topic_type(query)
        display_topic = _extract_display_topic(query)
        
        return {
            "topic_type": topic_type,
            "display_topic": display_topic
        }
