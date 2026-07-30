from typing import TypedDict, Annotated, List, Dict, Any
import operator

class AgentState(TypedDict):
    messages: Annotated[List[Any], operator.add]
    query: str
    depth: int
    complexity: int
    target_paragraphs: int
    target_sub_questions: int
    current_depth: int
    sub_questions: List[str]
    search_queries: List[List[str]]
    raw_pages: Dict[str, str]
    source_urls: List[str]
    scored_chunks: List[Dict[str, Any]]
    synthesis_results: List[Dict[str, Any]]
    gap_results: List[Dict[str, Any]]
    gap_iteration: int
    cited_report: str
    report: str
    findings: Annotated[List[str], operator.add]
    sub_tasks: List[str]
    feedback: str
    is_valid: bool
    prior_lessons: List[str]
    retrieved_memory: List[Dict[str, Any]]
    structured_refs: Annotated[List[Dict[str, Any]], operator.add]
    metrics: Dict[str, Any]
    logs: Annotated[List[str], operator.add]
    active_node: str
    provenance: Dict[str, Any]
