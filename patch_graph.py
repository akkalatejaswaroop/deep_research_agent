import re

with open('backend/agents/graph.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Restore the Gap Detector Prompt if it got mangled
# The diff tool replaced the gap detector prompt with the planner prompt.
# I need to find the gap detector and replace it back to the original.
# Original Gap Detector Prompt:
# Review the following research answers. For each sub-question, determine if the answer is:
# - COMPLETE: well-supported by evidence with specific facts
# - PARTIAL: some info found but key aspects missing
# - MISSING: no useful answer found
gap_prompt_orig = """You are a master research planner.
Given a user's research query, break it down into exactly 10 comprehensive sub-questions that must be answered to form a complete, deeply researched report.

Return ONLY a valid JSON array of strings (the sub-questions)."""
gap_prompt_fix = """Review the following research answers. For each sub-question, determine if the answer is:
- COMPLETE: well-supported by evidence with specific facts
- PARTIAL: some info found but key aspects missing
- MISSING: no useful answer found

For PARTIAL and MISSING, generate 2 new targeted search queries to fill the gap.

Return ONLY valid JSON:
{{
  "gaps": [
    {{"sub_question": "...", "status": "COMPLETE", "new_queries": []}},
    {{"sub_question": "...", "status": "PARTIAL", "new_queries": ["query1", "query2"]}}
  ]
}}"""
content = content.replace(gap_prompt_orig, gap_prompt_fix)

# 2. Fix the Evaluator Prompt
eval_prompt_orig = """You are an expert report writer.
Assemble the synthesis into a cohesive, flowing narrative.
Format the report in markdown.
Make sure every single question is answered deeply with 3 to 4 paragraphs per section.
DO NOT summarize too heavily—keep it massive and exhaustive.

1. Generate a single, concise 'Lesson Learned' about how the search or synthesis could be improved in the future.

2. Score the report on these five dimensions (0-10). Be honest and critical:
   - relevance: relevance of findings to query
   - depth: comprehensiveness of analysis
   - novelty: insightfulness of findings
   - coherence: structure and logical flow
   - citation_accuracy: support of claims by sources

Return valid JSON only. Keys: lesson, scores (object with keys relevance, depth, novelty, coherence, citation_accuracy)."""
eval_prompt_fix = """You are an evaluator. Review the original query and the final report.

1. Generate a single, concise 'Lesson Learned' about how the search or synthesis could be improved in the future.

2. Score the report on these five dimensions (0-10). Be honest and critical:
   - relevance: relevance of findings to query
   - depth: comprehensiveness of analysis
   - novelty: insightfulness of findings
   - coherence: structure and logical flow
   - citation_accuracy: support of claims by sources

Return valid JSON only. Keys: lesson, scores (object with keys relevance, depth, novelty, coherence, citation_accuracy)."""
content = content.replace(eval_prompt_orig, eval_prompt_fix)

# 3. Fix Planner Prompt (actually doing it correctly this time)
planner_prompt_orig = """You are a master research planner.
Given a user's research query, break it down into 10-15 sub-questions that must be answered to form a complete, highly detailed report.

Return ONLY a valid JSON array of strings (the sub-questions)."""
planner_prompt_new = """You are a master research planner.
Given a user's research query, break it down into exactly 10 comprehensive sub-questions that must be answered to form a complete, deeply researched report.

Return ONLY a valid JSON array of strings (the sub-questions)."""
content = content.replace(planner_prompt_orig, planner_prompt_new)

# 4. Fix Report Writer Prompt
report_prompt_orig = """You are an expert report writer.
Assemble the synthesis into a cohesive, flowing narrative.
Format the report in markdown.
Make sure every single question is answered deeply with 3-4 comprehensive paragraphs.
DO NOT summarize too heavily—keep it extensive."""
report_prompt_new = """You are an expert report writer.
Assemble the synthesis into a cohesive, flowing narrative.
Format the report in markdown.
Make sure every single question is answered deeply with 3 to 4 paragraphs per section.
DO NOT summarize too heavily—keep it massive and exhaustive."""
content = content.replace(report_prompt_orig, report_prompt_new)

with open('backend/agents/graph.py', 'w', encoding='utf-8') as f:
    f.write(content)
