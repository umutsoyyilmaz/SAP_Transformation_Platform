"""
SAP Transformation Management Platform
RAG Pipeline — Sprint 7.

Entity-aware chunking + hybrid search (semantic + keyword).

Features:
    - Entity-aware chunking strategies per model type
    - Embedding generation (via LLM Gateway)
    - Hybrid search: semantic (cosine) + keyword (FTS) + RRF fusion
    - Batch indexing for bulk operations

Usage:
    from app.ai.rag import RAGPipeline
    rag = RAGPipeline(gateway)
    rag.index_entity("requirement", req_id, chunk_text, program_id=1)
    results = rag.search("payment posting error", program_id=1, top_k=5)
"""

import json
import logging
import math
import re
from collections import defaultdict

from app.models import db
from app.models.ai import AIEmbedding

logger = logging.getLogger(__name__)

# ── Chunking Constants ────────────────────────────────────────────────────────

MAX_CHUNK_TOKENS = 512        # Max tokens per chunk (approx words × 1.3)
OVERLAP_TOKENS = 64           # Overlap between consecutive chunks
EMBEDDING_DIM = 1536          # text-embedding-3-small dimension


# ── Chunking Engine ───────────────────────────────────────────────────────────

class ChunkingEngine:
    """
    Entity-aware chunking — different strategies for different entity types.

    Each entity type has a custom extractor that produces structured text
    optimised for semantic search.
    """

    @staticmethod
    def chunk_entity(entity_type: str, entity_data: dict) -> list[dict]:
        """
        Generate chunks from an entity.

        Args:
            entity_type: One of requirement, backlog_item, risk, config_item,
                         test_case, defect, scenario, scope_item, process.
            entity_data: Dict of entity fields.

        Returns:
            List of dicts: [{text, chunk_index, module, phase, metadata}]
        """
        extractor = ENTITY_EXTRACTORS.get(entity_type, _extract_generic)
        full_text = extractor(entity_data)
        module = entity_data.get("module", "")
        phase = entity_data.get("phase", "")

        chunks = ChunkingEngine._split_text(full_text)
        return [
            {
                "text": chunk,
                "chunk_index": i,
                "module": module,
                "phase": phase,
                "metadata": json.dumps({
                    "entity_type": entity_type,
                    "entity_id": entity_data.get("id"),
                    "title": entity_data.get("title", entity_data.get("name", ""))[:200],
                }),
            }
            for i, chunk in enumerate(chunks)
        ]

    @staticmethod
    def _split_text(text: str, max_tokens: int = MAX_CHUNK_TOKENS,
                    overlap: int = OVERLAP_TOKENS) -> list[str]:
        """Split text into overlapping chunks by approximate token count."""
        words = text.split()
        if not words:
            return [text] if text.strip() else []

        # Approximate tokens (1 word ≈ 1.3 tokens)
        max_words = int(max_tokens / 1.3)
        overlap_words = int(overlap / 1.3)

        if len(words) <= max_words:
            return [text]

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + max_words, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start = end - overlap_words
            if start >= len(words) - overlap_words:
                break

        return chunks if chunks else [text]


# ── Entity Text Extractors ───────────────────────────────────────────────────

