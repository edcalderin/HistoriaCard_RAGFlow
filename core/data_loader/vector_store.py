import asyncio
import logging
from pathlib import Path

from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore, RetrievalMode

from core.config import LLMConfig
from core.model.embedding import Embedding
from utils.logging import setup_logging

setup_logging()

path_dir: Path = Path(__file__).parent / "documents"


class VectorStore:
    def __init__(self, llm_config: LLMConfig) -> None:
        self._llm_config = llm_config

    def _get_documents(self) -> list[Document]:
        """Get Documents.

        Extract document from pdf file.

        Returns:
        List of Documents
        """
        filename: Path = path_dir / self._llm_config.filename
        loader = PyPDFLoader(filename)
        docs = [doc for doc in loader.lazy_load()]
        return docs

    @staticmethod
    def _create_chunks(docs: list[Document]) -> list[Document]:
        """
        The function `_create_chunks` takes a list of `Document` objects, splits the
        text content of each document using a `CharacterTextSplitter`, and returns a
        list of split `Document` objects.

        Args:
          docs: The `docs` parameter is a list of `Document` objects that are being
        passed to the `_create_chunks` method.

        Returns:
          The function `_create_chunks` is returning a list of documents that have
          been split using the `CharacterTextSplitter` class.
        """
        text_splitter = CharacterTextSplitter()
        return text_splitter.split_documents(docs)

    async def _async_store_documents(
        self, documents: list[Document], embeddings: HuggingFaceEmbeddings
    ) -> None:
        """
        This async function stores documents with embeddings in a Qdrant vector store.

        Args:
          documents: The `documents` parameter is a list of `Document` objects that
        contain the data to be stored in the vector store.
          embeddings: The `embeddings` parameter in the `_async_store_documents`
        function is of type `HuggingFaceEmbeddings`. It is used to provide the
        embeddings for the documents that are being stored in the vector store.
        """
        try:
            await QdrantVectorStore.afrom_documents(
                documents=documents,
                path=self._llm_config.qdrant_store_path,
                collection_name=self._llm_config.collection_name,
                embedding=embeddings,
                retrieval_mode=RetrievalMode.DENSE,
            )
        except Exception as ex:
            raise Exception(f"Error by initializing vector embeddings: {ex}") from ex

    async def load_to_qdrant_index(self) -> None:
        try:
            logging.info("Starting...")
            documents: list[Document] = self._get_documents()
            chunked_documents: list[Document] = self._create_chunks(documents)
            embeddings: HuggingFaceEmbeddings = Embedding.load_embeddings(
                self._llm_config.model_name
            )
            await self._async_store_documents(chunked_documents, embeddings)
        except Exception as ex:
            logging.error("An error was produced by loading to vector store")
            raise ex
        else:
            logging.info("Embeddings stored successfully!")


if __name__ == "__main__":
    vector_store = VectorStore(llm_config=LLMConfig())
    asyncio.run(vector_store.load_to_qdrant_index())
