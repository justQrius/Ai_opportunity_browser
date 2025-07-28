"""AI service for generating embeddings and other AI operations.

Supports multi-provider AI integration for semantic search and analysis.
"""

import os
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import openai
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this provider."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using text-embedding-ada-002."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        self.model = "text-embedding-ada-002"
        self.dimension = 1536
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI's text-embedding-ada-002 model."""
        try:
            # OpenAI has a limit on batch size, so we'll process in chunks
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            logger.info(
                "Generated OpenAI embeddings",
                text_count=len(texts),
                embedding_count=len(all_embeddings),
                model=self.model
            )
            
            return all_embeddings
            
        except Exception as e:
            logger.error("Failed to generate OpenAI embeddings", error=str(e), exc_info=True)
            raise


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing and development."""
    
    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings (random vectors)."""
        import random
        
        embeddings = []
        for text in texts:
            # Generate deterministic "embeddings" based on text hash
            random.seed(hash(text) % (2**32))
            embedding = [random.uniform(-1, 1) for _ in range(self.dimension)]
            embeddings.append(embedding)
        
        logger.debug(
            "Generated mock embeddings",
            text_count=len(texts),
            dimension=self.dimension
        )
        
        return embeddings
    
    def get_dimension(self) -> int:
        return self.dimension


class AIService:
    """Main AI service for embedding generation and other AI operations."""
    
    def __init__(self):
        self.embedding_provider: Optional[EmbeddingProvider] = None
        self._initialize_embedding_provider()
    
    def _initialize_embedding_provider(self):
        """Initialize the embedding provider based on available API keys."""
        try:
            # Try OpenAI first
            if os.getenv("OPENAI_API_KEY"):
                self.embedding_provider = OpenAIEmbeddingProvider()
                logger.info("Initialized OpenAI embedding provider")
                return
        except Exception as e:
            logger.warning("Failed to initialize OpenAI embedding provider", error=str(e))
        
        # Fall back to mock provider
        self.embedding_provider = MockEmbeddingProvider()
        logger.info("Initialized mock embedding provider (no API keys available)")
    
    async def generate_text_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not self.embedding_provider:
            raise RuntimeError("No embedding provider available")
        
        embeddings = await self.embedding_provider.generate_embeddings([text])
        return embeddings[0]
    
    async def generate_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not self.embedding_provider:
            raise RuntimeError("No embedding provider available")
        
        return await self.embedding_provider.generate_embeddings(texts)
    
    async def generate_opportunity_embedding(self, opportunity_data: Dict[str, Any]) -> List[float]:
        """Generate embedding for an opportunity based on its content."""
        # Combine relevant text fields for embedding
        text_parts = []
        
        if opportunity_data.get("title"):
            text_parts.append(f"Title: {opportunity_data['title']}")
        
        if opportunity_data.get("description"):
            text_parts.append(f"Description: {opportunity_data['description']}")
        
        if opportunity_data.get("summary"):
            text_parts.append(f"Summary: {opportunity_data['summary']}")
        
        if opportunity_data.get("ai_solution_types"):
            ai_types = opportunity_data["ai_solution_types"]
            if isinstance(ai_types, list):
                text_parts.append(f"AI Solution Types: {', '.join(ai_types)}")
            elif isinstance(ai_types, str):
                text_parts.append(f"AI Solution Types: {ai_types}")
        
        if opportunity_data.get("target_industries"):
            industries = opportunity_data["target_industries"]
            if isinstance(industries, list):
                text_parts.append(f"Target Industries: {', '.join(industries)}")
            elif isinstance(industries, str):
                text_parts.append(f"Target Industries: {industries}")
        
        if opportunity_data.get("tags"):
            tags = opportunity_data["tags"]
            if isinstance(tags, list):
                text_parts.append(f"Tags: {', '.join(tags)}")
            elif isinstance(tags, str):
                text_parts.append(f"Tags: {tags}")
        
        # Combine all text parts
        combined_text = "\n".join(text_parts)
        
        if not combined_text.strip():
            raise ValueError("No text content available for embedding generation")
        
        return await self.generate_text_embedding(combined_text)
    
    async def generate_search_query_embedding(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[float]:
        """Generate embedding for a search query, optionally incorporating filters."""
        text_parts = [f"Search Query: {query}"]
        
        if filters:
            if filters.get("ai_solution_types"):
                text_parts.append(f"AI Types: {', '.join(filters['ai_solution_types'])}")
            
            if filters.get("target_industries"):
                text_parts.append(f"Industries: {', '.join(filters['target_industries'])}")
            
            if filters.get("tags"):
                text_parts.append(f"Tags: {', '.join(filters['tags'])}")
        
        combined_text = "\n".join(text_parts)
        return await self.generate_text_embedding(combined_text)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by the current provider."""
        if not self.embedding_provider:
            return 1536  # Default OpenAI dimension
        
        return self.embedding_provider.get_dimension()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check AI service health."""
        try:
            # Test embedding generation with a simple text
            test_embedding = await self.generate_text_embedding("test")
            
            return {
                "status": "healthy",
                "provider": type(self.embedding_provider).__name__,
                "embedding_dimension": len(test_embedding),
                "message": "AI service is working correctly"
            }
            
        except Exception as e:
            logger.error("AI service health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "provider": type(self.embedding_provider).__name__ if self.embedding_provider else "none",
                "error": str(e),
                "message": "AI service health check failed"
            }


# Global AI service instance
ai_service = AIService()