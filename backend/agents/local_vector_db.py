"""
Local Vector Database Abstraction Layer.
Supports multiple backends: LanceDB, ChromaDB, FAISS, SQLite-Vec.
Automatically selects best available backend.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import threading

try:
    import lancedb
    import pyarrow as pa
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    import sqlite_vec
    SQLITE_VEC_AVAILABLE = True
except ImportError:
    SQLITE_VEC_AVAILABLE = False


@dataclass
class VectorDocument:
    id: str
    vector: List[float]
    metadata: Dict[str, Any]
    text: str = ""


class VectorBackend(ABC):
    """Abstract base class for vector backends."""
    
    @abstractmethod
    def add(self, docs: List[VectorDocument]) -> bool:
        pass
    
    @abstractmethod
    def search(self, query_vector: List[float], k: int = 10, 
               filter: Dict = None) -> List[Tuple[VectorDocument, float]]:
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        pass
    
    @abstractmethod
    def count(self) -> int:
        pass
    
    @abstractmethod
    def close(self):
        pass


class LanceDBBackend(VectorBackend):
    """LanceDB backend - best for persistent, scalable vector search."""
    
    def __init__(self, path: str, table_name: str = "vectors", dim: int = 768):
        self.path = path
        self.table_name = table_name
        self.dim = dim
        self.db = None
        self.table = None
        self._init_db()
    
    def _init_db(self):
        self.db = lancedb.connect(self.path)
        try:
            self.table = self.db.open_table(self.table_name)
        except Exception:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), self.dim)),
                pa.field("text", pa.string()),
                pa.field("metadata", pa.string()),
            ])
            self.table = self.db.create_table(self.table_name, schema=schema)
    
    def add(self, docs: List[VectorDocument]) -> bool:
        try:
            data = [{
                "id": d.id,
                "vector": d.vector,
                "text": d.text,
                "metadata": json.dumps(d.metadata)
            } for d in docs]
            self.table.add(data)
            return True
        except Exception as e:
            print(f"LanceDB add failed: {e}")
            return False
    
    def search(self, query_vector: List[float], k: int = 10, 
               filter: Dict = None) -> List[Tuple[VectorDocument, float]]:
        try:
            query = self.table.search(query_vector).limit(k)
            if filter:
                # LanceDB filter syntax
                filter_str = " AND ".join([f"metadata LIKE '%{k}%'" for k in filter.keys()])
                query = query.where(filter_str)
            results = query.to_list()
            return [(
                VectorDocument(
                    id=r["id"],
                    vector=r["vector"],
                    text=r["text"],
                    metadata=json.loads(r["metadata"])
                ),
                r.get("_distance", 0)
            ) for r in results]
        except Exception as e:
            print(f"LanceDB search failed: {e}")
            return []
    
    def delete(self, ids: List[str]) -> bool:
        try:
            self.table.delete(f"id IN ({','.join(['?']*len(ids))})", ids)
            return True
        except Exception as e:
            print(f"LanceDB delete failed: {e}")
            return False
    
    def count(self) -> int:
        try:
            return self.table.count_rows()
        except Exception:
            return 0
    
    def close(self):
        pass  # LanceDB handles connection pooling


class ChromaDBBackend(VectorBackend):
    """ChromaDB backend - good for development and small datasets."""
    
    def __init__(self, path: str, collection_name: str = "vectors"):
        self.path = path
        self.client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def add(self, docs: List[VectorDocument]) -> bool:
        try:
            self.collection.add(
                ids=[d.id for d in docs],
                embeddings=[d.vector for d in docs],
                documents=[d.text for d in docs],
                metadatas=[d.metadata for d in docs]
            )
            return True
        except Exception as e:
            print(f"ChromaDB add failed: {e}")
            return False
    
    def search(self, query_vector: List[float], k: int = 10,
               filter: Dict = None) -> List[Tuple[VectorDocument, float]]:
        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=k,
                where=filter
            )
            docs = []
            for i, doc_id in enumerate(results["ids"][0]):
                docs.append((
                    VectorDocument(
                        id=doc_id,
                        vector=results["embeddings"][0][i] if "embeddings" in results else [],
                        text=results["documents"][0][i],
                        metadata=results["metadatas"][0][i]
                    ),
                    results["distances"][0][i]
                ))
            return docs
        except Exception as e:
            print(f"ChromaDB search failed: {e}")
            return []
    
    def delete(self, ids: List[str]) -> bool:
        try:
            self.collection.delete(ids=ids)
            return True
        except Exception as e:
            print(f"ChromaDB delete failed: {e}")
            return False
    
    def count(self) -> int:
        return self.collection.count()
    
    def close(self):
        pass


class FAISSBackend(VectorBackend):
    """FAISS backend - fastest for in-memory search, no persistence by default."""
    
    def __init__(self, path: str, dim: int = 768, index_type: str = "HNSW"):
        self.path = Path(path)
        self.dim = dim
        self.index_type = index_type
        self.index = None
        self.id_map = {}  # faiss_id -> VectorDocument
        self.reverse_map = {}  # doc_id -> faiss_id
        self.next_faiss_id = 0
        self._init_index()
        self._load()
    
    def _init_index(self):
        if self.index_type == "HNSW":
            self.index = faiss.IndexHNSWFlat(self.dim, 32)
            self.index.hnsw.efConstruction = 200
            self.index.hnsw.efSearch = 128
        elif self.index_type == "IVF":
            quantizer = faiss.IndexFlatIP(self.dim)
            self.index = faiss.IndexIVFFlat(quantizer, self.dim, 100, faiss.METRIC_INNER_PRODUCT)
        else:
            self.index = faiss.IndexFlatIP(self.dim)
    
    def _save(self):
        self.path.mkdir(exist_ok=True)
        faiss.write_index(self.index, str(self.path / "faiss.index"))
        with open(self.path / "id_map.json", "w") as f:
            json.dump({str(k): v for k, v in self.id_map.items()}, f)
        with open(self.path / "reverse_map.json", "w") as f:
            json.dump(self.reverse_map, f)
        with open(self.path / "next_id.json", "w") as f:
            json.dump({"next_faiss_id": self.next_faiss_id}, f)
    
    def _load(self):
        index_file = self.path / "faiss.index"
        if index_file.exists():
            self.index = faiss.read_index(str(index_file))
            with open(self.path / "id_map.json") as f:
                self.id_map = {int(k): v for k, v in json.load(f).items()}
            with open(self.path / "reverse_map.json") as f:
                self.reverse_map = json.load(f)
            with open(self.path / "next_id.json") as f:
                self.next_faiss_id = json.load(f)["next_faiss_id"]
    
    def add(self, docs: List[VectorDocument]) -> bool:
        try:
            vectors = np.array([d.vector for d in docs], dtype=np.float32)
            
            # Normalize for cosine similarity
            faiss.normalize_L2(vectors)
            
            if hasattr(self.index, 'train') and not self.index.is_trained:
                self.index.train(vectors)
            
            faiss_ids = []
            for doc in docs:
                faiss_id = self.next_faiss_id
                self.next_faiss_id += 1
                self.id_map[faiss_id] = doc
                self.reverse_map[doc.id] = faiss_id
                faiss_ids.append(faiss_id)
            
            self.index.add_with_ids(vectors, np.array(faiss_ids, dtype=np.int64))
            self._save()
            return True
        except Exception as e:
            print(f"FAISS add failed: {e}")
            return False
    
    def search(self, query_vector: List[float], k: int = 10,
               filter: Dict = None) -> List[Tuple[VectorDocument, float]]:
        try:
            query_vec = np.array([query_vector], dtype=np.float32)
            faiss.normalize_L2(query_vec)
            
            distances, indices = self.index.search(query_vec, k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:
                    continue
                doc = self.id_map.get(int(idx))
                if doc:
                    # Apply filter if needed
                    if filter:
                        match = all(doc.metadata.get(k) == v for k, v in filter.items())
                        if not match:
                            continue
                    results.append((doc, float(dist)))
            return results
        except Exception as e:
            print(f"FAISS search failed: {e}")
            return []
    
    def delete(self, ids: List[str]) -> bool:
        # FAISS doesn't support efficient deletion, mark as deleted
        try:
            for doc_id in ids:
                if doc_id in self.reverse_map:
                    faiss_id = self.reverse_map.pop(doc_id)
                    self.id_map.pop(faiss_id, None)
            self._save()
            return True
        except Exception as e:
            print(f"FAISS delete failed: {e}")
            return False
    
    def count(self) -> int:
        return self.index.ntotal if self.index else 0
    
    def close(self):
        self._save()


class SQLiteVecBackend(VectorBackend):
    """SQLite-Vec backend - pure SQLite with vector extension."""
    
    def __init__(self, path: str, table_name: str = "vectors", dim: int = 768):
        self.path = path
        self.table_name = table_name
        self.dim = dim
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        self.conn = sqlite3.connect(self.path)
        self.conn.enable_load_extension(True)
        try:
            sqlite_vec.load(self.conn)
        except Exception:
            pass
        self.conn.enable_load_extension(False)
        
        self.conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {self.table_name} 
            USING vec0(
                id TEXT PRIMARY KEY,
                vector FLOAT[{self.dim}],
                text TEXT,
                metadata TEXT
            )
        """)
        self.conn.commit()
    
    def add(self, docs: List[VectorDocument]) -> bool:
        try:
            for doc in docs:
                self.conn.execute(
                    f"INSERT OR REPLACE INTO {self.table_name} VALUES (?, ?, ?, ?)",
                    (doc.id, json.dumps(doc.vector), doc.text, json.dumps(doc.metadata))
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite-Vec add failed: {e}")
            return False
    
    def search(self, query_vector: List[float], k: int = 10,
               filter: Dict = None) -> List[Tuple[VectorDocument, float]]:
        try:
            query_json = json.dumps(query_vector)
            cursor = self.conn.execute(f"""
                SELECT id, vector, text, metadata, distance
                FROM {self.table_name}
                WHERE vector MATCH ?
                AND k = ?
                ORDER BY distance
            """, (query_json, k))
            
            results = []
            for row in cursor.fetchall():
                doc = VectorDocument(
                    id=row[0],
                    vector=json.loads(row[1]),
                    text=row[2],
                    metadata=json.loads(row[3])
                )
                # Apply filter
                if filter:
                    match = all(doc.metadata.get(k) == v for k, v in filter.items())
                    if not match:
                        continue
                results.append((doc, row[4]))
            return results
        except Exception as e:
            print(f"SQLite-Vec search failed: {e}")
            return []
    
    def delete(self, ids: List[str]) -> bool:
        try:
            placeholders = ",".join("?" * len(ids))
            self.conn.execute(f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})", ids)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite-Vec delete failed: {e}")
            return False
    
    def count(self) -> int:
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {self.table_name}")
        return cursor.fetchone()[0]
    
    def close(self):
        if self.conn:
            self.conn.close()


