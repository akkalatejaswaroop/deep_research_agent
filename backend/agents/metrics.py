"""Research metrics tracker for the evaluation section of the paper.

Collects per-run quantitative data:
  - Per-node timing (wall-clock)
  - LLM call counts per node
  - Quality scores (LLM-as-a-Judge): relevance, depth, novelty, coherence, citation accuracy
  - Source quality breakdown
  - Depth & breadth (sub-questions, iterations, sources)
  - Self-improvement signal (lesson learned, score deltas)
"""
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class NodeTiming:
    node_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    llm_calls: int = 0


@dataclass
class QualityScores:
    relevance: float = 0.0
    depth: float = 0.0
    novelty: float = 0.0
    coherence: float = 0.0
    citation_accuracy: float = 0.0


@dataclass
class ResearchMetrics:
    session_id: str = ""
    query: str = ""
    depth_setting: int = 1
    complexity: int = 1
    total_time_ms: float = 0.0
    node_timings: Dict[str, NodeTiming] = field(default_factory=dict)
    llm_calls_total: int = 0
    sub_question_count: int = 0
    source_count: int = 0
    gap_iterations: int = 0
    quality: QualityScores = field(default_factory=QualityScores)
    source_quality_breakdown: Dict[str, int] = field(default_factory=dict)
    lessons: List[str] = field(default_factory=list)
    node_execution_order: List[str] = field(default_factory=list)
    total_nodes_explored: int = 0


class MetricsTracker:
    """Singleton-like tracker. Call start_run / end_run around each research graph execution."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.metrics = ResearchMetrics()
        self._current_node: Optional[str] = None
        self._node_start: float = 0.0
        self._run_start: float = 0.0
        self._timeline: List[Dict] = []

    def start_run(self, session_id: str, query: str, depth: int, complexity: int):
        self.reset()
        self.metrics.session_id = session_id
        self.metrics.query = query
        self.metrics.depth_setting = depth
        self.metrics.complexity = complexity
        self._run_start = time.time()

    def end_run(self):
        self.metrics.total_time_ms = round((time.time() - self._run_start) * 1000, 1)
        self.metrics.total_nodes_explored = len(self.metrics.node_execution_order)

    def start_node(self, node_name: str):
        self._current_node = node_name
        self._node_start = time.time()
        if node_name not in self.metrics.node_timings:
            self.metrics.node_timings[node_name] = NodeTiming(node_name=node_name)
        self.metrics.node_timings[node_name].start_time = self._node_start
        self.metrics.node_execution_order.append(node_name)

    def end_node(self, node_name: str):
        elapsed = time.time() - self._node_start
        timing = self.metrics.node_timings[node_name]
        timing.end_time = time.time()
        timing.duration_ms = round(elapsed * 1000, 1)

    def count_llm_call(self, node_name: str):
        self.metrics.llm_calls_total += 1
        if node_name in self.metrics.node_timings:
            self.metrics.node_timings[node_name].llm_calls += 1

    def record_sub_questions(self, count: int):
        self.metrics.sub_question_count = count

    def record_sources(self, count: int):
        self.metrics.source_count = count

    def record_gap_iterations(self, count: int):
        self.metrics.gap_iterations = count

    def record_source_quality(self, source_name: str):
        self.metrics.source_quality_breakdown[source_name] = \
            self.metrics.source_quality_breakdown.get(source_name, 0) + 1

    def set_quality_scores(self, scores: Dict[str, float]):
        q = self.metrics.quality
        q.relevance = scores.get("relevance", 0)
        q.depth = scores.get("depth", 0)
        q.novelty = scores.get("novelty", 0)
        q.coherence = scores.get("coherence", 0)
        q.citation_accuracy = scores.get("citation_accuracy", 0)

    def add_lesson(self, lesson: str):
        self.metrics.lessons.append(lesson)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self.metrics)
        d["quality"] = asdict(self.metrics.quality)
        timings_list = []
        for name, t in self.metrics.node_timings.items():
            td = asdict(t)
            td["node_name"] = name
            timings_list.append(td)
        d["node_timings"] = timings_list
        return d


# Module-level singleton
_tracker = MetricsTracker()


def get_tracker() -> MetricsTracker:
    return _tracker
