-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create Research Sessions table
CREATE TABLE public.research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    depth INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create Agent Interactions table
CREATE TABLE public.agent_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.research_sessions(id) ON DELETE CASCADE,
    agent_type TEXT NOT NULL,
    input TEXT,
    output TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confidence_score FLOAT,
    tokens_used INTEGER
);

-- Create Knowledge Base table with vector embeddings
CREATE TABLE public.knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hash TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768), -- Sized for nomic-embed-text embedding dimension
    source TEXT,
    relevance_tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create Feedback Logs table
CREATE TABLE public.feedback_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.research_sessions(id) ON DELETE CASCADE,
    user_feedback TEXT,
    auto_eval_score FLOAT,
    improvements_applied TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Row Level Security
ALTER TABLE public.research_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback_logs ENABLE ROW LEVEL SECURITY;
-- knowledge_base might be shared or per-user, leaving public for now

-- Policies
CREATE POLICY "Users can view own sessions" ON public.research_sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own sessions" ON public.research_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
