import time
from typing import Dict, List, Optional

# In-memory session metrics (cleared on server restart)
_sessions: Dict[str, dict] = {}

# Lightweight history for proof-of-improvement (keyed by normalized topic)
_quality_history: Dict[str, List[float]] = {}


def start_session(session_id: str, query: str = "", depth: int = 1):
    _sessions[session_id] = {
        "query": query,
        "depth": depth,
        "start_time": time.perf_counter(),
        "end_time": None,
        "node_timings": {},
        "node_order": [],
        "llm_calls": 0,
        "llm_calls_per_stage": {},
        "estimated_input_tokens": 0,
        "estimated_output_tokens": 0,
        "sub_question_count": 0,
        "queries_count": 0,
        "sources_found": 0,
        "gap_iterations": 0,
        "quality_scores": None,
        "prior_lessons_used": [],
    }


def get_session(sid: str) -> dict:
    return _sessions.get(sid, {})


def record_node_entry(sid: str, node: str):
    data = _sessions.get(sid)
    if data is None:
        return
    if "node_entry_times" not in data:
        data["node_entry_times"] = {}
    data["node_entry_times"][node] = time.perf_counter()
    data.setdefault("node_order", []).append(node)


def record_node_exit(sid: str, node: str):
    data = _sessions.get(sid)
    if data is None:
        return
    entry = data.get("node_entry_times", {}).pop(node, None)
    if entry is not None:
        duration_ms = (time.perf_counter() - entry) * 1000
        data["node_timings"][node] = round(duration_ms, 1)


def record_llm_call(sid: str, stage: str, input_len: int = 0, output_len: int = 0):
    data = _sessions.get(sid)
    if data is None:
        return
    data["llm_calls"] += 1
    data["llm_calls_per_stage"][stage] = data["llm_calls_per_stage"].get(stage, 0) + 1
    data["estimated_input_tokens"] += input_len
    data["estimated_output_tokens"] += output_len


def record_quality_scores(sid: str, scores: dict):
    data = _sessions.get(sid)
    if data is not None:
        data["quality_scores"] = scores


def record_prior_lessons(sid: str, lessons: list):
    data = _sessions.get(sid)
    if data is not None:
        data["prior_lessons_used"] = list(lessons)


def record_graph_state(sid: str, state: dict):
    data = _sessions.get(sid)
    if data is None:
        return
    data["sub_question_count"] = len(state.get("sub_questions", []))
    data["queries_count"] = len(state.get("search_queries", []))
    data["sources_found"] = len(state.get("source_urls", []))
    data["gap_iterations"] = state.get("gap_iteration", 0)


def compute(sid: str) -> Optional[dict]:
    data = _sessions.get(sid)
    if data is None:
        return None
    data["end_time"] = time.perf_counter()
    total_ms = round((data["end_time"] - data["start_time"]) * 1000, 1)

    scores = data.get("quality_scores") or {}
    overall = None
    if scores:
        vals = [v for v in scores.values() if isinstance(v, (int, float))]
        overall = round(sum(vals) / len(vals), 1) if vals else None

    # Build proof-of-improvement
    prior = data.get("prior_lessons_used", [])
    proof = {
        "prior_lessons_count": len(prior),
        "prior_lessons": prior[:5],
        "current_quality_scores": scores,
        "current_overall": overall,
    }

    # Compare against history for similar topics
    topic = _normalize_topic(data.get("query", ""))
    if topic:
        history = _quality_history.get(topic, [])
        if history:
            avg_before = round(sum(history) / len(history), 1)
            delta = round(overall - avg_before, 1) if overall else None
            proof["history_count"] = len(history)
            proof["average_prior_quality"] = avg_before
            proof["quality_delta"] = delta
        if overall is not None:
            history.append(overall)
            _quality_history[topic] = history[-20:]  # keep last 20

    return {
        "execution": {
            "total_duration_ms": total_ms,
            "node_timings_ms": dict(data["node_timings"]),
            "node_order": list(data["node_order"]),
        },
        "breadth": {
            "depth": data["depth"],
            "sub_questions": data["sub_question_count"],
            "search_queries": data["queries_count"],
            "sources_found": data["sources_found"],
            "gap_iterations": data["gap_iterations"],
        },
        "efficiency": {
            "total_llm_calls": data["llm_calls"],
            "llm_calls_per_stage": dict(data["llm_calls_per_stage"]),
            "estimated_input_tokens": data["estimated_input_tokens"],
            "estimated_output_tokens": data["estimated_output_tokens"],
        },
        "quality": {
            "scores": scores,
            "overall": overall,
        },
        "proof_of_improvement": proof,
    }


def clear(sid: str):
    _sessions.pop(sid, None)


def _normalize_topic(query: str) -> str:
    words = query.lower().split()[:4]
    return " ".join(sorted(words)) if words else ""
