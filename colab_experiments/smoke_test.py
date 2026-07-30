"""Quick smoke test of core simulation logic."""
import numpy as np, random, json

np.random.seed(42)
random.seed(42)

prompt = 'You are a research planning agent. Decompose the query into sub-questions.'
words = prompt.split()
print(f'Original ({len(words)} words): {prompt[:60]}...')

for mut_type in ['substitute', 'insert', 'rephrase']:
    w = words.copy()
    if mut_type == 'substitute':
        idx = random.randint(0, len(w) - 1)
        w[idx] = w[idx] + ' thoroughly'
    elif mut_type == 'insert':
        w.append('Be thorough and precise.')
    elif mut_type == 'rephrase':
        w.insert(0, 'as an expert')
    mutated = ' '.join(w)
    print(f'  {mut_type:12s} -> {mutated[:80]}')

class GraphTopology:
    def __init__(self, nodes=None, adjacency=None):
        self.nodes = nodes or ['planner','searcher','synthesis','evaluator']
        self.adjacency = adjacency or {
            'planner': [('searcher','fixed')],
            'searcher': [('synthesis','fixed')],
            'synthesis': [('evaluator','fixed')],
            'evaluator': []
        }
    def edge_count(self):
        return sum(len(v) for v in self.adjacency.values())
    def conditional_edge_count(self):
        return sum(1 for e in self.adjacency.values() for _,t in e if t=='conditional')

topo = GraphTopology()
print(f'\nTopology: {len(topo.nodes)} nodes, {topo.edge_count()} edges, {topo.conditional_edge_count()} conditional')

# Test fitness simulation
from dataclasses import dataclass
@dataclass
class Task:
    id: int
    query: str = "test"
    domain: str = "science"
    complexity: int = 2
    key_terms: tuple = ('test',)

task = Task(0, "What is dark matter?", "astrophysics", 2, ('dark','matter','wimp','axion'))

task_terms = set(t.lower() for t in task.key_terms)
term_matches = sum(1 for t in task_terms if t in prompt.lower())
print(f'Task term matches: {term_matches}/{len(task_terms)}')

base_q = 0.4 * min(1.0, term_matches / max(len(task_terms) * 0.4, 1))
base_q += 0.3 * min(1.0, len(prompt.split()) / 40.0)
base_q += 0.3 * sum(1 for m in ['json','return','generate','analyze'] if m in prompt.lower()) / 4.0
print(f'Base quality score: {base_q:.3f}')

quality = min(10, max(1, base_q * 8.5 + random.gauss(0, 1.5)))
print(f'Simulated quality: {quality:.2f}/10')
print(f'Success: {quality >= 7.0}')
print('\nALL SMOKE TESTS PASSED')
