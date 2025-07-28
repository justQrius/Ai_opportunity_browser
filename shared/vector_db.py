"""Vector database utilities using Pinecone for semantic search.

Supports the design document's vector database requirements:
- Opportunity embeddings for semantic search
- Market signal embeddings for similarity detection
- User preference embeddings for personalization
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pinecone
import structlog

logger = structlog.get_logger(__name__)


class VectorDatabaseManager:
    """Pinecone vector database manager for semantic operations.
    
    Implements the design document's vector database architecture for:
    - Semantic similarity detection
    - Opportunity matching and ranking
    - User preference-based personalization
    """
    
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.environment = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
        self.pc: Optional[Pinecone] = None
        
        # Index configurations based on design document requirements
        self.indexes = {
            "opportunities": {
                "dimension": 1536,  # OpenAI embedding dimension
                "metric": "cosine",
                "description": "Opportunity embeddings for semantic search"
            },
            "market-signals": {
                "dimension": 1536,
                "metric": "cosine", 
                "description": "Market signal embeddings for similarity detection"
            },
            "user-preferences": {
                "dimension": 1536,
                "metric": "cosine",
                "description": "User preference embeddings for personalization"
            }
        }
    
    async def initialize(self):
        """Initialize Pinecone connection and create indexes if needed."""
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")
        
        try:
            # Initialize Pinecone client
            self.pc = pinecone.Pinecone(api_key=self.api_key)
            
            # Create indexes if they don't exist
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            for index_name, config in self.indexes.items():
                if index_name not in existing_indexes:
                    logger.info("Creating Pinecone index", index_name=index_name)
                    
                    self.pc.create_index(
                        name=index_name,
                        dimension=config["dimension"],
                        metric=config["metric"],
                    )
                    
                    logger.info("Pinecone index created", index_name=index_name)
                else:
                    logger.info("Pinecone index already exists", index_name=index_name)
            
            logger.info("Pinecone vector database initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Pinecone", error=str(e), exc_info=True)
            raise
    
    def get_index(self, index_name: str):
        """Get Pinecone index instance."""
        if not self.pc:
            raise RuntimeError("Pinecone not initialized. Call initialize() first.")
        
        if index_name not in self.indexes:
            raise ValueError(f"Unknown index: {index_name}")
        
        return self.pc.Index(index_name)
    
    async def upsert_vectors(
        self, 
        index_name: str, 
        vectors: List[Dict[str, Any]]
    ) -> bool:
        """Upsert vectors to specified index.
        
        Args:
            index_name: Name of the index
            vectors: List of vector dictionaries with id, values, and metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            index = self.get_index(index_name)
            
            # Batch upsert for better performance
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                index.upsert(vectors=batch)
            
            logger.info(
                "Vectors upserted successfully", 
                index_name=index_name, 
                count=len(vectors)
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to upsert vectors", 
                index_name=index_name, 
                error=str(e), 
                exc_info=True
            )
            return False
    
    async def query_vectors(
        self,
        index_name: str,
        query_vector: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_values: bool = False
    ) -> List[Dict[str, Any]]:
        """Query vectors for similarity search.
        
        Args:
            index_name: Name of the index
            query_vector: Query vector for similarity search
            top_k: Number of top results to return
            filter_dict: Metadata filter dictionary
            include_metadata: Whether to include metadata in results
            include_values: Whether to include vector values in results
            
        Returns:
            List of similar vectors with scores and metadata
        """
        try:
            index = self.get_index(index_name)
            
            response = index.query(
                vector=query_vector,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=include_metadata,
                include_values=include_values
            )
            
            results = []
            for match in response.matches:
                result = {
                    "id": match.id,
                    "score": match.score
                }
                
                if include_metadata and match.metadata:
                    result["metadata"] = match.metadata
                
                if include_values and match.values:
                    result["values"] = match.values
                
                results.append(result)
            
            logger.debug(
                "Vector query completed", 
                index_name=index_name, 
                results_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Vector query failed", 
                index_name=index_name, 
                error=str(e), 
                exc_info=True
            )
            return []
    
    async def delete_vectors(
        self, 
        index_name: str, 
        ids: List[str]
    ) -> bool:
        """Delete vectors by IDs.
        
        Args:
            index_name: Name of the index
            ids: List of vector IDs to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            index = self.get_index(index_name)
            index.delete(ids=ids)
            
            logger.info(
                "Vectors deleted successfully", 
                index_name=index_name, 
                count=len(ids)
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete vectors", 
                index_name=index_name, 
                error=str(e), 
                exc_info=True
            )
            return False
    
    async def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        """Get index statistics.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Index statistics dictionary
        """
        try:
            index = self.get_index(index_name)
            stats = index.describe_index_stats()
            
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {}
            }
            
        except Exception as e:
            logger.error(
                "Failed to get index stats", 
                index_name=index_name, 
                error=str(e)
            )
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check vector database connectivity and status."""
        if not self.pc:
            try:
                await self.initialize()
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "message": "Failed to initialize Pinecone connection",
                    "error": str(e)
                }
        
        try:
            # Test by listing indexes
            indexes = [index.name for index in self.pc.list_indexes()]
            
            # Check if our required indexes exist
            missing_indexes = []
            for index_name in self.indexes.keys():
                if index_name not in indexes:
                    missing_indexes.append(index_name)
            
            if missing_indexes:
                return {
                    "status": "degraded",
                    "message": f"Missing indexes: {', '.join(missing_indexes)}",
                    "existing_indexes": indexes,
                    "missing_indexes": missing_indexes
                }
            
            # Get stats for all indexes
            index_stats = {}
            for index_name in self.indexes.keys():
                stats = await self.get_index_stats(index_name)
                index_stats[index_name] = stats
            
            return {
                "status": "healthy",
                "message": "Vector database is working correctly",
                "indexes": indexes,
                "index_stats": index_stats
            }
            
        except Exception as e:
            logger.error("Vector database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": "Vector database health check failed",
                "error": str(e)
            }


