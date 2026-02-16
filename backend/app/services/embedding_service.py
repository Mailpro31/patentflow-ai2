from abc import ABC, abstractmethod
from typing import List, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingBackend(ABC):
    """Abstract base class for embedding backends."""
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        pass
    
    @abstractmethod
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass


class VertexAIEmbedding(EmbeddingBackend):
    """Vertex AI embedding backend using Google Cloud."""
    
    def __init__(self):
        self.project_id = settings.VERTEX_AI_PROJECT_ID
        self.location = settings.VERTEX_AI_LOCATION
        self.model_name = settings.VERTEX_AI_MODEL
        self._client = None
        
    async def _get_client(self):
        """Lazy load Vertex AI client."""
        if self._client is None:
            try:
                from google.cloud import aiplatform
                from google.oauth2 import service_account
                
                # Initialize Vertex AI
                if settings.GOOGLE_APPLICATION_CREDENTIALS:
                    credentials = service_account.Credentials.from_service_account_file(
                        settings.GOOGLE_APPLICATION_CREDENTIALS
                    )
                    aiplatform.init(
                        project=self.project_id,
                        location=self.location,
                        credentials=credentials
                    )
                else:
                    aiplatform.init(project=self.project_id, location=self.location)
                
                self._client = aiplatform
                logger.info("Vertex AI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI client: {e}")
                raise
        
        return self._client
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Vertex AI."""
        try:
            client = await self._get_client()
            from vertexai.language_models import TextEmbeddingModel
            
            model = TextEmbeddingModel.from_pretrained(self.model_name)
            embeddings = model.get_embeddings([text])
            
            if embeddings and len(embeddings) > 0:
                return embeddings[0].values
            else:
                raise ValueError("No embeddings returned from Vertex AI")
                
        except Exception as e:
            logger.error(f"Vertex AI embedding generation failed: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using Vertex AI."""
        try:
            client = await self._get_client()
            from vertexai.language_models import TextEmbeddingModel
            
            model = TextEmbeddingModel.from_pretrained(self.model_name)
            embeddings = model.get_embeddings(texts)
            
            return [emb.values for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Vertex AI batch embedding generation failed: {e}")
            raise


class SentenceTransformerEmbedding(EmbeddingBackend):
    """Local SentenceTransformer embedding backend."""
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self._model = None
        
    async def _get_model(self):
        """Lazy load SentenceTransformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                
                logger.info(f"Loading SentenceTransformer model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info("SentenceTransformer model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model: {e}")
                raise
        
        return self._model
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using SentenceTransformer."""
        try:
            model = await self._get_model()
            
            # Generate embedding
            embedding = model.encode(text, convert_to_numpy=True)
            
            # Convert to list and normalize
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"SentenceTransformer embedding generation failed: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using SentenceTransformer."""
        try:
            model = await self._get_model()
            
            # Generate embeddings
            embeddings = model.encode(texts, convert_to_numpy=True)
            
            # Convert to list of lists
            return [emb.tolist() for emb in embeddings]
            
        except Exception as e:
            logger.error(f"SentenceTransformer batch embedding generation failed: {e}")
            raise


class EmbeddingService:
    """
    Main embedding service that uses strategy pattern to switch between backends.
    Supports Vertex AI (Gemini) and SentenceTransformers.
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize embedding service with specified provider.
        
        Args:
            provider: "vertex_ai" or "sentence_transformers". 
                     If None, uses settings.EMBEDDING_PROVIDER
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self._backend: Optional[EmbeddingBackend] = None
        
    async def _get_backend(self) -> EmbeddingBackend:
        """Get or create embedding backend."""
        if self._backend is None:
            if self.provider == "vertex_ai":
                logger.info("Using Vertex AI embedding backend")
                self._backend = VertexAIEmbedding()
            elif self.provider == "sentence_transformers":
                logger.info("Using SentenceTransformer embedding backend")
                self._backend = SentenceTransformerEmbedding()
            else:
                raise ValueError(f"Unknown embedding provider: {self.provider}")
        
        return self._backend
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        backend = await self._get_backend()
        
        try:
            embedding = await backend.generate_embedding(text)
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed with {self.provider}: {e}")
            
            # Fallback to SentenceTransformer if Vertex AI fails
            if self.provider == "vertex_ai":
                logger.warning("Falling back to SentenceTransformer")
                self.provider = "sentence_transformers"
                self._backend = None  # Reset backend
                return await self.generate_embedding(text)
            
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        backend = await self._get_backend()
        
        try:
            embeddings = await backend.generate_embeddings_batch(texts)
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Batch embedding generation failed with {self.provider}: {e}")
            
            # Fallback to SentenceTransformer if Vertex AI fails
            if self.provider == "vertex_ai":
                logger.warning("Falling back to SentenceTransformer")
                self.provider = "sentence_transformers"
                self._backend = None  # Reset backend
                return await self.generate_embeddings_batch(texts)
            
            raise


# Global instance
embedding_service = EmbeddingService()
