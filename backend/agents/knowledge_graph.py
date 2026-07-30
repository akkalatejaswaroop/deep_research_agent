import re
import json
import os
from typing import Dict, List, Tuple, Optional

try:
    import networkx as nx
except ImportError:
    nx = None

try:
    from db import get_db
except ImportError:
    get_db = None


# Common relation patterns for triple extraction
# Each tuple: (compiled_regex, group_subject, group_relation, group_object)
import re as _re_module

_RE_SUBJECT = r'([A-Z][a-zA-Z0-9]+(?:[- ][a-zA-Z0-9]+){0,4})'
_RE_OBJECT_TERM = r'(.+?)(?:\.(?:\s|$)|,\s+(?:and|which|where|including|such\s+as))'


def _compile_rel(verb_group: str) -> 're.Pattern':
    return _re_module.compile(
        rf'{_RE_SUBJECT}\s+(?:{verb_group})\s+{_RE_OBJECT_TERM}',
        _re_module.IGNORECASE,
    )


_RELATION_PATTERNS = [
    # is/are/was/were — captures object as whole predicate clause
    _compile_rel(r'is|are|was|were'),
    # Action verbs where entity is the subject
    _compile_rel(r'uses|employs|applies|leverages|utilizes'),
    _compile_rel(r'consists?\s+of|comprises?|includes?|contains?'),
    _compile_rel(r'enables?|allows?|lets?|permits?'),
    _compile_rel(r'achieves?|reaches?|attains?|demonstrates?|shows?'),
    _compile_rel(r'requires?|needs?|demands?'),
    _compile_rel(r'improves?|enhances?|boosts?|increases?'),
    _compile_rel(r'limits?|constrains?|restricts?|hinders?'),
    _compile_rel(r'differs?\s+from|contrasts?\s+with|outperforms?|exceeds?'),
    # has/have relation
    _compile_rel(r'has|have'),
    # produces/generates/creates
    _compile_rel(r'produces?|generates?|creates?|builds?|constructs?'),
]

_STOP_ENTITIES = {
    "it", "they", "this", "that", "these", "those", "we", "you",
    "one", "some", "many", "most", "all", "both", "each", "every",
    "researchers", "scientists", "experts", "studies", "research",
    "approach", "method", "technique", "system", "model",
}

_REJECT_SUBJECT_ENDING = {
    "that", "which", "where", "who", "whom", "whose",
    "when", "while", "if", "although", "because",
}


def _extract_triples_from_text(text: str) -> List[Tuple[str, str, str]]:
    """Extract (subject, relation, object) triples using regex patterns."""
    triples = []
    for pattern in _RELATION_PATTERNS:
        for m in pattern.finditer(text):
            subj = m.group(1).strip().rstrip(",").strip()
            obj = m.group(2).strip().rstrip(".,;").strip()
            # Extract the verb between subject and object from the full match
            after_subj = m.group(0)[m.end(1) - m.start(0):].strip()
            verb_part = after_subj[:after_subj.find(obj)].strip().split()
            verb_text = verb_part[0] if verb_part else "is"

            subj_last = subj.lower().split()[-1] if subj.split() else ""
            if (subj_last in _REJECT_SUBJECT_ENDING
                    or subj.lower() in _STOP_ENTITIES
                    or obj.lower() in _STOP_ENTITIES
                    or len(subj) <= 2 or len(obj) <= 2
                    or len(subj.split()) > 8 or len(obj.split()) > 12):
                continue
            triples.append((subj, verb_text, obj))
    return triples


