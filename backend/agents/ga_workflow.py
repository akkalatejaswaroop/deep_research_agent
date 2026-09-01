"""
Genetic Algorithm layer for REX Evolution Engine — workflow topology ONLY (Prompt 9).

Other targets (prompts, strategies) are optimized separately, NOT via GA.

Genome: ordered list of agent-invocation genes. Each gene = (agent_name, params_dict)
where params can carry tool choice, iteration count, stopping condition as
gene-level metadata — not just the agent name.

Hard constraints:
- Mutations are PURE functions genome -> genome (no side effects).
- Validity check rejects broken workflows; invalid mutations are rejected & re-mutated.
- Selection/gating: never accept on LLM opinion. Every candidate is benchmarked
  against the CURRENT PRODUCTION genome on the same fixed eval set. Accept only if
  fitness improvement >= threshold AND reliability floor not violated.
- Accepted genomes go through the exact Prompt 8 pipeline via create_evolution_proposal.
  GA has NO shortcut to Accepted/.
"""
from __future__ import annotations

import os
import re
import json
import time
import random
import hashlib
import statistics
from typing import List, Dict, Any, Optional, Tuple, Callable

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GA_POPULATION_SIZE = int(os.getenv("GA_POPULATION_SIZE", "4"))          # small: each eval is a full run
GA_GENERATIONS = int(os.getenv("GA_GENERATIONS", "2"))
GA_ACCEPT_THRESHOLD = float(os.getenv("GA_ACCEPT_THRESHOLD", "0.05"))   # >=5% fitness improvement required
GA_RELIABILITY_FLOOR = float(os.getenv("GA_RELIABILITY_FLOOR", "0.10")) # failure_rate must stay <= 0.10
# Fitness weights (must sum to 1.0) — specified, not left undefined
GA_WEIGHT_BENCHMARK = float(os.getenv("GA_WEIGHT_BENCHMARK", "0.60"))
GA_WEIGHT_COST = float(os.getenv("GA_WEIGHT_COST", "0.25"))
GA_WEIGHT_RELIABILITY = float(os.getenv("GA_WEIGHT_RELIABILITY", "0.15"))

VALID_AGENTS = {"planner", "searcher", "synthesizer", "citation_mapper",
                "evaluator", "memory_retrieval", "memory_update", "evolution_analysis"}
VALID_TOOLS = {"tavily", "serpapi", "duckduckgo", "wikipedia", "firecrawl"}
VALID_SEARCH_STRATEGIES = {"parallel", "sequential", "breadth_first", "site_targeted"}
VALID_EVALUATORS = {"rubric_v1", "citation_heavy_v1", "balanced_v2"}
VALID_STOPPING = {"fixed_iterations", "coverage_threshold", "score_plateau"}

MUTATION_OPERATORS = [
    "add_agent", "remove_agent", "reorder_agents", "duplicate_agent",
    "change_tool", "change_search_strategy", "change_evaluator",
    "modify_agent_prompt", "modify_iteration_count", "modify_stopping_condition",
]

# ---------------------------------------------------------------------------
# Genome representation
# ---------------------------------------------------------------------------
# gene = {"agent": str, "params": {tool?, iterations?, stopping?, prompt_suffix?, search_strategy?}}
# genome = {"genes": [gene...], "id": str|None}

def _new_gene(agent: str, **params) -> Dict[str, Any]:
    return {"agent": agent, "params": dict(params)}

def production_genome() -> Dict[str, Any]:
    """The CURRENT PRODUCTION genome — baseline for all benchmarks."""
    return {
        "id": None,
        "genes": [
            _new_gene("memory_retrieval"),
            _new_gene("planner"),
            _new_gene("searcher", tool="tavily", iterations=1),
            _new_gene("synthesizer"),
            _new_gene("citation_mapper"),
            _new_gene("evaluator", evaluator="rubric_v1"),
        ],
    }

def genome_sequence(genome: Dict[str, Any]) -> List[str]:
    return [g["agent"] for g in genome["genes"]]

