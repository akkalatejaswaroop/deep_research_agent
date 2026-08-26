import json, sys
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

data = json.loads(Path("graphify-out/graph.json").read_text(encoding="utf-8"))
G = json_graph.node_link_graph(data, edges="links")

terms = [
    "planner", "searcher", "filter", "synthesis", "evaluator",
    "citation", "gap", "memory", "agent", "report", "quality",
    "ollama", "redis", "celery", "supabase", "playwright",
]
scored = []
for nid, ndata in G.nodes(data=True):
    label = (ndata.get("label") or "").lower()
    score = sum(1 for t in terms if t in label)
    if score > 0:
        scored.append((score, nid))
scored.sort(reverse=True)
start_nodes = [nid for _, nid in scored[:3]]
print("START", [G.nodes[n].get("label", n) for n in start_nodes])

subgraph_nodes = set(start_nodes)
frontier = set(start_nodes)
edges = []
for _ in range(2):
    nxt = set()
    for n in frontier:
        for nb in G.neighbors(n):
            if nb not in subgraph_nodes:
                nxt.add(nb)
                edges.append((n, nb))
    subgraph_nodes.update(nxt)
    frontier = nxt

def rel(nid):
    label = (G.nodes[nid].get("label") or "").lower()
    return sum(1 for t in terms if t in label)

print(f"SUBGRAPH {len(subgraph_nodes)} nodes {len(edges)} edges")
for nid in sorted(subgraph_nodes, key=rel, reverse=True)[:25]:
    d = G.nodes[nid]
    print(f"NODE {d.get('label')} src={d.get('source_file')} loc={d.get('source_location')}")
