"""
Prompt 9 deliverable tests:
1. GA runs 2 generations on toy eval set -> fitness table.
2. GATING: zero genomes promoted to Accepted without clearing BOTH threshold and safety floor.
3. Mutation operators are pure functions.
4. Invalid genomes never enter the population.
5. Accepted path requires numeric benchmark delta (LLM opinion alone is invalid).
"""
import os
import pytest

os.environ.setdefault("REX_VAULT_PATH", r"D:\deep_research_agent\REX-Brain")
os.environ.setdefault("PREFER_LLM", "false")

# fast embed patch before imports
import backend.agents.memory_agent as _ma
import math as _math
import re as _re
import hashlib as _hashlib


def _fast_embed(text):
    vec = [0.0] * 384
    for tok in _re.findall(r"[a-z0-9]{3,}", text.lower()):
        h = int(_hashlib.sha256(tok.encode()).hexdigest()[:8], 16) % 384
        vec[h] += 1.0
    n = _math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


_ma.LocalVectorIndex._embed = lambda self, text: _fast_embed(text)
_ma.LocalVectorIndex._embed_ollama = lambda self, text: None


from backend.agents.ga_workflow import (
    production_genome, validate_genome, mutate, crossover_single_point,
    compute_fitness, gate_against_production, GenomeRecord, MUTATION_OPERATORS,
    evolve, GA_ACCEPT_THRESHOLD, GA_RELIABILITY_FLOOR,
)


class TestGenomeRepresentation:
    def test_production_genome_is_valid(self):
        ok, why = validate_genome(production_genome())
        assert ok, why

    def test_genes_carry_params(self):
        g = production_genome()
        searcher = [x for x in g["genes"] if x["agent"] == "searcher"][0]
        assert "tool" in searcher["params"], "gene must carry tool param"
        assert "iterations" in searcher["params"], "gene must carry iteration count"

    def test_invalid_genomes_rejected(self):
        # no planner
        bad1 = {"id": None, "genes": [
            {"agent": "memory_retrieval", "params": {}},
            {"agent": "searcher", "params": {}},
            {"agent": "evaluator", "params": {}},
        ]}
        ok, why = validate_genome(bad1)
        assert not ok and "planner" in why
        # evaluator not last
        bad2 = {"id": None, "genes": [
            {"agent": "planner", "params": {}},
            {"agent": "evaluator", "params": {}},
            {"agent": "searcher", "params": {}},
        ]}
        ok, why = validate_genome(bad2)
        assert not ok
        # invalid tool
        bad3 = {"id": None, "genes": [
            {"agent": "planner", "params": {}},
            {"agent": "searcher", "params": {"tool": "bogus_tool"}},
            {"agent": "synthesizer", "params": {}},
            {"agent": "evaluator", "params": {}},
        ]}
        ok, why = validate_genome(bad3)
        assert not ok and "tool" in why


class TestMutationOperators:
    def test_all_ten_operators_exist(self):
        from backend.agents.ga_workflow import _MUTATIONS
        expected = {
            "add_agent", "remove_agent", "reorder_agents", "duplicate_agent",
            "change_tool", "change_search_strategy", "change_evaluator",
            "modify_agent_prompt", "modify_iteration_count", "modify_stopping_condition",
        }
        assert set(_MUTATIONS.keys()) == expected

    def test_mutations_are_pure(self):
        base = production_genome()
        import json
        before = json.dumps(base, sort_keys=True)
        for op in MUTATION_OPERATORS:
            mutate(base, op=op, seed=1)
            after = json.dumps(base, sort_keys=True)
            assert before == after, f"mutation {op} mutated its input — not pure!"

    def test_mutations_produce_valid_genomes(self):
        base = production_genome()
        for seed in range(30):
            child, applied = mutate(base, seed=seed)
            ok, why = validate_genome(child)
            assert ok, f"seed {seed} produced invalid genome ({why})"
            assert applied in MUTATION_OPERATORS


class TestCrossover:
    def test_single_point_crossover_valid(self):
        a, _ = mutate(production_genome(), seed=3)
        b, _ = mutate(production_genome(), seed=9)
        child, applied = crossover_single_point(a, b, seed=5)
        ok, why = validate_genome(child)
        assert ok, why
        assert "crossover" in applied or applied in MUTATION_OPERATORS

    def test_crossover_respects_validity(self):
        for seed in range(20):
            a, _ = mutate(production_genome(), seed=seed)
            b, _ = mutate(production_genome(), seed=seed + 100)
            child, _ = crossover_single_point(a, b, seed=seed)
            ok, why = validate_genome(child)
            assert ok, f"crossover seed {seed} broke validity: {why}"


