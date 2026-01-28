import os
import uuid
import hashlib
import logging
from typing import List
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter, 
    Language
)
from .vector_store import VectorStoreManager, MemoryItem
from .config import get_pinecone_index_name

# Configure logging to stay professional
logger = logging.getLogger(__name__)

class CodeIndexer:
    """
    Scans the codebase, chunks files, and ingests them into Pinecone.
    Implements the SkullRender 'Bones + Brain' philosophy by clean indexing.
    """
    
    def __init__(self, index_name: str = None):
        self.vm = VectorStoreManager(index_name=index_name)
        self.namespace = "codebase"
        
        # Splitters for different languages
        self.splitters = {
            ".py": RecursiveCharacterTextSplitter.from_language(
                language=Language.PYTHON, chunk_size=1000, chunk_overlap=100
            ),
            ".ts": RecursiveCharacterTextSplitter.from_language(
                language=Language.TS, chunk_size=1000, chunk_overlap=100
            ),
            ".md": RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=100
            )
        }
        self.default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=100
        )

    def _get_file_id(self, file_path: str, chunk_idx: int) -> str:
        """Generates a stable UUID based on file path and chunk index."""
        hash_input = f"{file_path}_{chunk_idx}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, hash_input))

    def scan_and_index(self, root_dir: str, extensions: List[str] = [".py", ".ts", ".md"]):
        """
        Walks through the directory and indexes files matching extensions.
        """
        logger.info(f"Starting Codebase Indexing at: {root_dir}")
        items_to_upsert = []
        
        for root, dirs, files in os.walk(root_dir):
            # Ignore hidden dirs and pycache
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in extensions:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, root_dir)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        splitter = self.splitters.get(ext, self.default_splitter)
                        chunks = splitter.split_text(content)
                        
                        logger.debug(f"Indexing {rel_path} ({len(chunks)} chunks)")
                        
                        for i, chunk in enumerate(chunks):
                            item_id = self._get_file_id(rel_path, i)
                            items_to_upsert.append({
                                "id": item_id,
                                "content": chunk,
                                "metadata": {
                                    "file_path": rel_path,
                                    "extension": ext,
                                    "chunk_idx": i,
                                    "total_chunks": len(chunks)
                                }
                            })
                            
                    except Exception as e:
                        logger.error(f"Error indexing {rel_path}: {e}")

        if items_to_upsert:
            logger.info(f"Batching {len(items_to_upsert)} items into Pinecone (Namespace: {self.namespace})...")
            self.vm.batch_upsert_memory(items_to_upsert, namespace=self.namespace)
            logger.info("Codebase Ingestion Complete.")
        else:
            logger.warning("No files found to index.")

if __name__ == "__main__":
    # Configure root logger for CLI usage
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Target the src and .agent folders relative to the playground root
    # Adjust path if running from different locations
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    indexer = CodeIndexer()
    indexer.scan_and_index(base_dir)
