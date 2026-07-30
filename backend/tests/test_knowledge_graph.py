import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def kg():
    from agents.knowledge_graph import KnowledgeGraph
    g = KnowledgeGraph()
    g.add_triple("Transformer", "uses", "self-attention", "test", "https://example.com")
    g.add_triple("Transformer", "achieves", "state-of-the-art", "test", "https://example.com")
    g.add_triple("Self-attention", "has", "quadratic complexity", "test", "https://arxiv.org")
    g.add_triple("BERT", "is", "a transformer model", "test", "https://example.com")
    g.add_triple("GPT", "is", "a transformer model", "test", "https://example.com")
    return g


class TestKnowledgeGraph:
    def test_add_triple(self, kg):
        assert kg.graph.number_of_edges() == 5
        assert kg.graph.number_of_nodes() == 8

    def test_get_facts(self, kg):
        facts = kg.get_facts("Transformer")
        assert len(facts) == 2
        relations = {f["relation"] for f in facts}
        assert "uses" in relations
        assert "achieves" in relations

    def test_get_reverse_facts(self, kg):
        facts = kg.get_reverse_facts("a transformer model")
        assert len(facts) == 2
        subjects = {f["subject"] for f in facts}
        assert "BERT" in subjects
        assert "GPT" in subjects

    def test_query_related_one_hop(self, kg):
        related = kg.query_related("Transformer", max_hops=1)
        objects = {f["object"] for f in related}
        assert "self-attention" in objects

    def test_query_related_two_hops(self, kg):
        related = kg.query_related("Transformer", max_hops=2)
        assert len(related) >= 1

    def test_search_by_term(self, kg):
        results = kg.search("transformer")
        assert len(results) > 0
        subjects = {f["subject"] for f in results}
        assert "Transformer" in subjects

    def test_search_by_partial_term(self, kg):
        results = kg.search("attention")
        assert len(results) > 0

    def test_search_no_match(self, kg):
        results = kg.search("zzzznonexistent")
        assert len(results) == 0

    def test_get_all_entities(self, kg):
        entities = kg.get_all_entities()
        assert len(entities) >= 5

    def test_get_all_triples(self, kg):
        triples = kg.get_all_triples()
        assert len(triples) == 5

    def test_get_stats(self, kg):
        stats = kg.get_stats()
        assert stats["entities"] == 8
        assert stats["triples"] == 5


class TestTripleExtraction:
    def test_simple_is_relation(self):
        from agents.knowledge_graph import _extract_triples_from_text
        triples = _extract_triples_from_text(
            "Transformer is a neural network model for sequence processing."
        )
        assert len(triples) >= 1
        subj, rel, obj = triples[0]
        assert "Transformer" in subj
        assert rel == "is"

    def test_uses_relation(self):
        from agents.knowledge_graph import _extract_triples_from_text
        triples = _extract_triples_from_text(
            "GPT-4 uses a transformer decoder architecture."
        )
        assert len(triples) >= 1
        subj, rel, obj = triples[0]
        assert "GPT" in subj

    def test_achieves_relation(self):
        from agents.knowledge_graph import _extract_triples_from_text
        triples = _extract_triples_from_text(
            "The system achieves 95% accuracy on the benchmark."
        )
        assert len(triples) >= 1
        subj, rel, obj = triples[0]
        assert rel == "achieves"

    def test_empty_text(self):
        from agents.knowledge_graph import _extract_triples_from_text
        assert _extract_triples_from_text("") == []

    def test_text_without_relations(self):
        from agents.knowledge_graph import _extract_triples_from_text
        assert _extract_triples_from_text("Hello world.") == []

    def test_improves_relation(self):
        from agents.knowledge_graph import _extract_triples_from_text
        triples = _extract_triples_from_text(
            "Algorithm-X improves training speed by 2x."
        )
        assert len(triples) >= 1
        subj, rel, obj = triples[0]
        assert rel == "improves"


class TestAddFromSynthesis:
    def test_adds_triples_from_results(self):
        from agents.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        results = [
            {
                "sub_question": "What is a transformer?",
                "answer": (
                    "The transformer architecture uses self-attention mechanisms. "
                    "It achieves state-of-the-art results on NLP tasks."
                ),
            }
        ]
        count = kg.add_from_synthesis(results)
        assert count >= 1
        assert kg.graph.number_of_edges() >= 1

    def test_empty_results(self):
        from agents.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        count = kg.add_from_synthesis([])
        assert count == 0

    def test_results_with_no_answer(self):
        from agents.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        count = kg.add_from_synthesis([{"sub_question": "test", "answer": ""}])
        assert count == 0


class TestSerialization:
    def test_to_dict_roundtrip(self, kg):
        data = kg.to_dict()
        from agents.knowledge_graph import KnowledgeGraph
        kg2 = KnowledgeGraph.from_dict(data)
        assert kg2.graph.number_of_edges() == kg.graph.number_of_edges()
        assert kg2.graph.number_of_nodes() == kg.graph.number_of_nodes()

    def test_save_load_json(self, kg, tmp_path):
        import json
        from agents.knowledge_graph import KnowledgeGraph
        fp = str(tmp_path / "test_kg.json")
        kg.save_json(fp)
        kg2 = KnowledgeGraph.load_json(fp)
        assert kg2.graph.number_of_edges() == kg.graph.number_of_edges()


class TestGlobalKG:
    def test_global_singleton(self):
        from agents.knowledge_graph import get_global_knowledge_graph
        kg1 = get_global_knowledge_graph()
        kg2 = get_global_knowledge_graph()
        assert kg1 is kg2

    def test_global_save_load(self):
        from agents.knowledge_graph import KnowledgeGraph, get_global_knowledge_graph, save_global_knowledge_graph
        import agents.knowledge_graph as kg_mod
        # Set up a fresh global KG with known state
        fresh = KnowledgeGraph()
        fresh.add_triple("Known", "is", "a test entity")
        kg_mod._global_kg = fresh
        save_global_knowledge_graph()
        # Reset to force reload
        kg_mod._global_kg = None
        kg2 = get_global_knowledge_graph()
        assert kg2.graph.number_of_edges() == 1
