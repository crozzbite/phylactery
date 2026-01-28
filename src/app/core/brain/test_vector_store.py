"""
Verification tests for VectorStoreManager and Hybrid Search.
Ensures connection, indexing, and retrieval are working correctly.
"""

import unittest
import os
from unittest.mock import MagicMock, patch
import os
# Set dummy environment variable before imports
os.environ["PINECONE_API_KEY"] = "dummy-key"

from src.app.core.brain.vector_store import VectorStoreManager

class TestVectorStoreManager(unittest.TestCase):
    
    def setUp(self):
        # Patch dependencies in the config module to avoid network calls and ValueError
        self.patcher_client = patch('src.app.core.brain.config.get_pinecone_client')
        self.patcher_name = patch('src.app.core.brain.config.get_pinecone_index_name')
        self.patcher_host = patch('src.app.core.brain.config.get_pinecone_index_host')
        
        self.mock_get_client = self.patcher_client.start()
        self.mock_get_name = self.patcher_name.start()
        self.mock_get_host = self.patcher_host.start()
        
        # Mock Pinecone client and index
        self.mock_pc = MagicMock()
        self.mock_index = MagicMock()
        self.mock_get_client.return_value = self.mock_pc
        self.mock_get_name.return_value = "test-index"
        self.mock_get_host.return_value = None # Start with name-based
        
        # When self.pc.Index(...) is called, return the mock index
        self.mock_pc.Index.return_value = self.mock_index
        
        self.vm = VectorStoreManager(index_name="test-index")

    def tearDown(self):
        self.patcher_client.stop()
        self.patcher_name.stop()
        self.patcher_host.stop()

    def test_upsert_memory(self):
        # Mock inference responses
        mock_dense = MagicMock()
        mock_dense.values = [0.1] * 1024
        mock_sparse = MagicMock()
        mock_sparse.sparse_indices = [1, 2, 3]
        mock_sparse.sparse_values = [0.5, 0.3, 0.2]
        
        self.mock_pc.inference.embed.side_effect = [
            [mock_dense], # First call for dense
            [mock_sparse] # Second call for sparse
        ]
        
        self.vm.upsert_memory(
            id="test-id",
            content="Hello world",
            metadata={"source": "test"},
            namespace="test-ns"
        )
        
        # Verify upsert was called with expected structure
        self.mock_index.upsert.assert_called_once()
        args, kwargs = self.mock_index.upsert.call_args
        vectors = kwargs['vectors']
        self.assertEqual(vectors[0]['id'], "test-id")
        self.assertEqual(vectors[0]['metadata']['content'], "Hello world")
        self.assertEqual(kwargs['namespace'], "test-ns")

    def test_query_memory(self):
        # Mock inference for query
        mock_dense_q = MagicMock()
        mock_dense_q.values = [0.1] * 1024
        mock_sparse_q = MagicMock()
        mock_sparse_q.sparse_indices = [1]
        mock_sparse_q.sparse_values = [1.0]
        
        self.mock_pc.inference.embed.side_effect = [
            [mock_dense_q],
            [mock_sparse_q]
        ]
        
        # Mock query results
        mock_results = MagicMock()
        mock_results.to_dict.return_value = {
            "matches": [{"id": "res1", "score": 0.9, "metadata": {"content": "hit"}}]
        }
        self.mock_index.query.return_value = mock_results
        
        results = self.vm.query_memory(query_text="search this", alpha=0.5)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "res1")
        
        # Verify alpha weighting was applied correctly in query call
        args, kwargs = self.mock_index.query.call_args
        # h_dense = dense * 0.5
        self.assertEqual(kwargs['vector'][0], 0.05)
        # h_sparse = sparse * (1 - 0.5)
        self.assertEqual(kwargs['sparse_vector']['values'][0], 0.5)

    def test_query_memory_rerank(self):
        # 1. Mock inference for query
        mock_dense_q = MagicMock()
        mock_dense_q.values = [0.1] * 1024
        mock_sparse_q = MagicMock()
        mock_sparse_q.sparse_indices = [1]
        mock_sparse_q.sparse_values = [1.0]
        
        # Inference calls: 2 for query vectors (dense/sparse)
        self.mock_pc.inference.embed.side_effect = [
            [mock_dense_q],
            [mock_sparse_q]
        ]
        
        # 2. Mock query results (Initial Retrieval)
        mock_results = MagicMock()
        mock_results.to_dict.return_value = {
            "matches": [
                {"id": "res1", "score": 0.9, "metadata": {"content": "hit 1"}},
                {"id": "res2", "score": 0.8, "metadata": {"content": "hit 2"}}
            ]
        }
        self.mock_index.query.return_value = mock_results
        
        # 3. Mock Rerank Response
        mock_rerank_hit = MagicMock()
        mock_rerank_hit.document = {"id": "res2", "metadata": {"content": "hit 2"}}
        mock_rerank_hit.score = 0.99
        
        mock_rerank_response = MagicMock()
        mock_rerank_response.data = [mock_rerank_hit]
        self.mock_pc.inference.rerank.return_value = mock_rerank_response
        
        results = self.vm.query_memory(
            query_text="search this", 
            rerank=True, 
            rerank_top_n=1
        )
        
        # Verify reranked result is returned (res2 was moved to top)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "res2")
        self.assertEqual(results[0]["score"], 0.99)
        
        # Verify rerank was called with correct parameters (including flattened 'content')
        expected_docs = [
            {"id": "res1", "content": "hit 1", "metadata": {"content": "hit 1"}},
            {"id": "res2", "content": "hit 2", "metadata": {"content": "hit 2"}}
        ]
        self.mock_pc.inference.rerank.assert_called_once_with(
            model="bge-reranker-v2-m3",
            query="search this",
            documents=expected_docs,
            top_n=1,
            rank_fields=["content"],
            return_documents=True
        )

if __name__ == '__main__':
    unittest.main()