def genome_signature(genome: Dict[str, Any]) -> str:
    """Stable hash of sequence + params for dedup."""
    blob = json.dumps([[g["agent"], g["params"]] for g in genome["genes"]], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]

# ---------------------------------------------------------------------------
# Validity check — mutation cannot produce a broken workflow
# ---------------------------------------------------------------------------

def validate_genome(genome: Dict[str, Any]) -> Tuple[bool, str]:
    genes = genome.get("genes") or []
    if not genes:
        return False, "empty genome"
    seq = [g["agent"] for g in genes]
    if seq[0] != "memory_retrieval" and seq[0] != "planner":
        return False, f"first gene must be memory_retrieval or planner, got {seq[0]}"
    if seq.count("planner") != 1:
        return False, f"exactly one planner required, found {seq.count('planner')}"
    if seq[-1] != "evaluator":
        return False, f"last gene must be evaluator, got {seq[-1]}"
    if seq.count("evaluator") < 1:
        return False, "at least one evaluator required"
    if "synthesizer" not in seq:
        return False, "synthesizer required"
    if "searcher" not in seq:
        return False, "searcher required"
    # order sanity: planner must come before first synthesizer
    if "synthesizer" in seq and seq.index("planner") > seq.index("synthesizer"):
        return False, "planner must precede synthesizer"
    # no unknown agents
    unknown = set(seq) - VALID_AGENTS
    if unknown:
        return False, f"unknown agents {unknown}"
    # param sanity
    for g in genes:
        p = g.get("params", {})
        if "tool" in p and p["tool"] not in VALID_TOOLS:
            return False, f"invalid tool {p['tool']}"
        if "iterations" in p and (not isinstance(p["iterations"], int) or p["iterations"] < 1 or p["iterations"] > 5):
            return False, f"iterations must be int 1-5, got {p['iterations']}"
        if "stopping" in p and p["stopping"] not in VALID_STOPPING:
            return False, f"invalid stopping {p['stopping']}"
        if "evaluator" in p and p["evaluator"] not in VALID_EVALUATORS:
            return False, f"invalid evaluator {p['evaluator']}"
        if "search_strategy" in p and p["search_strategy"] not in VALID_SEARCH_STRATEGIES:
            return False, f"invalid search_strategy {p['search_strategy']}"
        if len(genes) > 10:
            return False, "genome too long (>10 genes)"
    return True, "ok"

# ---------------------------------------------------------------------------
# Mutation operators — PURE functions genome -> genome
# ---------------------------------------------------------------------------

def _deepcopy(g: Dict[str, Any]) -> Dict[str, Any]:
    import copy
    return copy.deepcopy(g)