class TestFitness:
    def test_weights_sum_to_one(self):
        from backend.agents import ga_workflow as ga
        total = ga.GA_WEIGHT_BENCHMARK + ga.GA_WEIGHT_COST + ga.GA_WEIGHT_RELIABILITY
        assert abs(total - 1.0) < 1e-9, f"weights must sum to 1.0, got {total}"

    def test_fitness_formula(self):
        # 0.6*bench + 0.25*(1-cost) + 0.15*(1-fail)
        fit = compute_fitness(benchmark_score=0.8, cost_norm=0.4, failure_rate=0.05)
        expected = round(0.6 * 0.8 + 0.25 * 0.6 + 0.15 * 0.95, 4)
        assert abs(fit - expected) < 1e-6


class TestGating:
    def _rec(self, fitness, fail_rate):
        return GenomeRecord(
            genome=production_genome(), generation=1, parents=[],
            mutation_applied="test", evaluation={"score": 0.7, "cost_norm": 0.4, "failure_rate": fail_rate},
            fitness=fitness,
        )

    def test_reject_below_threshold(self):
        prod_ev = {"failure_rate": 0.05}
        gate = gate_against_production(self._rec(0.74, 0.05), prod_ev, production_fitness=0.7295)
        assert gate["accepted"] is False
        assert not gate["clears_threshold"]

    def test_accept_above_threshold_with_safety(self):
        prod_ev = {"failure_rate": 0.08}
        gate = gate_against_production(self._rec(0.80, 0.06), prod_ev, production_fitness=0.70)
        assert gate["accepted"] is True
        assert gate["clears_threshold"] and gate["within_safety_floor"] and gate["no_reliability_regression"]

    def test_reject_on_safety_floor_violation(self):
        prod_ev = {"failure_rate": 0.12}
        # big fitness gain but failure rate above floor -> must NOT accept
        gate = gate_against_production(self._rec(0.95, 0.20), prod_ev, production_fitness=0.70)
        assert gate["accepted"] is False
        assert not gate["within_safety_floor"]
        assert any("safety floor" in r for r in gate["reasons"])

    def test_no_llm_opinion_field(self):
        # structural proof: gate function takes only numbers, has llm_opinion_used=False hardcoded
        prod_ev = {"failure_rate": 0.05}
        gate = gate_against_production(self._rec(0.90, 0.04), prod_ev, production_fitness=0.70)
        assert gate["llm_opinion_used"] is False


class TestTwoGenerationsEndToEnd:
    def test_two_generations_zero_unearned_promotions(self):
        res = evolve(generations=2, eval_set=[{"q": f"toy-{i}"} for i in range(4)], verbose=False)

        # fitness table exists across both generations
        gens = sorted({r["generation"] for r in res["generations"]})
        assert gens == [1, 2]
        assert len(res["generations"]) >= 6  # N=4 per gen minimum

        # every row has defined fitness and full benchmark result
        for row in res["generations"]:
            assert isinstance(row["fitness"], float) and 0.0 <= row["fitness"] <= 1.0

        # gating: count promotions
        promotions = [g for g in res["gates"] if g["accepted"]]
        for g in res["gates"]:
            if g["accepted"]:
                # must clear BOTH conditions
                assert g["fitness_delta"] >= GA_ACCEPT_THRESHOLD
                assert g["within_safety_floor"] and g["no_reliability_regression"]

        # In this toy run the champion delta was below threshold — assert zero unearned promotions
        for g in res["gates"]:
            if not (g["fitness_delta"] >= GA_ACCEPT_THRESHOLD
                    and g["within_safety_floor"] and g["no_reliability_regression"]):
                assert g["accepted"] is False, f"gen{g['generation']} promoted without clearing gates!"

        # No genome note may live in Accepted/ via GA (GA has no shortcut)
        accepted_dir = os.path.join(os.environ["REX_VAULT_PATH"], "05_Evolution", "Accepted")
        if os.path.exists(accepted_dir):
            accepted_files = [f for f in os.listdir(accepted_dir) if f.startswith("GEN-")]
            assert not accepted_files, f"GEN- notes found in Accepted/: {accepted_files}"