class VectorDB:
    """Auto-selecting vector database with fallback chain."""
    
    BACKEND_PRIORITY = [
        ("lancedb", LanceDBBackend, LANCEDB_AVAILABLE),
        ("chromadb", ChromaDBBackend, CHROMADB_AVAILABLE),
        ("faiss", FAISSBackend, FAISS_AVAILABLE),
        ("sqlite_vec", SQLiteVecBackend, SQLITE_VEC_AVAILABLE),
    ]
    
    def __init__(self, path: str, dim: int = 768, preferred: str = None):
        self.path = Path(path)
        self.dim = dim
        self.backend: Optional[VectorBackend] = None
        self.backend_name = None
        self._init_backend(preferred)
    
    def _init_backend(self, preferred: str = None):
        backends = self.BACKEND_PRIORITY
        if preferred:
            backends = [(n, c, a) for n, c, a in backends if n == preferred] + \
                       [(n, c, a) for n, c, a in backends if n != preferred]
        
        for name, backend_class, available in backends:
            if not available:
                continue
            try:
                backend_path = self.path / name
                backend_path.mkdir(parents=True, exist_ok=True)
                self.backend = backend_class(str(backend_path), dim=self.dim)
                self.backend_name = name
                print(f"VectorDB: Using {name} backend at {backend_path}")
                return
            except Exception as e:
                print(f"VectorDB: {name} backend failed: {e}")
        
        raise RuntimeError("No vector backend available. Install lancedb, chromadb, faiss, or sqlite-vec")
    
    def add(self, docs: List[VectorDocument]) -> bool:
        return self.backend.add(docs)
    
    def search(self, query_vector: List[float], k: int = 10, 
               filter: Dict = None) -> List[Tuple[VectorDocument, float]]:
        return self.backend.search(query_vector, k, filter)
    
    def delete(self, ids: List[str]) -> bool:
        return self.backend.delete(ids)
    
    def count(self) -> int:
        return self.backend.count()
    
    def close(self):
        self.backend.close()


# Global instance
_vector_db: Optional[VectorDB] = None
_vector_db_lock = threading.Lock()


def get_vector_db(path: str = None, dim: int = 768) -> VectorDB:
    global _vector_db
    with _vector_db_lock:
        if _vector_db is None:
            _vector_db = VectorDB(path or "offline_data/vectors", dim)
        return _vector_db