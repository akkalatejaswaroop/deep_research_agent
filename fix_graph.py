with open('backend/agents/graph.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if line.strip() == 'chain = prompt | get_llm("evaluator")':
        new_lines.append(line)
        new_lines.append('    response = chain.invoke({"query": state["query"], "report": state.get("report", "")})\n')
        new_lines.append('\n')
        new_lines.append('    lesson = response.content\n')
        new_lines.append('    scores = {}\n')
        new_lines.append('    parsed = extract_json(lesson)\n')
        new_lines.append('    if isinstance(parsed, dict):\n')
        new_lines.append('        if "scores" in parsed:\n')
        new_lines.append('            scores = parsed["scores"]\n')
        new_lines.append('        if "lesson" in parsed:\n')
        new_lines.append('            lesson = parsed["lesson"]\n')
        new_lines.append('\n')
        new_lines.append('    record_quality_scores(sid, scores)\n')
        new_lines.append('    record_node_exit(sid, "evaluator")\n')
        new_lines.append('\n')
        new_lines.append('    if supabase_client:\n')
        new_lines.append('        try:\n')
        new_lines.append('            vector = embeddings.embed_query(lesson)\n')
        new_lines.append('            content_hash = hashlib.sha256(lesson.encode("utf-8")).hexdigest()\n')
        new_lines.append('            supabase_client.table("knowledge_base").insert({\n')
        new_lines.append('                "content_hash": content_hash,\n')
        new_lines.append('                "content": lesson,\n')
        new_lines.append('                "embedding": vector,\n')
        new_lines.append('                "source": "Self-Reflection",\n')
        new_lines.append('                "relevance_tags": ["lesson_learned"],\n')
        new_lines.append('                "analysis": parsed if isinstance(parsed, dict) else {}\n')
        new_lines.append('            }).execute()\n')
        new_lines.append('        except Exception as e:\n')
        new_lines.append('            print(f"Failed to insert lesson: {e}")\n')
        new_lines.append('\n')
        new_lines.append('    return {"feedback": lesson}\n')
        new_lines.append('\n')
        new_lines.append('\n')
        new_lines.append('# ---------------------------------------------------------------------------\n')
        new_lines.append('# Memory Retrieval – Hybrid Search\n')
        new_lines.append('# ---------------------------------------------------------------------------\n')
        new_lines.append('\n')
        new_lines.append('def memory_retrieval_node(state: AgentState, config: RunnableConfig) -> Dict:\n')
        new_lines.append('    sid = config["configurable"]["thread_id"]\n')
        new_lines.append('    _current_session_id.set(sid)\n')
        new_lines.append('    record_node_entry(sid, "memory_retrieval")\n')
        new_lines.append('    emit_thought(config, "Retrieving relevant past research from knowledge base...")\n')
        new_lines.append('    if not supabase_client:\n')
        new_lines.append('        record_node_exit(sid, "memory_retrieval")\n')
        new_lines.append('        return {"retrieved_memory": []}\n')
        new_lines.append('\n')
        new_lines.append('    query = state.get("query", "")\n')
        new_lines.append('    if not query:\n')
        new_lines.append('        record_node_exit(sid, "memory_retrieval")\n')
        new_lines.append('        return {"retrieved_memory": []}\n')
        new_lines.append('\n')
        break
    else:
        new_lines.append(line)

for i, line in enumerate(lines):
    if i >= 1136 and line.strip() == 'try:':
        new_lines.extend(lines[i:])
        break

with open('backend/agents/graph.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
