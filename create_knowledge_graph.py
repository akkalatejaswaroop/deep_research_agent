import json
import os
from datetime import datetime

# Define the 21 agents with their properties
agents = {
    "agents": {
        "total_count": 21,
        "created": datetime.now().isoformat(),
        "description": "21-Agent Deep Research System - Production Upgrade",
        
        "categories": {
            "core_pipeline": {
                "count": 7,
                "description": "Core pipeline agents forming the main research flow",
                "agents": [
                    {
                        "id": 1,
                        "name": "Query Decomposer",
                        "task": "Breaks complex queries into optimal sub-questions using phi3:mini",
                        "task_frequency": "Every research query",
                        "model": "phi3:mini",
                        "output": "sub_questions list",
                        "dependencies": ["query", "topic_type_detection"]
                    },
                    {
                        "id": 2,
                        "name": "Research Orchestrator",
                        "task": "Coordinates multi-strategy search across arXiv/DuckDuckGo/Wikipedia/PixelRAG; manages search budget and iterations; tracks search_iterations counter",
                        "task_frequency": "Every research query",
                        "model": "qwen2.5:3b",
                        "output": "source_urls, scored_chunks",
                        "dependencies": ["sub_queries", "search_budget"]
                    },
                    {
                        "id": 3,
                        "name": "Multi-Source Scraper",
                        "task": "4-tier fallback: Trafilatura -> BS4 -> Jina Reader -> Playwright; SQLite page cache (scraper_cache.db); anti-blocking rotation",
                        "task_frequency": "Every research query",
                        "model": "N/A (deterministic)",
                        "output": "raw_pages, scored_chunks",
                        "dependencies": ["sub_queries", "source_urls"]
                    },
                    {
                        "id": 4,
                        "name": "Domain Intelligence",
                        "task": "Live domain credibility scoring; maintains dynamic blocklist; updates SOURCE_DOWNWEIGHT_DOMAINS automatically; credibility tiers primary/academic/vendor_blog/seo",
                        "task_frequency": "Every research query",
                        "model": "N/A (rule-based)",
                        "output": "source_tiers, blocked_domains",
                        "dependencies": ["source_urls", "cited_report"]
                    },
                    {
                        "id": 5,
                        "name": "Citation Verifier",
                        "task": "Cross-checks numeric claims + entity verification via _cross_check_numeric_claims + _verify_entity_names; flags unverified claims for re-search; generates Evidence Verification Notes section",
                        "task_frequency": "Every research query",
                        "model": "phi3:mini or heuristic",
                        "output": "verified_claims, unverified_list",
                        "dependencies": ["cited_report", "source_urls"]
                    },
                    {
                        "id": 6,
                        "name": "Quality Scorer",
                        "task": "Computes 5-dimension scores (relevance, depth, novelty, coherence, citation_accuracy) via real_quality_scorer.compute_quality_scores(); LLM judge (phi3:mini) or heuristic fallback; overall weighted average; regenerates if overall < 7/10",
                        "task_frequency": "Every research completion",
                        "model": "phi3:mini or heuristic",
                        "output": "scores dict, overall_score",
                        "dependencies": ["cited_report", "source_urls"]
                    },
                    {
                        "id": 7,
                        "name": "Coherence Auditor",
                        "task": "Analyzes heading hierarchy (H1/H2/H3 count); transition density; list item ratio; summary/ref presence; assigns coherence score 0-10; controls flow based on score thresholds",
                        "task_frequency": "Every research completion",
                        "model": "phi3:mini or heuristic",
                        "output": "coherence_score, flow_decision",
                        "dependencies": ["cited_report", "quality_metrics"]
                    }
                ]
            },
            "enhancement_agents": {
                "count": 8,
                "description": "Enhancement agents for quality and automation",
                "agents": [
                    {
                        "id": 8,
                        "name": "Lesson Learner",
                        "task": "Extracts lessons from evaluator output; stores to Supabase knowledge_base + global KG; feeds back to planner_node via prior_lessons; enables auto-improvement across sessions",
                        "task_frequency": "Every research completion",
                        "model": "phi3:mini",
                        "output": "lessons list, prior_lessons update",
                        "dependencies": ["evaluator_output", "prior_lessons"]
                    },
                    {
                        "id": 9,
                        "name": "Gap Analyzer",
                        "task": "Identifies missing topics by comparing covered vs. missing topics; generates new sub-questions; controls gap_detector loop continuation (max 3 iterations)",
                        "task_frequency": "Every research completion with gaps",
                        "model": "phi3:mini",
                        "output": "new_sub_questions, gap_iteration increment",
                        "dependencies": ["quality_metrics", "missing_topics"]
                    },
                    {
                        "id": 10,
                        "name": "Repetition Detector",
                        "task": "Detects near-duplicate sections via _cross_section_duplication_check (similarity >= 0.3); triggers source diversification when redundancy > threshold; prevents redundant content",
                        "task_frequency": "Every research completion",
                        "model": "N/A (deterministic)",
                        "output": "redundancy_score, diversification_trigger",
                        "dependencies": ["cited_report", "source_urls"]
                    },
                    {
                        "id": 11,
                        "name": "Tone & Style Adjuster",
                        "task": "Checks brand voice compliance; adjusts formality level (academic/industry/general); optimizes for target audience; ensures consistent voice across reports",
                        "task_frequency": "Every research completion",
                        "model": "phi3:mini",
                        "output": "tone_adjustment, style_metrics",
                        "dependencies": ["cited_report", "quality_metrics"]
                    },
                    {
                        "id": 12,
                        "name": "Fact Checker",
                        "task": "Verifies all factual claims in report; generates 'Evidence Verification Notes' section listing unverified claims; integrates with _cross_check_numeric_claims and _verify_entity_names",
                        "task_frequency": "Every research completion",
                        "model": "phi3:mini or heuristic",
                        "output": "verification_notes, unverified_claims",
                        "dependencies": ["cited_report", "source_urls"]
                    },
                    {
                        "id": 13,
                        "name": "Source Diversifier",
                        "task": "When redundancy detected (repetition_detector), searches alternative domains and sources; prevents same content from different URLs; improves source triangulation",
                        "task_frequency": "If redundancy detected",
                        "model": "qwen2.5:3b",
                        "output": "new_source_urls, diversification_report",
                        "dependencies": ["repetition_detector", "quality_metrics"]
                    },
                    {
                        "id": 14,
                        "name": "Export Specialist",
                        "task": "Generates final output in quality-tiered formats: PDF (formatted), Markdown (raw data), JSON (raw data); quality levels: fast (300s), thorough (540s), premium (with LLM judge)",
                        "task_frequency": "Every research completion",
                        "model": "N/A (formatting)",
                        "output": "exported_report (PDF/MD/JSON)",
                        "dependencies": ["cited_report", "quality_metrics", "format_preference"]
                    },
                    {
                        "id": 15,
                        "name": "Trend Analyzer",
                        "task": "Detects emerging topics via query modifiers (trending:, latest:, recent:); Google Trends + Reddit API integration (when available); auto-prefixes queries with trending indicators",
                        "task_frequency": "Every research query with trending keywords",
                        "model": "phi3:mini or Google Trends API",
                        "output": "trending_modifier, enhanced_query",
                        "dependencies": ["query", "trending_keywords"]
                    }
                ]
            },
            "infrastructure_agents": {
                "count": 6,
                "description": "Infrastructure agents for system operation",
                "agents": [
                    {
                        "id": 16,
                        "name": "Redis Cache Agent",
                        "task": "Multi-level caching: Redis (1h TTL preferred) -> File (backend_cache.json, 24h) -> Memory fallback; automatic TTL expiration; cache warm-up on startup; max 100 entries; cleanup of expired entries",
                        "task_frequency": "Every research query (check/refresh)",
                        "model": "N/A (cache system)",
                        "output": "cached_result, cache_key",
                        "dependencies": ["query_hash", "cache_config"]
                    },
                    {
                        "id": 17,
                        "name": "Model Router",
                        "task": "Dynamic model selection per task: phi3:mini for planning (30s timeout), qwen2.5:3b for synthesis (120s timeout); per-stage timeouts in _MODEL_TIMEOUT; _select_model_for_task() routes based on task keywords; 50% LLM cost reduction",
                        "task_frequency": "Every LLM call",
                        "model": "Task-dependent: phi3:mini or qwen2.5:3b",
                        "output": "selected_model, model_switch_decision",
                        "dependencies": ["task_description", "model_availability"]
                    },
                    {
                        "id": 18,
                        "name": "Session Manager",
                        "task": "Persists session state every 30s to Redis; enables true background execution via Celery; checkpoint/restore support for interruptible research; resume_research_graph task",
                        "task_frequency": "Every research session",
                        "model": "N/A (system)",
                        "output": "session_id, checkpoint, resume_data",
                        "dependencies": ["query", "depth", "complexity"]
                    },
                    {
                        "id": 19,
                        "name": "Monitoring Agent",
                        "task": "Prometheus metrics (REQUESTS_TOTAL, LATENCY_HISTOGRAM); LangSmith tracing; per-node timing; error rate alerts; /api/v1/agents/status endpoint; performance dashboard",
                        "task_frequency": "Continuous",
                        "model": "N/A (monitoring system)",
                        "output": "metrics_dashboard, error_alerts",
                        "dependencies": ["system_health", "performance_data"]
                    },
                    {
                        "id": 20,
                        "name": "Scheduler Agent",
                        "task": "POST /api/v1/research/schedule endpoint; supports daily/weekly/monthly frequencies; integrates with Celery Beat; schedule_id generation; next_run calculation; user-triggered automations",
                        "task_frequency": "User-initiated",
                        "model": "N/A (scheduling system)",
                        "output": "schedule_id, next_run_time",
                        "dependencies": ["query", "frequency", "trigger_queries"]
                    },
                    {
                        "id": 21,
                        "name": "Auto-Continue Agent",
                        "task": "Checks gap_iteration < max_gaps; if gaps exist, triggers research_orchestrator node with new queries based on missing_topics; updates session state; seamless user experience for gap resolution",
                        "task_frequency": "Every research completion with gaps",
                        "model": "phi3:mini",
                        "output": "new_sub_questions, gap_iteration increment",
                        "dependencies": ["gap_iteration", "missing_topics", "quality_metrics"]
                    }
                ]
            }
        }
    }
}

# Save the knowledge graph
output_path = r"D:\deep_research_agent\agent_knowledge_graph.json"
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(agents, f, indent=2, ensure_ascii=False)

print(f"Knowledge graph created at: {output_path}")
print(f"Total agents: {agents['agents']['total_count']}")
print(f"Categories: {list(agents['agents'].keys())}")