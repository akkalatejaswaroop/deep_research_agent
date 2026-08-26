from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

c = canvas.Canvas(os.path.join(os.environ.get('TEMP', '/tmp'), 'new_version_information.pdf'), pagesize=letter)
width, height = letter

# Title
c.setFont('Helvetica-Bold', 16)
c.drawString(50, height - 50, 'Deep Research Agent - 21-Agent Upgrade')
c.setFont('Helvetica', 12)
c.drawString(50, height - 80, 'Production-Ready Enhancement Report')

# Section: Current Agents
c.setFont('Helvetica-Bold', 14)
c.drawString(50, height - 120, 'Current Agent Framework (21 Agents)')

c.setFont('Helvetica', 9)
y = height - 160

# Agent categories and details
agents_info = [
    ('A. Core Pipeline Agents (7)', [
        ('1. Query Decomposer', 'Breaks complex queries into optimal sub-questions using phi3:mini; conserves LLM budget; generates 8-12 sub-questions'),
        ('2. Research Orchestrator', 'Coordinates multi-strategy search across arXiv/DuckDuckGo/Wikipedia/PixelRAG; manages search budget and iterations; tracks search_iterations counter'),
        ('3. Multi-Source Scraper', '4-tier fallback: Trafilatura -> BS4 -> Jina Reader -> Playwright; SQLite page cache (scraper_cache.db); anti-blocking rotation'),
        ('4. Domain Intelligence', 'Live domain credibility scoring; maintains dynamic blocklist; updates SOURCE_DOWNWEIGHT_DOMAINS automatically; credibility tiers primary/academic/vendor_blog/seo'),
        ('5. Citation Verifier', 'Cross-checks numeric claims + entity verification via _cross_check_numeric_claims + _verify_entity_names; flags unverified claims for re-search; generates Evidence Verification Notes section'),
        ('6. Quality Scorer', 'Computes 5-dimension scores (relevance, depth, novelty, coherence, citation_accuracy) via real_quality_scorer.compute_quality_scores(); LLM judge (phi3:mini) or heuristic fallback; overall weighted average; regenerates if overall < 7/10'),
        ('7. Coherence Auditor', 'Analyzes heading hierarchy (H1/H2/H3 count); transition density; list item ratio; summary/ref presence; assigns coherence score 0-10; controls flow based on score thresholds')
    ]),
    ('B. Enhancement Agents (8)', [
        ('8. Lesson Learner', 'Extracts lessons from evaluator output; stores to Supabase knowledge_base + global KG; feeds back to planner_node via prior_lessons; enables auto-improvement across sessions'),
        ('9. Gap Analyzer', 'Identifies missing topics by comparing covered vs. missing topics; generates new sub-questions based on gap type; controls gap_detector loop continuation (max 3 iterations)'),
        ('10. Repetition Detector', 'Detects near-duplicate sections via _cross_section_duplication_check (similarity >= 0.3); triggers source diversification when redundancy > threshold; prevents redundant content'),
        ('11. Tone & Style Adjuster', 'Checks brand voice compliance; adjusts formality level (academic/industry/general); optimizes for target audience; ensures consistent voice across reports'),
        ('12. Fact Checker', 'Verifies all factual claims in report; generates "Evidence Verification Notes" section listing unverified claims; integrates with _cross_check_numeric_claims and _verify_entity_names'),
        ('13. Source Diversifier', 'When redundancy detected (repetition_detector), searches alternative domains and sources; prevents same content from different URLs; improves source triangulation'),
        ('14. Export Specialist', 'Generates final output in quality-tiered formats: PDF (formatted), Markdown (raw data), JSON (structured); quality levels: fast (300s), thorough (540s), premium (with LLM judge)'),
        ('15. Trend Analyzer', 'Detects emerging topics via query modifiers (trending:, latest:, current:); Google Trends + Reddit API integration (when available); auto-prefixes queries with trending indicators')
    ]),
    ('C. Infrastructure Agents (6)', [
        ('16. Redis Cache Agent', 'Multi-level caching: Redis (1h TTL preferred) -> File (backend_cache.json, 24h) -> Memory fallback; automatic TTL expiration; cache warm-up on startup; max 100 entries; cleanup of expired entries'),
        ('17. Model Router', 'Dynamic model selection per task: phi3:mini for planning (30s timeout), qwen2.5:3b for synthesis (120s timeout); per-stage timeouts in _MODEL_TIMEOUT; _select_model_for_task() routes based on task keywords; 50% LLM cost reduction'),
        ('18. Session Manager', 'Persists session state every 30s to Redis; enables true background execution via Celery; checkpoint/restore support for interruptible research; resume_research_graph task'),
        ('19. Monitoring Agent', 'Prometheus metrics (REQUESTS_TOTAL, LATENCY_HISTOGRAM); LangSmith tracing; per-node timing; error rate alerts; /api/v1/agents/status endpoint; performance dashboard'),
        ('20. Scheduler Agent', 'POST /api/v1/research/schedule endpoint; supports daily/weekly/monthly frequencies; integrates with Celery Beat; schedule_id generation; next_run calculation; user-triggered automations'),
        ('21. Auto-Continue Agent', 'Checks gap_iteration < max_gaps; if gaps exist, triggers research_orchestrator node with new queries based on missing_topics; updates session state; seamless user experience for gap resolution')
    ])
]

for category, agents in agents_info:
    c.setFont('Helvetica-Bold', 11)
    c.drawString(50, y, category)
    y -= 25
    c.setFont('Helvetica', 8)
    for agent_name, agent_desc in agents:
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(55, y, f'{agent_name}: {agent_desc}')
        y -= 18

c.save()
print(f'PDF created at {os.path.join(os.environ.get("TEMP", "/tmp"), "new_version_information.pdf")}')