def _extract_requirement(data: dict) -> str:
    parts = [
        f"Requirement: {data.get('title', '')}",
        f"Code: {data.get('code', '')}",
        f"Type: {data.get('requirement_type', '')}",
        f"Priority: {data.get('priority', '')}",
        f"Module: {data.get('module', '')}",
        f"Fit/Gap: {data.get('fit_gap', data.get('fit_gap_status', ''))}",
        f"Description: {data.get('description', '')}",
        f"Acceptance Criteria: {data.get('acceptance_criteria', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _extract_backlog_item(data: dict) -> str:
    parts = [
        f"WRICEF Item: {data.get('title', '')}",
        f"Code: {data.get('code', '')}",
        f"Type: {data.get('wricef_type', '')} ({data.get('object_type', '')})",
        f"Module: {data.get('module', '')}",
        f"Status: {data.get('status', '')}",
        f"Priority: {data.get('priority', '')}",
        f"Description: {data.get('description', '')}",
        f"Complexity: {data.get('complexity', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _extract_risk(data: dict) -> str:
    parts = [
        f"Risk: {data.get('title', '')}",
        f"Code: {data.get('code', '')}",
        f"Category: {data.get('category', '')}",
        f"Probability: {data.get('probability', '')}, Impact: {data.get('impact', '')}",
        f"Risk Score: {data.get('risk_score', '')}",
        f"RAG: {data.get('rag_status', '')}",
        f"Description: {data.get('description', '')}",
        f"Mitigation: {data.get('mitigation_plan', '')}",
        f"Response: {data.get('response_strategy', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _extract_test_case(data: dict) -> str:
    parts = [
        f"Test Case: {data.get('title', '')}",
        f"Code: {data.get('code', '')}",
        f"Layer: {data.get('test_layer', '')}",
        f"Module: {data.get('module', '')}",
        f"Description: {data.get('description', '')}",
        f"Preconditions: {data.get('preconditions', '')}",
        f"Test Steps: {data.get('test_steps', '')}",
        f"Expected Result: {data.get('expected_result', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _extract_defect(data: dict) -> str:
    parts = [
        f"Defect: {data.get('title', '')}",
        f"Code: {data.get('code', '')}",
        f"Severity: {data.get('severity', '')}",
        f"Module: {data.get('module', '')}",
        f"Status: {data.get('status', '')}",
        f"Description: {data.get('description', '')}",
        f"Steps to Reproduce: {data.get('steps_to_reproduce', '')}",
        f"Resolution: {data.get('resolution', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _extract_config_item(data: dict) -> str:
    parts = [
        f"Config Item: {data.get('name', '')}",
        f"Module: {data.get('module', '')}",
        f"Config Key: {data.get('config_key', '')}",
        f"Transaction: {data.get('transaction', '')}",
        f"Description: {data.get('description', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _extract_scenario(data: dict) -> str:
    parts = [
        f"Scenario: {data.get('name', '')}",
        f"Approach: {data.get('approach', '')}",
        f"Description: {data.get('description', '')}",
        f"Benefits: {data.get('benefits', '')}",
        f"Risks: {data.get('risks', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _extract_scope_item(data: dict) -> str:
    parts = [
        f"Scope Item: {data.get('name', '')}",
        f"Code: {data.get('code', '')}",
        f"Module: {data.get('module', '')}",
        f"Type: {data.get('item_type', '')}",
        f"Fit/Gap: {data.get('fit_gap', data.get('fit_gap_status', ''))}",
        f"Description: {data.get('description', '')}",
    ]
    return "\n".join(p for p in parts if not p.endswith(": "))


def _extract_generic(data: dict) -> str:
    """Fallback extractor — concatenate key fields."""
    parts = []
    for key in ["title", "name", "code", "description", "module", "status", "type"]:
        val = data.get(key, "")
        if val:
            parts.append(f"{key.replace('_', ' ').title()}: {val}")
    return "\n".join(parts) or str(data)[:1000]


# Entity type → extractor function mapping
ENTITY_EXTRACTORS = {
    "requirement": _extract_requirement,
    "backlog_item": _extract_backlog_item,
    "risk": _extract_risk,
    "test_case": _extract_test_case,
    "defect": _extract_defect,
    "config_item": _extract_config_item,
    "scenario": _extract_scenario,
    "scope_item": _extract_scope_item,
}


# ── RAG Pipeline ──────────────────────────────────────────────────────────────

class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.

    Handles indexing (chunk + embed + store) and searching (hybrid retrieval).
    """

    def __init__(self, gateway=None):
        """
        Args:
            gateway: LLMGateway instance for embedding calls.
                     If None, embeddings must be provided externally.
        """
        self.gateway = gateway
        self.chunker = ChunkingEngine()

    # ── Indexing ──────────────────────────────────────────────────────────

    def index_entity(
        self,
        entity_type: str,
        entity_id: int,
        entity_data: dict,
        program_id: int | None = None,
        embed: bool = True,
    ) -> list[AIEmbedding]:
        """
        Chunk an entity, generate embeddings, and store in vector DB.

        Args:
            entity_type: Entity type string.
            entity_id: Entity primary key.
            entity_data: Full entity dict.
            program_id: Program association.
            embed: Whether to generate embeddings (requires gateway).

        Returns:
            List of created AIEmbedding records.
        """
        # Remove old embeddings for this entity
        AIEmbedding.query.filter_by(
            entity_type=entity_type, entity_id=entity_id,
        ).delete()

        # Generate chunks
        chunks = self.chunker.chunk_entity(entity_type, entity_data)
        if not chunks:
            db.session.commit()
            return []

        # Generate embeddings if gateway available
        embeddings_vectors = None
        if embed and self.gateway:
            try:
                texts = [c["text"] for c in chunks]
                embeddings_vectors = self.gateway.embed(
                    texts, purpose="rag_indexing", program_id=program_id,
                )
            except Exception as e:
                logger.warning("Embedding generation failed, storing without vectors: %s", e)

        # Store chunks
        records = []
        for i, chunk in enumerate(chunks):
            vec_json = None
            if embeddings_vectors and i < len(embeddings_vectors):
                vec_json = json.dumps(embeddings_vectors[i])

            rec = AIEmbedding(
                entity_type=entity_type,
                entity_id=entity_id,
                program_id=program_id,
                chunk_text=chunk["text"],
                chunk_index=chunk["chunk_index"],
                embedding_json=vec_json,
                module=chunk.get("module", ""),
                phase=chunk.get("phase", ""),
                metadata_json=chunk.get("metadata", "{}"),
            )
            db.session.add(rec)
            records.append(rec)

        db.session.commit()
        return records

    def batch_index(
        self,
        entities: list[dict],
        program_id: int | None = None,
        embed: bool = True,
    ) -> int:
        """
        Index multiple entities in batch.

        Args:
            entities: List of {"entity_type": ..., "entity_id": ..., "data": {...}}
            program_id: Default program association.
            embed: Generate embeddings.

        Returns:
            Total number of chunks created.
        """
        total = 0
        for ent in entities:
            recs = self.index_entity(
                entity_type=ent["entity_type"],
                entity_id=ent["entity_id"],
                entity_data=ent["data"],
                program_id=ent.get("program_id", program_id),
                embed=embed,
            )
            total += len(recs)
        return total

    # ── Search ────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        *,
        program_id: int | None = None,
        entity_type: str | None = None,
        module: str | None = None,
        top_k: int = 10,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> list[dict]:
        """
        Hybrid search: semantic similarity + keyword matching with RRF fusion.

        Args:
            query: Natural language search query.
            program_id: Filter by program.
            entity_type: Filter by entity type.
            module: Filter by SAP module.
            top_k: Number of results to return.
            semantic_weight: Weight for semantic similarity scores.
            keyword_weight: Weight for keyword matching scores.

        Returns:
            List of result dicts sorted by combined score.
        """
        # Build base query with filters
        base_q = AIEmbedding.query
        if program_id:
            base_q = base_q.filter(AIEmbedding.program_id == program_id)
        if entity_type:
            base_q = base_q.filter(AIEmbedding.entity_type == entity_type)
        if module:
            base_q = base_q.filter(AIEmbedding.module == module)

        candidates = base_q.all()
        if not candidates:
            return []

        # Semantic search scores
        semantic_scores = {}
        query_vec = None
        if self.gateway:
            try:
                query_vecs = self.gateway.embed([query], purpose="rag_search")
                query_vec = query_vecs[0] if query_vecs else None
            except Exception as e:
                logger.warning("Query embedding failed: %s", e)

        if query_vec:
            for emb in candidates:
                if emb.embedding_json:
                    try:
                        emb_vec = json.loads(emb.embedding_json)
                        sim = _cosine_similarity(query_vec, emb_vec)
                        semantic_scores[emb.id] = sim
                    except (json.JSONDecodeError, ValueError):
                        pass

        # Keyword search scores (BM25-like)
        keyword_scores = _keyword_search(query, candidates)

        # RRF (Reciprocal Rank Fusion) combination
        combined = _rrf_fusion(
            semantic_scores, keyword_scores,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
        )

        # Sort by combined score, take top_k
        sorted_results = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Build result objects
        emb_map = {e.id: e for e in candidates}
        results = []
        for emb_id, score in sorted_results:
            emb = emb_map.get(emb_id)
            if emb:
                results.append({
                    "id": emb.id,
                    "entity_type": emb.entity_type,
                    "entity_id": emb.entity_id,
                    "program_id": emb.program_id,
                    "chunk_text": emb.chunk_text,
                    "module": emb.module,
                    "phase": emb.phase,
                    "score": round(score, 4),
                    "semantic_score": round(semantic_scores.get(emb.id, 0.0), 4),
                    "keyword_score": round(keyword_scores.get(emb.id, 0.0), 4),
                    "metadata": emb.metadata_json,
                })

        return results

    # ── Statistics ────────────────────────────────────────────────────────

    @staticmethod
    def get_index_stats(program_id: int | None = None) -> dict:
        """Get embedding index statistics."""
        base_q = AIEmbedding.query
        if program_id:
            base_q = base_q.filter(AIEmbedding.program_id == program_id)

        total = base_q.count()
        with_embedding = base_q.filter(AIEmbedding.embedding_json.isnot(None)).count()

        # Group by entity type
        type_counts = {}
        for row in db.session.query(
            AIEmbedding.entity_type,
            db.func.count(AIEmbedding.id),
        ).group_by(AIEmbedding.entity_type).all():
            type_counts[row[0]] = row[1]

        return {
            "total_chunks": total,
            "with_embeddings": with_embedding,
            "without_embeddings": total - with_embedding,
            "by_entity_type": type_counts,
        }


# ── Helper Functions ──────────────────────────────────────────────────────────

def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _keyword_search(query: str, candidates: list[AIEmbedding]) -> dict[int, float]:
    """
    BM25-like keyword scoring.

    Tokenizes query and chunk texts, computes TF-IDF-like score.
    """
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return {}

    # Document frequency
    df = defaultdict(int)
    doc_tokens_map = {}
    for emb in candidates:
        tokens = _tokenize(emb.chunk_text)
        doc_tokens_map[emb.id] = tokens
        for t in set(tokens):
            df[t] += 1

    n = len(candidates)
    scores = {}
    for emb in candidates:
        tokens = doc_tokens_map[emb.id]
        if not tokens:
            continue

        # BM25 score
        score = 0.0
        tf_map = defaultdict(int)
        for t in tokens:
            tf_map[t] += 1

        avg_dl = sum(len(doc_tokens_map[e.id]) for e in candidates) / max(n, 1)
        k1 = 1.2
        b = 0.75
        dl = len(tokens)

        for qt in query_tokens:
            if qt in tf_map:
                tf = tf_map[qt]
                idf = math.log((n - df.get(qt, 0) + 0.5) / (df.get(qt, 0) + 0.5) + 1)
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / max(avg_dl, 1)))
                score += idf * tf_norm

        if score > 0:
            scores[emb.id] = score

    # Normalize to [0, 1]
    max_score = max(scores.values()) if scores else 1.0
    return {k: v / max_score for k, v in scores.items()}


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer, lowercased."""
    return re.findall(r'\b\w+\b', text.lower())


def _rrf_fusion(
    scores_a: dict[int, float],
    scores_b: dict[int, float],
    *,
    semantic_weight: float = 0.6,
    keyword_weight: float = 0.4,
    k: int = 60,
) -> dict[int, float]:
    """
    Reciprocal Rank Fusion for combining two ranked lists.

    RRF score = Σ weight / (k + rank)
    """
    all_ids = set(scores_a.keys()) | set(scores_b.keys())
    if not all_ids:
        return {}

    # Build rank lists
    rank_a = _scores_to_ranks(scores_a)
    rank_b = _scores_to_ranks(scores_b)

    combined = {}
    for doc_id in all_ids:
        score = 0.0
        if doc_id in rank_a:
            score += semantic_weight / (k + rank_a[doc_id])
        if doc_id in rank_b:
            score += keyword_weight / (k + rank_b[doc_id])
        combined[doc_id] = score

    return combined


def _scores_to_ranks(scores: dict[int, float]) -> dict[int, int]:
    """Convert score dict to rank dict (1-based)."""
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return {doc_id: rank + 1 for rank, (doc_id, _) in enumerate(sorted_items)}
