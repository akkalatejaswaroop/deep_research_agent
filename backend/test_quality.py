from real_quality_scorer import compute_quality_scores, compute_overall

report = """# Deep Research Report: Neuro-Symbolic AI

Executive Summary
The deep-research pipeline for Neuro-Symbolic AI is taking longer than the 540s budget.

Analyzed & Cited Primary Sources (55)
1 arxiv.org https://arxiv.org/abs/2509.02918v1
"""

sources = []
for i in range(55):
    sources.append({"url": f"https://source{i}.com", "domain": f"source{i}.com", "content": ""})

scores = compute_quality_scores("Neuro-Symbolic AI", report, sources)
overall = compute_overall(scores)
print('Scores:', scores)
print('Overall:', overall)