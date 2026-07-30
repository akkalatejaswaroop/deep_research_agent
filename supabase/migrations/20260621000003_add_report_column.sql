-- Add report content and structured reference columns to research_sessions
-- so exports work even after server restart (exports use DB as fallback when
-- in-memory session_states cache is empty).

ALTER TABLE public.research_sessions
  ADD COLUMN IF NOT EXISTS report TEXT,
  ADD COLUMN IF NOT EXISTS structured_refs JSONB DEFAULT '[]'::jsonb;
