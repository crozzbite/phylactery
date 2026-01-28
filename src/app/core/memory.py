import logging
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document

load_dotenv()
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from .models import Skill

logger = logging.getLogger(__name__)


class VectorMemory:
    """Manages the long-term vector memory using Pinecone."""

    def __init__(self) -> None:
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX", "phylactery-skills")
        self.embeddings = self._get_embeddings()
        self.vector_store: PineconeVectorStore | None = None

        if self.api_key:
            self._init_pinecone()
        else:
            logger.warning("⚠️ PINECONE_API_KEY not found. Memory will be lobotomized.")

    def _get_embeddings(self) -> object:
        """Factory for embedding model based on env."""
        provider = os.getenv("AI_PROVIDER", "ollama").lower()
        if provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            return OpenAIEmbeddings(api_key=key)  # type: ignore
        else:
            # Fallback to Ollama for local embeddings (e.g., nomic-embed-text)
            return OllamaEmbeddings(model="nomic-embed-text")

    def _init_pinecone(self) -> None:
        """Initializes connection to Pinecone."""
        try:
            pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists, if not assume it's created or log warning
            # Logic to create index is better handled in a setup script or carefully here
            existing_indexes = [i.name for i in pc.list_indexes()]
            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                pc.create_index(
                    name=self.index_name,
                    dimension=1536 if isinstance(self.embeddings, OpenAIEmbeddings) else 768,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )

            self.vector_store = PineconeVectorStore(
                index_name=self.index_name,
                embedding=self.embeddings,
                pinecone_api_key=self.api_key
            )
            logger.info("✅ Connected to Pinecone Memory.")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Pinecone: {e}")

    async def index_skills(self, skills: list[Skill]) -> None:
        """Re-indexes all provided skills."""
        if not self.vector_store:
            return

        documents = []
        for skill in skills:
            # Metadata for filtering and context
            meta = {
                "name": skill.name,
                "version": skill.version,
                "tags": ",".join(skill.tags),
                "path": skill.path
            }
            # Content is what we embed
            doc = Document(page_content=skill.content, metadata=meta)
            documents.append(doc)

        if documents:
            logger.info(f"🧠 Encoding {len(documents)} skills into vector space...")
            # Ideally delete old namespace or overwrite. For simplicity we add_documents
            # PineconeVectorStore doesn't support 'overwrite' directly without logic
            await self.vector_store.aadd_documents(documents)
            logger.info("✨ Knowledge Indexing Complete.")

    async def retrieve_relevant(self, query: str, k: int = 2) -> list[Document]:
        """Retrieves top-k relevant skills for a query."""
        if not self.vector_store:
            return []

        try:
            # Cast because langchain types can be loose
            from typing import cast
            results = await self.vector_store.asimilarity_search(query, k=k)
            return cast(list[Document], results)
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []

# Singleton
memory = VectorMemory()