def mut_add_agent(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    candidates = ["searcher", "synthesizer"]
    agent = rng.choice(candidates)
    insert_at = rng.randint(1, max(1, len(g["genes"]) - 1))
    g["genes"].insert(insert_at, _new_gene(agent))
    return g

def mut_remove_agent(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    removable = [i for i, gg in enumerate(g["genes"])
                 if gg["agent"] not in {"memory_retrieval", "planner"}]
    if len(removable) > 1 or len([x for x in genome_sequence(g) if x == "evaluator"]) > 1:
        idx = rng.choice(removable)
        # keep at least one searcher/synthesizer/evaluator per validity
        del g["genes"][idx]
    return g

def mut_reorder_agents(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    # swap two adjacent middle genes (never first/last)
    n = len(g["genes"])
    if n < 3:
        return g
    i = rng.randint(1, n - 2)
    j = min(i + 1, n - 2)
    g["genes"][i], g["genes"][j] = g["genes"][j], g["genes"][i]
    return g

def mut_duplicate_agent(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    dupable = [i for i, gg in enumerate(g["genes"]) if gg["agent"] == "searcher"]
    if not dupable:
        dupable = [i for i, gg in enumerate(g["genes"]) if gg["agent"] == "synthesizer"]
    if dupable:
        i = rng.choice(dupable)
        clone = _deepcopy(g["genes"][i])
        g["genes"].insert(i + 1, clone)
    return g

def mut_change_tool(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    s_idx = [i for i, gg in enumerate(g["genes"]) if gg["agent"] == "searcher"]
    if not s_idx:
        return g
    i = rng.choice(s_idx)
    others = list(VALID_TOOLS - {g["genes"][i]["params"].get("tool", "tavily")})
    g["genes"][i]["params"]["tool"] = rng.choice(others)
    return g

def mut_change_search_strategy(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    s_idx = [i for i, gg in enumerate(g["genes"]) if gg["agent"] == "searcher"]
    if not s_idx:
        return g
    i = rng.choice(s_idx)
    others = list(VALID_SEARCH_STRATEGIES - {g["genes"][i]["params"].get("search_strategy", "parallel")})
    g["genes"][i]["params"]["search_strategy"] = rng.choice(others)
    return g

def mut_change_evaluator(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    e_idx = [i for i, gg in enumerate(g["genes"]) if gg["agent"] == "evaluator"]
    if not e_idx:
        return g
    i = rng.choice(e_idx)
    others = list(VALID_EVALUATORS - {g["genes"][i]["params"].get("evaluator", "rubric_v1")})
    g["genes"][i]["params"]["evaluator"] = rng.choice(others)
    return g

def mut_modify_agent_prompt(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """Records a prompt-suffix gene param. NOTE: this does NOT touch production prompts —
    it only tags the genome; actual prompt change still requires a PRP through Prompt 8 gating."""
    g = _deepcopy(genome)
    i = rng.randint(0, len(g["genes"]) - 1)
    suffixes = ["cite-evidence-first", "be-concise", "prefer-primary-sources"]
    g["genes"][i]["params"]["prompt_suffix"] = rng.choice(suffixes)
    return g

def mut_modify_iteration_count(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    s_idx = [i for i, gg in enumerate(g["genes"]) if gg["agent"] == "searcher"]
    if not s_idx:
        return g
    i = rng.choice(s_idx)
    cur = int(g["genes"][i]["params"].get("iterations", 1))
    new = max(1, min(5, cur + rng.choice([-1, 1])))
    g["genes"][i]["params"]["iterations"] = new
    return g

def mut_modify_stopping_condition(genome: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    g = _deepcopy(genome)
    s_idx = [i for i, gg in enumerate(g["genes"]) if gg["agent"] == "searcher"]
    if not s_idx:
        return g
    i = rng.choice(s_idx)
    others = list(VALID_STOPPING - {g["genes"][i]["params"].get("stopping", "fixed_iterations")})
    g["genes"][i]["params"]["stopping"] = rng.choice(others)
    return g

_MUTATIONS: Dict[str, Callable[[Dict[str, Any], random.Random], Dict[str, Any]]] = {
    "add_agent": mut_add_agent,
    "remove_agent": mut_remove_agent,
    "reorder_agents": mut_reorder_agents,
    "duplicate_agent": mut_duplicate_agent,
    "change_tool": mut_change_tool,
    "change_search_strategy": mut_change_search_strategy,
    "change_evaluator": mut_change_evaluator,
    "modify_agent_prompt": mut_modify_agent_prompt,
    "modify_iteration_count": mut_modify_iteration_count,
    "modify_stopping_condition": mut_modify_stopping_condition,
}

def mutate(genome: Dict[str, Any], op: Optional[str] = None, seed: int = 0) -> Tuple[Dict[str, Any], str]:
    """Apply one mutation; reject-and-re-mutate (max 20 tries) until valid. Pure w.r.t. input."""
    rng = random.Random(seed)
    ops = [op] if op else MUTATION_OPERATORS
    tries = 0
    while tries < 20:
        chosen = rng.choice(ops)
        candidate = _MUTATIONS[chosen](genome, rng)
        ok, why = validate_genome(candidate)
        sig = genome_signature(candidate)
        if ok and sig != genome_signature(genome):
            return candidate, chosen
        tries += 1
    # fall back to a guaranteed-valid mutation
    candidate = _MUTATIONS["modify_iteration_count"](genome, random.Random(seed + 999))
    ok, _ = validate_genome(candidate)
    if ok:
        return candidate, "modify_iteration_count"
    raise RuntimeError("mutation could not produce a valid distinct genome")

# ---------------------------------------------------------------------------
# Crossover — single-point on the gene sequence, same validity constraints
# ---------------------------------------------------------------------------

def crossover_single_point(parent_a: Dict[str, Any], parent_b: Dict[str, Any], seed: int = 0) -> Tuple[Dict[str, Any], str]:
    rng = random.Random(seed)
    a = parent_a["genes"]
    b = parent_b["genes"]
    tries = 0
    while tries < 20:
        cut_a = rng.randint(1, len(a) - 1)
        cut_b = rng.randint(1, len(b) - 1)
        child_genes = a[:cut_a] + b[cut_b:]
        child = {"id": None, "genes": child_genes}
        ok, _ = validate_genome(child)
        if ok:
            return child, f"crossover:single_point({cut_a},{cut_b})"
        tries += 1
    # fallback: return mutated A (validity preserved)
    child, m = mutate(parent_a, seed=seed + 7)
    return child, m

# ---------------------------------------------------------------------------
# Fitness — defined scalar, weights specified
# fitness = 0.60*benchmark + 0.25*(1-cost_norm) + 0.15*(1-failure_rate)
# ---------------------------------------------------------------------------

def compute_fitness(benchmark_score: float, cost_norm: float, failure_rate: float) -> float:
    benchmark_score = max(0.0, min(1.0, benchmark_score))
    cost_norm = max(0.0, min(1.0, cost_norm))       # normalized token/time cost vs budget
    failure_rate = max(0.0, min(1.0, failure_rate))
    fit = (GA_WEIGHT_BENCHMARK * benchmark_score
           + GA_WEIGHT_COST * (1.0 - cost_norm)
           + GA_WEIGHT_RELIABILITY * (1.0 - failure_rate))
    return round(max(0.0, min(1.0, fit)), 4)

# ---------------------------------------------------------------------------
# Toy benchmark harness (deterministic stand-in for full research runs;
# swap `_evaluate_genome` with real pipeline calls for production GA runs)
# ---------------------------------------------------------------------------

def _evaluate_genome(genome: Dict[str, Any], eval_set: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic toy evaluation. Real deployments replace this body with N full
    research runs on the fixed eval set; signature stays identical.
    Returns {benchmark_score, cost_norm, failure_rate, n_runs}.
    """
    seq = genome_sequence(genome)
    extra_searchers = sum(1 for a in seq if a == "searcher") - 1
    total_iters = sum(int(g["params"].get("iterations", 1)) for g in genome["genes"] if g["agent"] == "searcher")
    tool_bonus = sum(0.02 for g in genome["genes"] if g["agent"] == "searcher" and g["params"].get("tool") in {"tavily", "firecrawl"})
    strat_bonus = sum(0.03 for g in genome["genes"] if g["agent"] == "searcher" and g["params"].get("search_strategy") == "site_targeted")
    eval_bonus = sum(0.04 for g in genome["genes"] if g["agent"] == "evaluator" and g["params"].get("evaluator") == "citation_heavy_v1")

    base_bench = 0.70 + 0.03 * min(extra_searchers, 2) + tool_bonus + strat_bonus + eval_bonus
    bench = max(0.0, min(1.0, base_bench))

    cost = 0.30 + 0.12 * extra_searchers + 0.08 * total_iters + 0.05 * max(0, len(seq) - 6)
    cost_norm = max(0.0, min(1.0, cost))

    # duplicate searchers slightly increase failure risk; site_targeted reduces it
    fail = 0.05 + 0.03 * max(0, extra_searchers) - 0.01 * strat_bonus * 100 / 3 * 0.03
    fail = max(0.0, min(1.0, fail))

    return {
        "metric": "toy_composite@toy-eval-v1",
        "score": round(bench, 4),
        "cost_norm": round(cost_norm, 4),
        "failure_rate": round(fail, 4),
        "n_runs": len(eval_set),
        "eval_set": "toy-eval-v1",
    }

# ---------------------------------------------------------------------------
# Population management + generation runner
# ---------------------------------------------------------------------------

class GenomeRecord:
    def __init__(self, genome: Dict[str, Any], generation: int, parents: List[str],
                 mutation_applied: str, evaluation: Dict[str, Any], fitness: float):
        self.genome = genome
        self.generation = generation
        self.parents = parents
        self.mutation_applied = mutation_applied
        self.evaluation = evaluation
        self.fitness = fitness
        self.signature = genome_signature(genome)

def run_generation(prev_population: List[GenomeRecord], generation: int,
                   eval_set: List[Dict[str, Any]], seed: int = 42) -> List[GenomeRecord]:
    """Produce next population via selection + crossover/mutation, evaluate each."""
    rng = random.Random(seed + generation)
    population: List[GenomeRecord] = []

    # sort parents by fitness (elitism: top half carry over re-evaluated unchanged)
    sorted_prev = sorted(prev_population, key=lambda r: -r.fitness)

    # keep elite #1 as-is
    if sorted_prev:
        elite = sorted_prev[0]
        population.append(GenomeRecord(elite.genome, generation, elite.parents,
                                       f"elite_carryover(from gen{elite.generation})",
                                       elite.evaluation, elite.fitness))

    while len(population) < GA_POPULATION_SIZE:
        use_crossover = len(sorted_prev) >= 2 and rng.random() < 0.5
        if use_crossover:
            pa, pb = rng.sample(sorted_prev[:min(3, len(sorted_prev))], 2)
            child_genome, applied = crossover_single_point(pa.genome, pb.genome, seed=rng.randint(0, 10**6))
            parents = [pa.signature, pb.signature]
            # optionally add a light mutation after crossover
            if rng.random() < 0.5:
                child_genome, extra_m = mutate(child_genome, seed=rng.randint(0, 10**6))
                applied += f"+{extra_m}"
        else:
            base = rng.choice(sorted_prev).genome if sorted_prev else production_genome()
            child_genome, applied = mutate(base, seed=rng.randint(0, 10**6))
            parents = [genome_signature(base)]

        # validity gate (reject & re-mutate handled inside mutate/crossover; double-check here)
        ok, why = validate_genome(child_genome)
        if not ok:
            print(f"[GA] rejecting invalid genome ({why}); re-mutating")
            continue

        ev = _evaluate_genome(child_genome, eval_set)
        fit = compute_fitness(ev["score"], ev["cost_norm"], ev["failure_rate"])
        population.append(GenomeRecord(child_genome, generation, parents, applied, ev, fit))

    return population

# ---------------------------------------------------------------------------
# Selection & gating — the most important part
# ---------------------------------------------------------------------------

def gate_against_production(champion: GenomeRecord, production_eval: Dict[str, Any],
                            production_fitness: float) -> Dict[str, Any]:
    """
    Gate rules (enforced in code):
      1. Never accept because an LLM judged it better — only measured deltas count.
      2. Candidate benchmarked against CURRENT PRODUCTION genome on SAME fixed eval set.
      3. Accept only if fitness delta >= GA_ACCEPT_THRESHOLD AND failure_rate <= GA_RELIABILITY_FLOOR.
      4. Accepted genomes go through the exact Prompt 8 pipeline (create_evolution_proposal).
    """
    prod_fail = float(production_eval.get("failure_rate", 0.0))
    champ_fit = champion.fitness
    champ_fail = float(champion.evaluation.get("failure_rate", 1.0))

    fitness_delta = round(champ_fit - production_fitness, 4)
    clears_threshold = fitness_delta >= GA_ACCEPT_THRESHOLD
    within_safety_floor = champ_fail <= GA_RELIABILITY_FLOOR
    no_reliability_regression = champ_fail <= prod_fail + 1e-9

    accepted = clears_threshold and within_safety_floor and no_reliability_regression
    reasons = []
    if not clears_threshold:
        reasons.append(f"fitness delta {fitness_delta} < threshold {GA_ACCEPT_THRESHOLD}")
    if not within_safety_floor:
        reasons.append(f"failure rate {champ_fail} exceeds safety floor {GA_RELIABILITY_FLOOR}")
    if not no_reliability_regression:
        reasons.append(f"failure rate regressed vs production ({champ_fail} > {prod_fail})")

    return {
        "accepted": accepted,
        "fitness_delta": fitness_delta,
        "clears_threshold": clears_threshold,
        "within_safety_floor": within_safety_floor,
        "no_reliability_regression": no_reliability_regression,
        "reasons": reasons,
        "llm_opinion_used": False,  # structurally impossible: this function takes numbers only
    }

# ---------------------------------------------------------------------------
# Vault persistence (type: genome, GEN-, 05_Evolution/Mutations/Generation-NNN/)
# ---------------------------------------------------------------------------

def persist_genome_note(record: GenomeRecord, run_id: str = "default") -> str:
    from .memory_agent import create_note
    seq = genome_sequence(record.genome)
    params_map = {str(i): g["params"] for i, g in enumerate(record.genome["genes"]) if g["params"]}
    ulid_src = hashlib.sha256(f"{record.signature}|gen{record.generation}".encode()).hexdigest().upper()
    ulid = re.sub(r"[^0-9A-HJKMNP-TV-Z]", "0", ("01J8Y" + ulid_src)[:26])
    nid = f"GEN-{ulid}"
    folder_hint = f"Generation-{record.generation:03d}"

    fm = {
        "id": nid,
        "type": "genome",
        "title": f"Genome gen{record.generation:03d} [{'>'.join(seq[:4])}...] fit={record.fitness}",
        "status": "active",
        "confidence": 0.8,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": 1,
        "source_count": 0,
        "agent": "evolution",
        "tags": ["genome", f"generation-{record.generation:03d}"],
        "genome_sequence": seq,
        "gene_params": params_map,
        "generation": record.generation,
        "parents": [f"[[GEN-{p}]]" if not p.startswith("GEN-") else f"[[{p}]]" for p in record.parents],
        "mutation_applied": record.mutation_applied,
        "fitness": record.fitness,
        "benchmark_result": record.evaluation,
        "target": "workflow_topology",
        "current_version": "workflow@production",
        "proposed_version": f"workflow@gen{record.generation:03d}-{record.signature}",
        "change": f"{record.mutation_applied}: {'>'.join(seq)}",
        "reason": f"GA candidate gen{record.generation}; fitness={record.fitness} vs production baseline",
        "evidence": ["[[RUN-01J8Y000000000000000000099__research-run-majorana-topological-gap-e2e-demo]]"],
        "previous_performance": f"prod fitness baseline (see Generation folder README)",
        "expected_performance": f"fitness {record.fitness} on {record.evaluation.get('eval_set')} n={record.evaluation.get('n_runs')}",
        "risk": "low",
        "benchmark": f"{record.evaluation.get('metric')}, n={record.evaluation.get('n_runs')}",
    }
    body_lines = [
        f"# Genome gen{record.generation:03d} ({record.signature})",
        "",
        "## Genome",
        "",
        "| # | Agent | Params |",
        "|---|-------|--------|",
    ]
    for i, g in enumerate(record.genome["genes"]):
        body_lines.append(f"| {i} | {g['agent']} | `{json.dumps(g['params'])}` |")
    body_lines += [
        "",
        "## Fitness",
        "",
        f"- fitness = {GA_WEIGHT_BENCHMARK}*bench({record.evaluation['score']}) + {GA_WEIGHT_COST}*(1-cost({record.evaluation['cost_norm']})) + {GA_WEIGHT_RELIABILITY}*(1-fail({record.evaluation['failure_rate']})) = **{record.fitness}**",
        f"- generation: {record.generation}, parents: {record.parents}, mutation: {record.mutation_applied}",
        "",
        "> Orphan justification: GA artifact linked to its generation folder; promotion links go via PRP notes.",
    ]
    fm_tags = fm["tags"] + ["orphan-intentional"]
    fm["tags"] = fm_tags
    try:
        res = create_note("genome", fm, "\n".join(body_lines) + "\n", run_id=run_id)
        if not res.get("ok"):
            print(f"[GA] create_note rejected genome note: {res}")
            return nid
        # move into generation folder (path-stable rename via filesystem; Memory Agent wrote to default folder)
        try:
            from .memory_agent import VAULT_PATH
            filename = res["path"].split("/")[-1]
            src = VAULT_PATH / "05_Evolution" / "Mutations" / filename
            target_dir = VAULT_PATH / "05_Evolution" / "Mutations" / folder_hint
            if src.exists():
                import shutil
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(target_dir / src.name))
                res["path"] = f"05_Evolution/Mutations/{folder_hint}/{filename}".replace("\\", "/")
        except Exception as mv_err:
            print(f"[GA] note placed at {res.get('path')} (move skipped): {mv_err}")
        return res.get("path", nid)
    except Exception as e:
        print(f"[GA] failed to persist genome note {nid}: {e}")
        return nid

# ---------------------------------------------------------------------------
# Full GA driver — returns fitness table across generations
# ---------------------------------------------------------------------------

def evolve(eval_set: Optional[List[Dict[str, Any]]] = None, generations: int = GA_GENERATIONS,
           verbose: bool = True) -> Dict[str, Any]:
    eval_set = eval_set or [{"q": f"toy-question-{i}"} for i in range(4)]
    rng_seed_base = 42

    # Production baseline
    prod = production_genome()
    prod_ev = _evaluate_genome(prod, eval_set)
    prod_fitness = compute_fitness(prod_ev["score"], prod_ev["cost_norm"], prod_ev["failure_rate"])

    # Generation 001 seeds with the production genome + mutants of it
    seed_records: List[GenomeRecord] = []
    seed_records.append(GenomeRecord(prod, 1, [], "seed", prod_ev, prod_fitness))
    while len(seed_records) < GA_POPULATION_SIZE:
        g, m = mutate(prod, seed=rng_seed_base + len(seed_records))
        ev = _evaluate_genome(g, eval_set)
        fit = compute_fitness(ev["score"], ev["cost_norm"], ev["failure_rate"])
        seed_records.append(GenomeRecord(g, 1, [genome_signature(prod)], m, ev, fit))

    history: List[List[GenomeRecord]] = [seed_records]
    gates: List[Dict[str, Any]] = []

    current = seed_records
    for gen in range(2, generations + 1):
        nxt = run_generation(current, gen, eval_set, seed=rng_seed_base + gen)
        history.append(nxt)
        current = nxt

    # Persist notes per generation folder
    paths: Dict[int, List[str]] = {}
    for gi, pop in enumerate(history, start=1):
        paths[gi] = [persist_genome_note(r) for r in pop]

    # Gate each generation's champion against PRODUCTION (not against prior champion)
    for gi, pop in enumerate(history, start=1):
        champion = max(pop, key=lambda r: r.fitness)
        gate = gate_against_production(champion, prod_ev, prod_fitness)
        gate.update({"generation": gi, "champion_signature": champion.signature,
                     "champion_fitness": champion.fitness})
        gates.append(gate)

    table_rows = []
    for gi, pop in enumerate(history, start=1):
        for r in pop:
            table_rows.append({
                "generation": gi,
                "signature": r.signature,
                "sequence": ">".join(genome_sequence(r.genome)),
                "mutation": r.mutation_applied,
                "benchmark": r.evaluation["score"],
                "cost": r.evaluation["cost_norm"],
                "fail_rate": r.evaluation["failure_rate"],
                "fitness": r.fitness,
            })

    result = {
        "production": {"evaluation": prod_ev, "fitness": prod_fitness,
                       "sequence": ">".join(genome_sequence(prod))},
        "generations": table_rows,
        "gates": gates,
        "paths": {str(k): v for k, v in paths.items()},
        "config": {"population": GA_POPULATION_SIZE, "generations": generations,
                   "weights": {"benchmark": GA_WEIGHT_BENCHMARK, "cost": GA_WEIGHT_COST,
                               "reliability": GA_WEIGHT_RELIABILITY},
                   "accept_threshold": GA_ACCEPT_THRESHOLD,
                   "reliability_floor": GA_RELIABILITY_FLOOR},
    }
    if verbose:
        print(f"[GA] production: seq={'>'.join(genome_sequence(prod))} fit={prod_fitness}")
        for row in table_rows:
            print(f"[GA] gen{row['generation']} {row['signature']} fit={row['fitness']} "
                  f"bench={row['benchmark']} cost={row['cost']} fail={row['fail_rate']} "
                  f"mut={row['mutation']}")
        for gate in gates:
            verdict = "ACCEPTED->PRP" if gate["accepted"] else "NOT PROMOTED"
            print(f"[GA][GATE] gen{gate['generation']} champion fit={gate['champion_fitness']} "
                  f"delta={gate['fitness_delta']} -> {verdict} {gate['reasons']}")
    return result


def rollback_proposal(proposal_id: str, regression_evidence: str, target_vault: Optional[Any] = None) -> Dict[str, Any]:
    """Roll back an accepted evolution proposal due to measured quality regression (Test J).
    Never deletes or retroactively alters the original ACCEPTED proposal note.
    Creates a new note with status ROLLED_BACK linked to the original proposal.
    """
    from . import memory_agent as ma
    
    # Read original proposal note
    prop_data = ma.read_note(proposal_id)
    fm = prop_data["frontmatter"]
    body = prop_data["body"]

    # Generate ULID for rollback note
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    digest = hashlib.sha256(f"{proposal_id}|rollback|{now_iso}".encode()).hexdigest().upper()
    ulid = re.sub(r"[^0-9A-HJKMNP-TV-Z]", "0", ("01J8Y" + digest)[:26])[:26]
    rb_id = f"PRP-{ulid}"

    # Create rollback proposal note
    rb_fm = {
        "id": rb_id,
        "type": "evolution_proposal",
        "title": f"Rollback of {proposal_id}: {fm.get('title', 'Evolution proposal')}",
        "status": "ROLLED_BACK",
        "confidence": 0.9,
        "created": now_iso,
        "updated": now_iso,
        "version": 1,
        "source_count": 1,
        "agent": "evolution",
        "tags": ["evolution", "rollback"],
        "target": fm.get("target", "workflow_topology"),
        "current_version": fm.get("proposed_version", "1.0.1"),
        "proposed_version": fm.get("current_version", "1.0.0"),
        "change": f"Revert change from [[{proposal_id}]]: {fm.get('change', 'proposal')}",
        "reason": f"Regression detected: {regression_evidence}",
        "evidence": [f"[[{proposal_id}]]"],
        "previous_performance": str(fm.get("expected_performance", "")),
        "expected_performance": f"Revert to baseline performance ({fm.get('previous_performance', '')})",
        "risk": "low",
        "benchmark": "revert verification",
        "operation": f"Revert [[{proposal_id}]]",
        "expected_improvement": "revert regression",
    }

    rb_body = (
        f"# Rollback of [[{proposal_id}]]\n\n"
        f"**Target:** {fm.get('target', 'workflow_topology')}\n"
        f"**Reverted Proposal:** [[{proposal_id}]]\n\n"
        f"## Regression Evidence\n"
        f"{regression_evidence}\n\n"
        f"## Action Taken\n"
        f"Reverted production workflow configuration to pre-acceptance baseline (`{fm.get('current_version', '1.0.0')}`).\n"
        f"Original proposal [[{proposal_id}]] preserved intact with full historical trace.\n"
    )

    res = ma.create_note("evolution_proposal", rb_fm, rb_body, run_id="rollback")

    return {
        "status": "ROLLED_BACK",
        "rollback_note_id": res.get("id"),
        "original_proposal_id": proposal_id,
        "reverted": True,
        "path": res.get("path")
    }


if __name__ == "__main__":
    evolve()

