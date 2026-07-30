import os
import json
import sqlite3
import threading

try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

import socket
from urllib.parse import urlparse

def is_supabase_reachable(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        if not host:
            return False
        if ":" in host:
            host, port_str = host.split(":")
            port = int(port_str)
        else:
            port = 443 if parsed.scheme == "https" else 80
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except Exception:
        return False

def get_supabase_client():
    if create_client and SUPABASE_URL and SUPABASE_KEY:
        if not is_supabase_reachable(SUPABASE_URL):
            print("Supabase host is unreachable; falling back to offline mode.")
            return None
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            print(f"Error initializing Supabase: {e}")
            return None
    return None

supabase_client = get_supabase_client()

# SQLite setup
_local = threading.local()
DB_PATH = os.path.join(os.path.dirname(__file__), "local.db")

def get_db():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn

def init_db():
    conn = get_db()
    conn.executescript("""
        PRAGMA foreign_keys=OFF;
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            created_at TEXT NOT NULL,
            report TEXT DEFAULT '',
            structured_refs TEXT DEFAULT '[]',
            source_urls TEXT DEFAULT '[]',
            synthesis_results TEXT DEFAULT '[]',
            _metrics TEXT DEFAULT '{}',
            provenance TEXT DEFAULT '{}',
            feedback TEXT DEFAULT '',
            session_data TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS lessons (
            content_hash TEXT PRIMARY KEY,
            content TEXT NOT NULL DEFAULT '',
            embedding TEXT DEFAULT '[]',
            source TEXT DEFAULT '',
            relevance_tags TEXT DEFAULT '[]',
            analysis TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS knowledge_graph_entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS knowledge_graph_triples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            source TEXT DEFAULT '',
            confidence REAL DEFAULT 1.0
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_lessons_created ON lessons(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_triples_subject ON knowledge_graph_triples(subject);
        CREATE INDEX IF NOT EXISTS idx_triples_object ON knowledge_graph_triples(object);
    """)
    conn.commit()

init_db()

def _dict_from_row(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    for key in ("structured_refs", "source_urls", "synthesis_results", "_metrics", "provenance", "session_data",
                 "embedding", "relevance_tags", "analysis", "metadata"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d

def _rows_to_list(rows) -> list:
    return [_dict_from_row(r) for r in rows]

# In-memory cache (backed by SQLite)
in_memory_sessions: list = []
in_memory_knowledge: list = []

def load_local_caches():
    global in_memory_sessions, in_memory_knowledge
    conn = get_db()
    try:
        in_memory_sessions = _rows_to_list(conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall())
    except Exception as e:
        print(f"Error loading sessions from SQLite: {e}")
        in_memory_sessions = []
    try:
        in_memory_knowledge = _rows_to_list(conn.execute("SELECT * FROM lessons ORDER BY created_at DESC").fetchall())
    except Exception as e:
        print(f"Error loading lessons from SQLite: {e}")
        in_memory_knowledge = []

def save_session_local(session):
    conn = get_db()
    sid = session.get("id", "")
    if not sid:
        sid = str(hash(str(session)))
    row = {
        "id": sid,
        "query": session.get("query", ""),
        "created_at": session.get("created_at", ""),
        "report": session.get("report", ""),
        "structured_refs": json.dumps(session.get("structured_refs", []), ensure_ascii=False),
        "source_urls": json.dumps(session.get("source_urls", []), ensure_ascii=False),
        "synthesis_results": json.dumps(session.get("synthesis_results", []), ensure_ascii=False),
        "_metrics": json.dumps(session.get("_metrics", {}), ensure_ascii=False),
        "provenance": json.dumps(session.get("provenance", {}), ensure_ascii=False),
        "feedback": session.get("feedback", ""),
        "session_data": json.dumps({k: v for k, v in session.items() if k not in (
            "id", "query", "created_at", "report", "structured_refs", "source_urls",
            "synthesis_results", "_metrics", "provenance", "feedback",
        )}, ensure_ascii=False),
    }
    conn.execute("""INSERT INTO sessions (id, query, created_at, report, structured_refs, source_urls,
                   synthesis_results, _metrics, provenance, feedback, session_data)
                   VALUES (:id, :query, :created_at, :report, :structured_refs, :source_urls,
                   :synthesis_results, :_metrics, :provenance, :feedback, :session_data)
                   ON CONFLICT(id) DO UPDATE SET
                   report=excluded.report, query=excluded.query, structured_refs=excluded.structured_refs,
                   source_urls=excluded.source_urls, synthesis_results=excluded.synthesis_results,
                   _metrics=excluded._metrics, provenance=excluded.provenance, feedback=excluded.feedback,
                   session_data=excluded.session_data""", row)
    conn.commit()
    # Update in-memory cache
    for idx, s in enumerate(in_memory_sessions):
        if s.get("id") == sid:
            in_memory_sessions[idx] = {**session, "id": sid}
            break
    else:
        in_memory_sessions.insert(0, {**session, "id": sid})

def get_lessons_by_topic(query: str, limit: int = 5) -> list:
    """Retrieve lessons most relevant to a query topic, from local DB + in-memory cache."""
    words = query.lower().split()[:4]
    topic_key = " ".join(sorted(w for w in words if len(w) > 2)) if words else ""
    scored = []
    seen_hashes = set()
    for l in list(in_memory_knowledge):
        ch = l.get("content_hash", "")
        if ch in seen_hashes:
            continue
        seen_hashes.add(ch)
        l_content = (l.get("content") or l.get("analysis", {}).get("lesson") or "").lower()
        l_query = (l.get("query") or "").lower()
        score = 0
        if topic_key and any(w in l_content for w in topic_key.split()):
            score += 3
        if topic_key and any(w in l_query for w in topic_key.split()):
            score += 5
        if not topic_key:
            score = 1
        scored.append((score, l))
    scored.sort(key=lambda x: -x[0])
    return [l for s, l in scored[:limit] if s > 0] or list(in_memory_knowledge)[:limit]


def save_lesson_local(lesson):
    conn = get_db()
    chash = lesson.get("content_hash", "")
    row = {
        "content_hash": chash,
        "content": lesson.get("content", ""),
        "embedding": json.dumps(lesson.get("embedding", []), ensure_ascii=False),
        "source": lesson.get("source", ""),
        "relevance_tags": json.dumps(lesson.get("relevance_tags", []), ensure_ascii=False),
        "analysis": json.dumps(lesson.get("analysis", {}), ensure_ascii=False),
        "created_at": lesson.get("created_at", ""),
    }
    conn.execute("""INSERT INTO lessons (content_hash, content, embedding, source, relevance_tags, analysis, created_at)
                   VALUES (:content_hash, :content, :embedding, :source, :relevance_tags, :analysis, :created_at)
                   ON CONFLICT(content_hash) DO UPDATE SET
                   content=excluded.content, embedding=excluded.embedding, source=excluded.source,
                   relevance_tags=excluded.relevance_tags, analysis=excluded.analysis""", row)
    conn.commit()
    # Update in-memory cache
    for idx, l in enumerate(in_memory_knowledge):
        if l.get("content_hash") == chash:
            in_memory_knowledge[idx] = {**lesson, "content_hash": chash}
            break
    else:
        in_memory_knowledge.insert(0, {**lesson, "content_hash": chash})

# Load existing data into memory
load_local_caches()
