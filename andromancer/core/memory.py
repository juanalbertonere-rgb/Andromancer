import json
import hashlib
import time
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any
from andromancer import config as cfg

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger("AndroMancer.Memory")

@dataclass
class Memory:
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_access: float = field(default_factory=time.time)

class MemoryStore:
    """Semantic memory with TF-IDF vectors for local semantic search"""
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.memories: List[Memory] = []
        self._load()

    def _hash_embedding(self, text: str) -> List[float]:
        """Legacy hash-based 'embedding' for backward compatibility"""
        hash_obj = hashlib.md5(text.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        vec = [((hash_int >> (i * 4)) & 0xF) / 16.0 for i in range(16)]
        return vec

    def store(self, content: str, metadata: Dict = None) -> Memory:
        # We store the hash embedding for compatibility but we will use TF-IDF for retrieval
        mem = Memory(
            id=hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:12],
            content=content,
            embedding=self._hash_embedding(content),
            metadata=metadata or {}
        )
        self.memories.append(mem)
        self._save()
        return mem

    def retrieve(self, query: str, top_k: int = 5) -> List[Memory]:
        if not self.memories:
            return []

        if HAS_SKLEARN and len(self.memories) > 1:
            try:
                # Local semantic search using TF-IDF with character n-grams for fuzzy matching
                documents = [m.content for m in self.memories]
                vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
                tfidf_matrix = vectorizer.fit_transform(documents)
                query_vec = vectorizer.transform([query])

                similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()

                # Get top_k indices
                related_docs_indices = similarities.argsort()[::-1][:top_k]

                results = []
                for idx in related_docs_indices:
                    if similarities[idx] > 0: # Only return somewhat relevant memories
                        mem = self.memories[idx]
                        results.append(mem)

                # Update access stats
                for m in results:
                    m.access_count += 1
                    m.last_access = time.time()

                return results
            except Exception as e:
                logger.error(f"TF-IDF retrieval failed, falling back to hash: {e}")

        # Fallback to legacy hash-based retrieval
        query_vec = self._hash_embedding(query)
        scored = []
        for mem in self.memories:
            # Simple cosine similarity on hash vectors
            sim = self._legacy_cosine_similarity(query_vec, mem.embedding)
            scored.append((sim, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [m for _, m in scored[:top_k]]

        for m in results:
            m.access_count += 1
            m.last_access = time.time()
        return results

    def _legacy_cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b: return 0
        dot = sum(x*y for x,y in zip(a,b))
        norm_a = sum(x*x for x in a) ** 0.5
        norm_b = sum(x*x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a * norm_b else 0

    def _save(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump([asdict(m) for m in self.memories], f)
        except Exception as e:
            logger.error(f"Memory save error: {e}")

    def _load(self):
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    self.memories = [Memory(**m) for m in data]
            except Exception as e:
                logger.error(f"Memory load error: {e}")

memory_store = MemoryStore(cfg.VECTOR_DB_PATH)