class KnowledgeGraph:
    """In-memory knowledge graph storing (subject, relation, object) triples."""

    def __init__(self):
        if nx is None:
            raise ImportError("networkx is required for KnowledgeGraph")
        self.graph = nx.DiGraph()

    # ------------------------------------------------------------------
    # Adding data
    # ------------------------------------------------------------------

    def add_triple(self, subject: str, relation: str, obj: str,
                   source_query: str = "", source_url: str = "") -> None:
        """Add a (subject, relation, object) triple to the graph."""
        self.graph.add_edge(subject, obj, relation=relation,
                            source_query=source_query, source_url=source_url)

    def add_from_text(self, text: str, source_query: str = "",
                      source_url: str = "") -> int:
        """Extract triples from text and add them to the graph. Returns count."""
        triples = _extract_triples_from_text(text)
        for subj, rel, obj in triples:
            self.add_triple(subj, rel, obj, source_query, source_url)
        return len(triples)

    def add_from_synthesis(self, synthesis_results: List[Dict],
                           query: str = "") -> int:
        """Extract triples from each synthesis result. Returns total count."""
        total = 0
        for result in synthesis_results:
            answer = result.get("answer", "")
            if answer:
                total += self.add_from_text(answer, source_query=query)
        return total

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_facts(self, entity: str) -> List[Dict]:
        """Get all triples where entity is the subject."""
        if entity not in self.graph:
            return []
        facts = []
        for _, obj, data in self.graph.out_edges(entity, data=True):
            facts.append({
                "subject": entity,
                "relation": data.get("relation", ""),
                "object": obj,
                "source_query": data.get("source_query", ""),
                "source_url": data.get("source_url", ""),
            })
        return facts

    def get_reverse_facts(self, entity: str) -> List[Dict]:
        """Get all triples where entity is the object (i.e., who points to it)."""
        if entity not in self.graph:
            return []
        facts = []
        for subj, _, data in self.graph.in_edges(entity, data=True):
            facts.append({
                "subject": subj,
                "relation": data.get("relation", ""),
                "object": entity,
                "source_query": data.get("source_query", ""),
                "source_url": data.get("source_url", ""),
            })
        return facts

    def query_related(self, entity: str, max_hops: int = 2) -> List[Dict]:
        """BFS from entity to find related entities up to max_hops away."""
        if entity not in self.graph:
            return []
        visited = {entity}
        results = []
        queue = [(entity, 0)]
        while queue:
            current, depth = queue.pop(0)
            if depth > 0:
                facts = self.get_facts(current) + self.get_reverse_facts(current)
                for f in facts:
                    if f not in results:
                        results.append(f)
            if depth < max_hops:
                neighbors = set(self.graph.successors(current)) | set(self.graph.predecessors(current))
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))
        return results

    def search(self, query: str) -> List[Dict]:
        """Full-text search on entity names. Returns matching entities and their facts."""
        terms = query.lower().split()
        matches = set()
        for node in self.graph.nodes:
            node_lower = node.lower()
            if any(t in node_lower for t in terms):
                matches.add(node)

        results = []
        for entity in sorted(matches, key=lambda e: len(e)):
            facts = self.get_facts(entity) + self.get_reverse_facts(entity)
            results.extend(facts)
        return results

    def get_all_entities(self) -> List[str]:
        return sorted(self.graph.nodes)

    def get_all_triples(self) -> List[Dict]:
        triples = []
        for subj, obj, data in self.graph.edges(data=True):
            triples.append({
                "subject": subj,
                "relation": data.get("relation", ""),
                "object": obj,
            })
        return triples

    def get_stats(self) -> Dict:
        return {
            "entities": self.graph.number_of_nodes(),
            "triples": self.graph.number_of_edges(),
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        triples = []
        for subj, obj, data in self.graph.edges(data=True):
            triples.append({
                "subject": subj,
                "relation": data.get("relation", ""),
                "object": obj,
                "source_query": data.get("source_query", ""),
                "source_url": data.get("source_url", ""),
            })
        return {"triples": triples}

    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeGraph":
        kg = cls()
        for t in data.get("triples", []):
            kg.add_triple(
                t.get("subject", ""),
                t.get("relation", ""),
                t.get("object", ""),
                t.get("source_query", ""),
                t.get("source_url", ""),
            )
        return kg

    def save_json(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_json(cls, filepath: str) -> "KnowledgeGraph":
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        return cls()

    def _ensure_table(self) -> None:
        if get_db is None:
            return
        conn = get_db()
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph_triples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                source TEXT DEFAULT '',
                confidence REAL DEFAULT 1.0
            )
        """)
        conn.commit()

    def save_to_db(self) -> None:
        if get_db is None:
            return
        self._ensure_table()
        conn = get_db()
        conn.execute("DELETE FROM knowledge_graph_triples")
        for subj, obj, data in self.graph.edges(data=True):
            conn.execute(
                "INSERT INTO knowledge_graph_triples (subject, predicate, object, source, confidence) VALUES (?, ?, ?, ?, ?)",
                (subj, data.get("relation", ""), obj, data.get("source_query", ""), 1.0),
            )
        conn.commit()

    @classmethod
    def load_from_db(cls) -> "KnowledgeGraph":
        kg = cls()
        if get_db is None:
            return kg
        kg._ensure_table()
        try:
            conn = get_db()
            rows = conn.execute("SELECT subject, predicate, object, source FROM knowledge_graph_triples").fetchall()
            for row in rows:
                kg.add_triple(row["subject"], row["predicate"], row["object"], row["source"], "")
        except Exception:
            pass
        return kg

    def reset_db(self) -> None:
        """Drop and recreate the triples table (mostly for testing)."""
        if get_db is None:
            return
        conn = get_db()
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE IF EXISTS knowledge_graph_triples")
        conn.commit()


# Singleton for cross-request use (similar to in_memory_knowledge)
_global_kg: Optional[KnowledgeGraph] = None


def get_global_knowledge_graph() -> KnowledgeGraph:
    global _global_kg
    if _global_kg is None:
        _global_kg = KnowledgeGraph.load_from_db()
    return _global_kg


def save_global_knowledge_graph() -> None:
    global _global_kg
    if _global_kg is not None:
        _global_kg.save_to_db()
