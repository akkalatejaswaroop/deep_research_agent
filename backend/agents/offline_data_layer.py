"""
Offline-First Data Layer for Deep Research.
Provides pre-downloaded datasets, local vector search, and hybrid online/offline routing.
"""

import os
import sqlite3
import json
import hashlib
import time
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import lancedb
except ImportError:
    lancedb = None

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


class DataSource(Enum):
    WIKIPEDIA = "wikipedia"
    ARXIV = "arxiv"
    COMMON_CRAWL = "common_crawl"
    GUTENBERG = "gutenberg"
    WIKIDATA = "wikidata"
    LOCAL_DOCS = "local_docs"
    CACHED_WEB = "cached_web"


@dataclass
class OfflineDocument:
    doc_id: str
    title: str
    content: str
    source: DataSource
    url: str = ""
    metadata: Dict = None
    embedding: List[float] = None
    timestamp: float = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp == 0:
            self.timestamp = time.time()


class OfflineDataManager:
    """Manages all offline data sources with unified search interface."""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or os.path.join(os.path.dirname(__file__), "..", "offline_data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "offline_corpus.db"
        self.vector_db_path = self.data_dir / "vectors"
        self.vector_db_path.mkdir(exist_ok=True)
        
        self._init_sqlite()
        self._init_vector_db()
        self._embedding_model = None
        self._search_index = None
        
    def _init_sqlite(self):
        """Initialize SQLite for document metadata and full-text search."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT,
                metadata TEXT,
                timestamp REAL
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts 
            USING fts5(title, content, metadata, content=documents, content_rowid=rowid)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT,
                results TEXT,
                timestamp REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON documents(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON documents(timestamp)")
        conn.commit()
        conn.close()
    
    def _init_vector_db(self):
        """Initialize LanceDB for vector similarity search."""
        if lancedb is not None:
            try:
                self.vector_db = lancedb.connect(str(self.vector_db_path))
                # Create table if not exists
                try:
                    self.vector_table = self.vector_db.open_table("documents")
                except Exception:
                    import pyarrow as pa
                    schema = pa.schema([
                        pa.field("doc_id", pa.string()),
                        pa.field("vector", pa.list_(pa.float32(), 768)),
                        pa.field("title", pa.string()),
                        pa.field("source", pa.string()),
                    ])
                    self.vector_table = self.vector_db.create_table("documents", schema=schema)
            except Exception as e:
                print(f"LanceDB init failed: {e}")
                self.vector_db = None
                self.vector_table = None
        else:
            self.vector_db = None
            self.vector_table = None
    
    def _get_embedding_model(self):
        """Lazy load embedding model."""
        if self._embedding_model is None and SentenceTransformer is not None:
            try:
                # Use local model, fallback to nomic-embed-text compatible
                model_path = self.data_dir / "models" / "nomic-embed-text"
                if model_path.exists():
                    self._embedding_model = SentenceTransformer(str(model_path))
                else:
                    # Download on first run (requires internet once)
                    self._embedding_model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
                    self._embedding_model.save(str(model_path))
            except Exception as e:
                print(f"Embedding model load failed: {e}")
                self._embedding_model = False
        return self._embedding_model if self._embedding_model is not False else None
    
    def add_document(self, doc: OfflineDocument) -> bool:
        """Add document to both SQLite and vector DB."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)",
                (doc.doc_id, doc.title, doc.content, doc.source.value, doc.url,
                 json.dumps(doc.metadata), doc.timestamp)
            )
            # Update FTS
            conn.execute(
                "INSERT OR REPLACE INTO documents_fts(rowid, title, content, metadata) "
                "SELECT rowid, title, content, metadata FROM documents WHERE doc_id = ?",
                (doc.doc_id,)
            )
            conn.commit()
        except Exception as e:
            print(f"SQLite insert failed: {e}")
            conn.close()
            return False
        conn.close()
        
        # Add to vector DB
        if self.vector_table is not None and doc.embedding:
            try:
                self.vector_table.add([{
                    "doc_id": doc.doc_id,
                    "vector": doc.embedding,
                    "title": doc.title,
                    "source": doc.source.value
                }])
            except Exception as e:
                print(f"Vector DB insert failed: {e}")
        
        return True
    
    def search_fts(self, query: str, limit: int = 20, source: DataSource = None) -> List[OfflineDocument]:
        """Full-text search using SQLite FTS5."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        where_clause = ""
        params = [query, limit]
        if source:
            where_clause = " AND source = ?"
            params.insert(-1, source.value)
        
        try:
            cursor = conn.execute(f"""
                SELECT d.* FROM documents d
                JOIN documents_fts f ON d.rowid = f.rowid
                WHERE documents_fts MATCH ? {where_clause}
                ORDER BY rank
                LIMIT ?
            """, params)
            rows = cursor.fetchall()
        except Exception as e:
            print(f"FTS search failed: {e}")
            rows = []
        conn.close()
        
        return [self._row_to_doc(row) for row in rows]
    
    def search_vector(self, query: str, limit: int = 20, source: DataSource = None) -> List[OfflineDocument]:
        """Semantic vector search using LanceDB."""
        if self.vector_table is None:
            return []
        
        model = self._get_embedding_model()
        if model is None:
            return []
        
        try:
            query_embedding = model.encode(query).tolist()
            
            where_clause = f"source = '{source.value}'" if source else None
            
            results = self.vector_table.search(query_embedding).limit(limit)
            if where_clause:
                results = results.where(where_clause)
            
            results = results.to_list()
            
            # Fetch full documents from SQLite
            doc_ids = [r["doc_id"] for r in results]
            if not doc_ids:
                return []
            
            placeholders = ",".join("?" * len(doc_ids))
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"SELECT * FROM documents WHERE doc_id IN ({placeholders})", doc_ids)
            rows = cursor.fetchall()
            conn.close()
            
            doc_map = {row["doc_id"]: self._row_to_doc(row) for row in rows}
            return [doc_map[doc_id] for doc_id in doc_ids if doc_id in doc_map]
            
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []
    
    def hybrid_search(self, query: str, limit: int = 20, source: DataSource = None, 
                      alpha: float = 0.5) -> List[OfflineDocument]:
        """Combine FTS and vector search with reciprocal rank fusion."""
        fts_results = self.search_fts(query, limit * 2, source)
        vec_results = self.search_vector(query, limit * 2, source)
        
        # Reciprocal Rank Fusion
        scores = {}
        for rank, doc in enumerate(fts_results):
            scores[doc.doc_id] = scores.get(doc.doc_id, 0) + 1.0 / (rank + 1 + 60) * alpha
        for rank, doc in enumerate(vec_results):
            scores[doc.doc_id] = scores.get(doc.doc_id, 0) + 1.0 / (rank + 1 + 60) * (1 - alpha)
        
        # Get all unique docs
        all_docs = {doc.doc_id: doc for doc in fts_results + vec_results}
        sorted_ids = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        
        return [all_docs[doc_id] for doc_id in sorted_ids[:limit] if doc_id in all_docs]
    
    def _row_to_doc(self, row: sqlite3.Row) -> OfflineDocument:
        return OfflineDocument(
            doc_id=row["doc_id"],
            title=row["title"],
            content=row["content"],
            source=DataSource(row["source"]),
            url=row["url"] or "",
            metadata=json.loads(row["metadata"] or "{}"),
            timestamp=row["timestamp"]
        )
    
    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT source, COUNT(*) as count FROM documents GROUP BY source")
        stats = {row[0]: row[1] for row in cursor.fetchall()}
        cursor = conn.execute("SELECT COUNT(*) FROM documents")
        stats["total"] = cursor.fetchone()[0]
        conn.close()
        return stats


class DatasetDownloader:
    """Downloads and prepares offline datasets."""
    
    DATASETS = {
        "wikipedia_mini": {
            "url": "https://huggingface.co/datasets/wikimedia/wikipedia/resolve/main/20231101.en/part-00000.parquet",
            "size_gb": 2.5,
            "description": "Wikipedia 2023 snapshot (first shard, ~1M articles)"
        },
        "wikipedia_abstracts": {
            "url": "https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract.xml.gz",
            "size_gb": 1.2,
            "description": "Wikipedia article abstracts only"
        },
        "arxiv_metadata": {
            "url": "https://huggingface.co/datasets/Cornell-University/arxiv/resolve/main/arxiv-metadata-oai-snapshot.json",
            "size_gb": 3.5,
            "description": "arXiv paper metadata (2M+ papers)"
        },
        "simple_wikipedia": {
            "url": "https://huggingface.co/datasets/wikimedia/wikipedia/resolve/main/20231101.simple/part-00000.parquet",
            "size_gb": 0.3,
            "description": "Simple English Wikipedia (~200K articles)"
        }
    }
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.download_dir = data_dir / "downloads"
        self.download_dir.mkdir(exist_ok=True)
    
    def download_dataset(self, name: str, progress_callback=None) -> bool:
        """Download a dataset with progress tracking."""
        if name not in self.DATASETS:
            return False
        
        info = self.DATASETS[name]
        url = info["url"]
        dest = self.download_dir / f"{name}.tmp"
        final = self.download_dir / Path(url).name
        
        try:
            import requests
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                downloaded = 0
                with open(dest, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(downloaded / total)
            
            dest.rename(final)
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            if dest.exists():
                dest.unlink()
            return False
    
    def process_wikipedia_abstracts(self, manager: OfflineDataManager, max_articles: int = 100000):
        """Process Wikipedia abstracts XML into documents."""
        import xml.etree.ElementTree as ET
        import gzip
        
        xml_file = self.download_dir / "enwiki-latest-abstract.xml.gz"
        if not xml_file.exists():
            print("Abstracts file not found")
            return 0
        
        count = 0
        batch = []
        
        with gzip.open(xml_file, 'rt', encoding='utf-8') as f:
            for event, elem in ET.iterparse(f, events=('end',)):
                if elem.tag == 'doc':
                    title = elem.findtext('title', '')
                    url = elem.findtext('url', '')
                    abstract = elem.findtext('abstract', '')
                    
                    if abstract and len(abstract) > 100:
                        doc_id = hashlib.sha256(title.encode()).hexdigest()[:16]
                        doc = OfflineDocument(
                            doc_id=doc_id,
                            title=title,
                            content=abstract,
                            source=DataSource.WIKIPEDIA,
                            url=url,
                            metadata={"type": "abstract"}
                        )
                        batch.append(doc)
                        count += 1
                        
                        if len(batch) >= 100:
                            for d in batch:
                                manager.add_document(d)
                            batch = []
                        
                        if count >= max_articles:
                            break
                    elem.clear()
        
        if batch:
            for d in batch:
                manager.add_document(d)
        
        return count


# Singleton instance
_offline_manager: Optional[OfflineDataManager] = None


def get_offline_manager(data_dir: str = None) -> OfflineDataManager:
    global _offline_manager
    if _offline_manager is None:
        _offline_manager = OfflineDataManager(data_dir)
    return _offline_manager