"""
21 ReAct Autonomous Agent Fleet.
Instantiates all 21 specialized agents with dedicated roles, tool bindings, and reasoning loops.
"""

import logging
from typing import Dict, List, Any
from agents.base_agent import BaseResearchAgent
from agents.tools import (
    ScraperTool,
    DomainCredibilityTool,
    FactCheckTool,
    CitationVerifierTool,
    QualityScorerTool,
    CoherenceTool,
    RepetitionDetectorTool,
    MemoryVaultTool,
    TopicClassifierTool
)

logger = logging.getLogger("rex.fleet")


class AgentFleet:
    """Registry and manager for the 21 Autonomous Research Agents."""
    def __init__(self):
        self.agents: Dict[int, BaseResearchAgent] = {}
        self._initialize_fleet()

    def _initialize_fleet(self):
        # 1. Query Decomposer Agent
        self.agents[1] = BaseResearchAgent(
            name="Query Decomposer",
            role="Planning & Taxonomy",
            system_prompt="Decompose research queries into semantically distinct, specific sub-questions.",
            model_name="phi3:mini",
            tools=[TopicClassifierTool(), MemoryVaultTool()]
        )

        # 2. Research Orchestrator Agent
        self.agents[2] = BaseResearchAgent(
            name="Research Orchestrator",
            role="Research Coordination",
            system_prompt="Coordinate parallel search execution across domain tracks and manage search budgets.",
            model_name="qwen2.5:3b",
            tools=[TopicClassifierTool()]
        )

        # 3. Multi-Source Scraper Agent
        self.agents[3] = BaseResearchAgent(
            name="Multi-Source Scraper",
            role="Web Extraction",
            system_prompt="Extract clean markdown from web URLs using multi-tier scraper fallback.",
            model_name="deterministic",
            tools=[ScraperTool()]
        )

        # 4. Domain Intelligence Agent
        self.agents[4] = BaseResearchAgent(
            name="Domain Intelligence",
            role="Source Credibility",
            system_prompt="Evaluate domain authority and filter low-credibility or blocked web sources.",
            model_name="deterministic",
            tools=[DomainCredibilityTool()]
        )

        # 5. Citation Verifier Agent
        self.agents[5] = BaseResearchAgent(
            name="Citation Verifier",
            role="Citation Mapping",
            system_prompt="Map citations [N] directly to source sentences and strip broken markers.",
            model_name="phi3:mini",
            tools=[CitationVerifierTool()]
        )

        # 6. Quality Scorer Agent
        self.agents[6] = BaseResearchAgent(
            name="Quality Scorer",
            role="Report Evaluation",
            system_prompt="Score reports on relevance, depth, novelty, coherence, and citation accuracy.",
            model_name="phi3:mini",
            tools=[QualityScorerTool()]
        )

        # 7. Coherence Auditor Agent
        self.agents[7] = BaseResearchAgent(
            name="Coherence Auditor",
            role="Structure & Formatting",
            system_prompt="Audit heading hierarchy, transition density, and formatting balance.",
            model_name="phi3:mini",
            tools=[CoherenceTool()]
        )

        # 8. Lesson Learner Agent
        self.agents[8] = BaseResearchAgent(
            name="Lesson Learner",
            role="Continuous Learning",
            system_prompt="Extract self-reflection lessons and store them in the long-term knowledge vault.",
            model_name="phi3:mini",
            tools=[MemoryVaultTool()]
        )

        # 9. Gap Analyzer Agent
        self.agents[9] = BaseResearchAgent(
            name="Gap Analyzer",
            role="Completeness Audit",
            system_prompt="Identify unaddressed research angles and generate targeted gap queries.",
            model_name="phi3:mini",
            tools=[CoherenceTool()]
        )

        # 10. Repetition Detector Agent
        self.agents[10] = BaseResearchAgent(
            name="Repetition Detector",
            role="Redundancy Control",
            system_prompt="Detect cross-section semantic overlap and trigger source diversification.",
            model_name="deterministic",
            tools=[RepetitionDetectorTool()]
        )

        # 11. Tone & Style Auditor Agent
        self.agents[11] = BaseResearchAgent(
            name="Tone & Style Auditor",
            role="Editorial Voice",
            system_prompt="Enforce objective, authoritative voice and strip fluff lead-in phrases.",
            model_name="phi3:mini",
            tools=[CoherenceTool()]
        )

        # 12. Fact Checker Agent
        self.agents[12] = BaseResearchAgent(
            name="Fact Checker",
            role="Factual Grounding",
            system_prompt="Audit numerical figures, dates, and proper noun entities against source text.",
            model_name="phi3:mini",
            tools=[FactCheckTool()]
        )

        # 13. Source Diversifier Agent
        self.agents[13] = BaseResearchAgent(
            name="Source Diversifier",
            role="Source Triangulation",
            system_prompt="Force multi-domain source diversity when single-source dominance is detected.",
            model_name="qwen2.5:3b",
            tools=[DomainCredibilityTool()]
        )

        # 14. Export Specialist Agent
        self.agents[14] = BaseResearchAgent(
            name="Export Specialist",
            role="Artifact Export",
            system_prompt="Format research reports into Markdown, JSON, and PDF artifacts.",
            model_name="deterministic",
            tools=[]
        )

        # 15. Trend Analyzer Agent
        self.agents[15] = BaseResearchAgent(
            name="Trend Analyzer",
            role="Temporal Analysis",
            system_prompt="Detect temporal keywords and update research query time horizons.",
            model_name="phi3:mini",
            tools=[TopicClassifierTool()]
        )

        # 16. Redis Cache Agent
        self.agents[16] = BaseResearchAgent(
            name="Redis Cache Agent",
            role="Caching Infrastructure",
            system_prompt="Manage multi-level query caching and TTL expiration.",
            model_name="deterministic",
            tools=[]
        )

        # 17. Model Router Agent
        self.agents[17] = BaseResearchAgent(
            name="Model Router",
            role="LLM Cost Router",
            system_prompt="Dynamically route tasks between lightweight and high-capacity models.",
            model_name="deterministic",
            tools=[]
        )

        # 18. Session Manager Agent
        self.agents[18] = BaseResearchAgent(
            name="Session Manager",
            role="State Checkpointing",
            system_prompt="Save execution state checkpoints every 30s to support interruption/resume.",
            model_name="deterministic",
            tools=[]
        )

        # 19. Monitoring Agent
        self.agents[19] = BaseResearchAgent(
            name="Monitoring Agent",
            role="Telemetry & Latency",
            system_prompt="Record per-node timing, token usage, and latency telemetry.",
            model_name="deterministic",
            tools=[]
        )

        # 20. Scheduler Agent
        self.agents[20] = BaseResearchAgent(
            name="Scheduler Agent",
            role="Background Automations",
            system_prompt="Manage recurring cron research jobs and automated runs.",
            model_name="deterministic",
            tools=[]
        )

        # 21. Auto-Continue Agent
        self.agents[21] = BaseResearchAgent(
            name="Auto-Continue Agent",
            role="Loop Control",
            system_prompt="Control gap iteration loops until research quality target is met.",
            model_name="phi3:mini",
            tools=[QualityScorerTool()]
        )

    def get_agent(self, agent_id: int) -> Optional[BaseResearchAgent]:
        return self.agents.get(agent_id)

    def execute_fleet_step(self, agent_id: int, task: str, context: Dict[str, Any]) -> Any:
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent ID {agent_id} not found in fleet")
        return agent.execute(task, context)


# Global Singleton Fleet Instance
_global_fleet: Optional[AgentFleet] = None

def get_agent_fleet() -> AgentFleet:
    global _global_fleet
    if _global_fleet is None:
        _global_fleet = AgentFleet()
    return _global_fleet
