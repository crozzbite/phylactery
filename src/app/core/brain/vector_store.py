"""
VectorStoreManager: Core component for Phase 5.1.1.
Handles Hybrid Search (Dense + Sparse) and memory persistence.
"""

from typing import Dict, Optional, TypedDict
from .config import get_pinecone_client, get_pinecone_index_name, get_pinecone_index_host

class MemoryItem(TypedDict):
    """Contract for a single memory record."""
    id: str
    content: str
    metadata: Dict[str, object]

class VectorStoreManager:
    """
    Manages long-term memory using Pinecone.
    Implemented with Hybrid Search (Dense + Sparse) support.
    """
    
    def __init__(self, index_name: Optional[str] = None):
        self.pc = get_pinecone_client()
        self.index_name = index_name or get_pinecone_index_name()
        
        # Latency Optimization: Target by Host directly if available
        # This avoids the extra 'describe_index' call during initialization
        index_host = get_pinecone_index_host()
        if index_host:
            self.index = self.pc.Index(host=index_host)
        else:
            self.index = self.pc.Index(self.index_name)
        
    def _generate_hybrid_vectors(self, texts: List[str]) -> List[Dict[str, List[float]]]:
        # ... (same implementation for integrated inference)
        # Using Pinecone Inference API to generate vectors
        dense_response = self.pc.inference.embed(
            model="multilingual-e5-large",
            inputs=texts,
            parameters={"input_type": "passage", "truncate": "END"}
        )
        
        sparse_response = self.pc.inference.embed(
            model="pinecone-sparse-english-v0",
            inputs=texts,
            parameters={"input_type": "passage", "truncate": "END"}
        )
        
        results = []
        for d, s in zip(dense_response, sparse_response):
            results.append({
                "dense": d.values,
                "sparse": {
                    "indices": s.sparse_indices,
                    "values": s.sparse_values
                }
            })
        return results

    def upsert_memory(
        self, 
        id: str, 
        content: str, 
        metadata: Dict[str, object], 
        namespace: str = "default"
    ) -> None:
        """
        Saves a memory chunk into the vector store.
        Throughput Optimization: Batching is recommended for multiple records.
        """
        vectors = self._generate_hybrid_vectors([content])[0]
        
        # Security: Ensure metadata is flat JSON
        metadata["content"] = content
        
        self.index.upsert(
            vectors=[{
                "id": id,
                "values": vectors["dense"],
                "sparse_values": vectors["sparse"],
                "metadata": metadata
            }],
            namespace=namespace
        )

    def batch_upsert_memory(
        self, 
        items: List[MemoryItem], 
        namespace: str = "default",
        batch_size: int = 90
    ) -> None:
        """
        Ingests multiple memories in batches.
        Throughput Optimization: Uses batches of 'batch_size' to maximize performance.
        """
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            contents = [item["content"] for item in batch]
            
            # Generate vectors for the entire batch in one call (or two: dense/sparse)
            vectors_batch = self._generate_hybrid_vectors(contents)
            
            upsert_data = []
            for j, item in enumerate(batch):
                metadata = item.get("metadata", {})
                metadata["content"] = item["content"]
                
                upsert_data.append({
                    "id": item["id"],
                    "values": vectors_batch[j]["dense"],
                    "sparse_values": vectors_batch[j]["sparse"],
                    "metadata": metadata
                })
            
            self.index.upsert(vectors=upsert_data, namespace=namespace)

    def query_memory(
        self, 
        query_text: str, 
        namespace: str = "default", 
        top_k: int = 10,
        alpha: float = 0.5,
        rerank: bool = False,
        rerank_top_n: int = 5,
        metadata_filter: Optional[Dict[str, object]] = None
    ) -> List[Dict[str, object]]:
        """
        Performs a Hybrid Search query with optional Reranking and Metadata Filtering.
        
        Args:
            query_text: The user input or search term.
            namespace: The isolation namespace (Latency boost).
            top_k: Initial recall set.
            alpha: Weighting (1.0 = Dense only, 0.0 = Sparse only).
            rerank: Whether to perform a second-pass reranking (Relevance boost).
            rerank_top_n: Number of reranked results to return.
            metadata_filter: Metadata filtering expression (Relevance/Latency boost).
            
        Returns:
            List of results with metadata and scores.
        """
        # Generate query vectors
        dense_q = self.pc.inference.embed(
            model="multilingual-e5-large",
            inputs=[query_text],
            parameters={"input_type": "query", "truncate": "END"}
        )[0]
        
        sparse_q = self.pc.inference.embed(
            model="pinecone-sparse-english-v0",
            inputs=[query_text],
            parameters={"input_type": "query", "truncate": "END"}
        )[0]
        
        # Apply weighting
        h_dense = [v * alpha for v in dense_q.values]
        h_sparse = {
            "indices": sparse_q.sparse_indices,
            "values": [v * (1 - alpha) for v in sparse_q.sparse_values]
        }
        
        # Performance: avoid include_values=True (default is False)
        results = self.index.query(
            namespace=namespace,
            top_k=top_k,
            vector=h_dense,
            sparse_vector=h_sparse,
            filter=metadata_filter,
            include_metadata=True
        )
        
        matches = results.to_dict()["matches"]
        
        if not rerank or not matches:
            return matches

        # Second Stage: Standalone Reranking (Standalone as requested)
        # We must provide 'content' as a top-level field for the reranker
        docs_for_rerank = [
            {
                "id": m["id"], 
                "content": m["metadata"]["content"], 
                "metadata": m["metadata"]
            } for m in matches
        ]

        reranked = self.pc.inference.rerank(
            model="bge-reranker-v2-m3",
            query=query_text,
            documents=docs_for_rerank,
            top_n=rerank_top_n,
            rank_fields=["content"],
            return_documents=True
        )
        
        results_formatted = []
        for hit in reranked.data:
            results_formatted.append({
                "id": hit.document["id"],
                "score": hit.score,
                "metadata": hit.document["metadata"]
            })
            
        return results_formatted
