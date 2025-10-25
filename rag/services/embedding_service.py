"""
Embedding service for generating vector representations of text.
Uses sentence-transformers (free, local embeddings)
"""
import logging
from typing import List

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using local models."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service with sentence-transformers.

        Args:
            model_name: Model to use for embeddings. Options:
                - "all-MiniLM-L6-v2" (default, fast, 384 dimensions)
                - "all-mpnet-base-v2" (better quality, 768 dimensions)
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        logger.info(f"Embedding service initialized with {model_name}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} documents")
            embeddings = self.model.encode(texts, convert_to_tensor=False, show_progress_bar=True)
            embeddings_list = [emb.tolist() for emb in embeddings]
            logger.info(f"Successfully generated {len(embeddings_list)} embeddings")
            return embeddings_list
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Dimension size
        """
        # all-MiniLM-L6-v2 has 384 dimensions
        # all-mpnet-base-v2 has 768 dimensions
        return self.model.get_sentence_embedding_dimension()
