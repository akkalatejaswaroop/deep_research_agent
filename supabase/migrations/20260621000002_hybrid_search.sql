-- Hybrid search combining vector similarity + full-text keyword search
-- Uses the existing knowledge_base table with:
--   embedding vector(768)  -- for semantic search
--   fts tsvector           -- for keyword search (BM25)

CREATE OR REPLACE FUNCTION search_knowledge_base(
  query_text text,
  query_embedding vector(768),
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  content text,
  source text,
  relevance_tags text[],
  similarity float,
  keyword_score float,
  combined_score float
)
LANGUAGE sql STABLE
AS $$
  WITH semantic AS (
    SELECT
      id, content, source, relevance_tags,
      1 - (embedding <=> query_embedding) AS similarity
    FROM knowledge_base
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> query_embedding
    LIMIT match_count * 2
  ),
  keyword AS (
    SELECT
      id,
      ts_rank(fts, plainto_tsquery('english', query_text)) AS score
    FROM knowledge_base
    WHERE fts @@ plainto_tsquery('english', query_text)
    ORDER BY score DESC
    LIMIT match_count * 2
  )
  SELECT
    s.id, s.content, s.source, s.relevance_tags,
    s.similarity,
    COALESCE(k.score, 0) AS keyword_score,
    (COALESCE(s.similarity, 0) * 0.7 + COALESCE(k.score, 0) * 0.3) AS combined_score
  FROM semantic s
  LEFT JOIN keyword k ON s.id = k.id
  ORDER BY combined_score DESC
  LIMIT match_count;
$$;
