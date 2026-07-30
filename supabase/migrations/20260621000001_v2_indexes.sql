-- Enable pg_trgm for text search if not enabled
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Create an HNSW index on the vector embedding column for ultra-fast similarity search
-- Note: Replace 'embedding' with the actual vector column name if different.
-- Using cosine distance (vector_cosine_ops)
CREATE INDEX IF NOT EXISTS knowledge_base_embedding_hnsw_idx 
ON knowledge_base 
USING hnsw (embedding vector_cosine_ops);

-- 2. Add a tsvector column for BM25 sparse keyword searches (Hybrid Search)
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS fts tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- 3. Create a GIN index on the new tsvector column
CREATE INDEX IF NOT EXISTS knowledge_base_fts_idx ON knowledge_base USING GIN (fts);

-- 4. Create an RPC function to perform vector similarity matching (required for MMR Python logic)
CREATE OR REPLACE FUNCTION match_knowledge_base (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  required_tag text
)
RETURNS TABLE (
  id uuid,
  content text,
  embedding vector(768),
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    knowledge_base.id,
    knowledge_base.content,
    knowledge_base.embedding,
    1 - (knowledge_base.embedding <=> query_embedding) AS similarity
  FROM knowledge_base
  WHERE required_tag = ANY(knowledge_base.relevance_tags)
  AND 1 - (knowledge_base.embedding <=> query_embedding) > match_threshold
  ORDER BY knowledge_base.embedding <=> query_embedding
  LIMIT match_count;
$$;
