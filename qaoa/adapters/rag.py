"""Vector store and embedding support for RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chromadb.api import ClientAPI
    from chromadb.api.models.Collection import Collection


@dataclass(slots=True, kw_only=True)
class VectorStore:
    """ChromaDB-backed vector store for semantic retrieval."""

    collection_name: str
    persist_directory: str | None = None
    _client: ClientAPI | None = None
    _collection: Collection = field(init=False)

    def __post_init__(self) -> None:
        import chromadb

        if self.persist_directory:
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        else:
            self._client = chromadb.Client()
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name
        )

    def add_documents(self, documents: list[str], ids: list[str] | None = None) -> None:
        """Add documents to vector store with auto-generated embeddings."""
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
        self._collection.add(documents=documents, ids=ids)

    def query(self, query_text: str, n_results: int = 5) -> list[str]:
        """Retrieve top-k semantically similar documents."""
        results = self._collection.query(query_texts=[query_text], n_results=n_results)
        return results["documents"][0] if results["documents"] else []

    def delete_all(self) -> None:
        """Clear all documents from collection."""
        if self._client and self._collection:
            self._client.delete_collection(name=self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name
            )