class OpportunityVectorService:
    """Service for managing opportunity embeddings and semantic search."""
    
    def __init__(self, vector_db: VectorDatabaseManager):
        self.vector_db = vector_db
        self.index_name = "opportunities"
    
    async def store_opportunity_embedding(
        self,
        opportunity_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store opportunity embedding with metadata.
        
        Args:
            opportunity_id: Unique opportunity identifier
            embedding: Vector embedding of opportunity
            metadata: Opportunity metadata for filtering
            
        Returns:
            True if successful, False otherwise
        """
        vector_data = [{
            "id": opportunity_id,
            "values": embedding,
            "metadata": {
                **metadata,
                "type": "opportunity",
                "created_at": datetime.utcnow().isoformat()
            }
        }]
        
        return await self.vector_db.upsert_vectors(self.index_name, vector_data)
    
    async def find_similar_opportunities(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Find opportunities similar to query embedding.
        
        Args:
            query_embedding: Query vector for similarity search
            top_k: Number of similar opportunities to return
            filters: Metadata filters (e.g., industry, AI type)
            
        Returns:
            List of similar opportunities with similarity scores
        """
        return await self.vector_db.query_vectors(
            index_name=self.index_name,
            query_vector=query_embedding,
            top_k=top_k,
            filter_dict=filters,
            include_metadata=True
        )


class MarketSignalVectorService:
    """Service for managing market signal embeddings and similarity detection."""
    
    def __init__(self, vector_db: VectorDatabaseManager):
        self.vector_db = vector_db
        self.index_name = "market-signals"
    
    async def store_signal_embedding(
        self,
        signal_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store market signal embedding with metadata."""
        vector_data = [{
            "id": signal_id,
            "values": embedding,
            "metadata": {
                **metadata,
                "type": "market_signal",
                "created_at": datetime.utcnow().isoformat()
            }
        }]
        
        return await self.vector_db.upsert_vectors(self.index_name, vector_data)
    
    async def find_similar_signals(
        self,
        query_embedding: List[float],
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Find market signals similar to query embedding."""
        return await self.vector_db.query_vectors(
            index_name=self.index_name,
            query_vector=query_embedding,
            top_k=top_k,
            filter_dict=filters,
            include_metadata=True
        )


class UserPreferenceVectorService:
    """Service for managing user preference embeddings and personalization."""
    
    def __init__(self, vector_db: VectorDatabaseManager):
        self.vector_db = vector_db
        self.index_name = "user-preferences"
    
    async def store_user_preferences(
        self,
        user_id: str,
        preference_embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store user preference embedding."""
        vector_data = [{
            "id": user_id,
            "values": preference_embedding,
            "metadata": {
                **metadata,
                "type": "user_preferences",
                "updated_at": datetime.utcnow().isoformat()
            }
        }]
        
        return await self.vector_db.upsert_vectors(self.index_name, vector_data)
    
    async def find_similar_users(
        self,
        user_embedding: List[float],
        top_k: int = 10,
        exclude_user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find users with similar preferences."""
        filters = {}
        if exclude_user_id:
            filters = {"id": {"$ne": exclude_user_id}}
        
        return await self.vector_db.query_vectors(
            index_name=self.index_name,
            query_vector=user_embedding,
            top_k=top_k,
            filter_dict=filters,
            include_metadata=True
        )


# Alias for backward compatibility
VectorDBService = VectorDatabaseManager

# Global vector database manager instance
vector_db_manager = VectorDatabaseManager()

# Service instances
opportunity_vector_service = OpportunityVectorService(vector_db_manager)
market_signal_vector_service = MarketSignalVectorService(vector_db_manager)
user_preference_vector_service = UserPreferenceVectorService(vector_db_manager)