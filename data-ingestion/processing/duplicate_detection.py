"""Duplicate detection and deduplication for market signals."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from plugins.base import RawData
from shared.vector_db import VectorDBService


logger = logging.getLogger(__name__)


@dataclass
class DuplicateMatch:
    """Represents a duplicate match between two data items."""
    original_id: str
    duplicate_id: str
    similarity_score: float
    match_type: str  # exact, near_exact, semantic
    confidence: float


class ContentHasher:
    """Generate content hashes for exact duplicate detection."""
    
    def __init__(self):
        pass
    
    def generate_content_hash(self, raw_data: RawData) -> str:
        """Generate a hash for the content."""
        # Normalize content for hashing
        content = self._normalize_for_hashing(raw_data.content)
        title = self._normalize_for_hashing(raw_data.title or "")
        
        # Combine title and content
        combined_content = f"{title}\n{content}"
        
        # Generate SHA-256 hash
        return hashlib.sha256(combined_content.encode('utf-8')).hexdigest()
    
    def generate_fuzzy_hash(self, raw_data: RawData) -> str:
        """Generate a fuzzy hash for near-duplicate detection."""
        # More aggressive normalization for fuzzy matching
        content = self._aggressive_normalize(raw_data.content)
        title = self._aggressive_normalize(raw_data.title or "")
        
        combined_content = f"{title}\n{content}"
        
        # Use first 32 characters of hash for fuzzy matching
        return hashlib.sha256(combined_content.encode('utf-8')).hexdigest()[:32]
    
    def generate_source_hash(self, raw_data: RawData) -> Optional[str]:
        """Generate hash based on source-specific identifiers."""
        if raw_data.source_id and raw_data.source:
            source_key = f"{raw_data.source}:{raw_data.source_id}"
            return hashlib.sha256(source_key.encode('utf-8')).hexdigest()
        return None
    
    def _normalize_for_hashing(self, text: str) -> str:
        """Normalize text for consistent hashing."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common punctuation
        text = text.replace('.', '').replace(',', '').replace('!', '').replace('?', '')
        
        return text.strip()
    
    def _aggressive_normalize(self, text: str) -> str:
        """More aggressive normalization for fuzzy matching."""
        if not text:
            return ""
        
        # Start with basic normalization
        text = self._normalize_for_hashing(text)
        
        # Remove common words that don't affect meaning
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
        
        words = text.split()
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        return ' '.join(filtered_words)


class SemanticMatcher:
    """Semantic similarity matching using TF-IDF and cosine similarity."""
    
    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        self._fitted = False
        self._document_vectors = None
        self._document_ids = []
    
    def fit_documents(self, documents: List[Tuple[str, str]]) -> None:
        """Fit the vectorizer on a collection of documents.
        
        Args:
            documents: List of (doc_id, content) tuples
        """
        if not documents:
            return
        
        self._document_ids = [doc_id for doc_id, _ in documents]
        contents = [content for _, content in documents]
        
        try:
            self._document_vectors = self.vectorizer.fit_transform(contents)
            self._fitted = True
            logger.info(f"Fitted semantic matcher on {len(documents)} documents")
        except Exception as e:
            logger.error(f"Failed to fit semantic matcher: {e}")
            self._fitted = False
    
    def find_similar_documents(self, content: str, doc_id: str) -> List[Tuple[str, float]]:
        """Find semantically similar documents."""
        if not self._fitted or not content:
            return []
        
        try:
            # Transform the query content
            query_vector = self.vectorizer.transform([content])
            
            # Calculate cosine similarity
            similarities = cosine_similarity(query_vector, self._document_vectors).flatten()
            
            # Find similar documents above threshold
            similar_docs = []
            for i, similarity in enumerate(similarities):
                if similarity >= self.similarity_threshold and self._document_ids[i] != doc_id:
                    similar_docs.append((self._document_ids[i], float(similarity)))
            
            # Sort by similarity (highest first)
            similar_docs.sort(key=lambda x: x[1], reverse=True)
            
            return similar_docs
            
        except Exception as e:
            logger.error(f"Error finding similar documents: {e}")
            return []
    
    def calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate semantic similarity between two pieces of content."""
        if not content1 or not content2:
            return 0.0
        
        try:
            # Transform both contents
            vectors = self.vectorizer.fit_transform([content1, content2])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0


class DuplicateDetector:
    """Main duplicate detection system."""
    
    def __init__(self, vector_db: Optional[VectorDBService] = None):
        self.hasher = ContentHasher()
        self.semantic_matcher = SemanticMatcher()
        self.vector_db = vector_db
        
        # In-memory caches for recent data
        self._content_hashes: Dict[str, str] = {}  # hash -> data_id
        self._fuzzy_hashes: Dict[str, str] = {}    # fuzzy_hash -> data_id
        self._source_hashes: Dict[str, str] = {}   # source_hash -> data_id
        
        # Configuration
        self.semantic_threshold = 0.8
        self.fuzzy_threshold = 0.9
        self.cache_ttl_hours = 24
        
    async def detect_duplicates(self, raw_data: RawData) -> List[DuplicateMatch]:
        """Detect duplicates for a single data item."""
        duplicates = []
        data_id = f"{raw_data.source}:{raw_data.source_id}"
        
        # 1. Exact content hash matching
        content_hash = self.hasher.generate_content_hash(raw_data)
        if content_hash in self._content_hashes:
            original_id = self._content_hashes[content_hash]
            if original_id != data_id:
                duplicates.append(DuplicateMatch(
                    original_id=original_id,
                    duplicate_id=data_id,
                    similarity_score=1.0,
                    match_type="exact",
                    confidence=1.0
                ))
        else:
            self._content_hashes[content_hash] = data_id
        
        # 2. Source-based duplicate detection
        source_hash = self.hasher.generate_source_hash(raw_data)
        if source_hash and source_hash in self._source_hashes:
            original_id = self._source_hashes[source_hash]
            if original_id != data_id:
                duplicates.append(DuplicateMatch(
                    original_id=original_id,
                    duplicate_id=data_id,
                    similarity_score=1.0,
                    match_type="exact",
                    confidence=1.0
                ))
        elif source_hash:
            self._source_hashes[source_hash] = data_id
        
        # 3. Fuzzy hash matching (near-duplicates)
        if not duplicates:  # Only check if no exact duplicates found
            fuzzy_hash = self.hasher.generate_fuzzy_hash(raw_data)
            if fuzzy_hash in self._fuzzy_hashes:
                original_id = self._fuzzy_hashes[fuzzy_hash]
                if original_id != data_id:
                    duplicates.append(DuplicateMatch(
                        original_id=original_id,
                        duplicate_id=data_id,
                        similarity_score=0.95,
                        match_type="near_exact",
                        confidence=0.9
                    ))
            else:
                self._fuzzy_hashes[fuzzy_hash] = data_id
        
        # 4. Semantic similarity matching
        if not duplicates and self.vector_db:  # Only if no other duplicates found
            semantic_duplicates = await self._find_semantic_duplicates(raw_data, data_id)
            duplicates.extend(semantic_duplicates)
        
        return duplicates
    
    async def batch_detect_duplicates(self, raw_data_list: List[RawData]) -> Dict[str, List[DuplicateMatch]]:
        """Detect duplicates in a batch of data items."""
        results = {}
        
        # Prepare documents for semantic matching
        documents = []
        for raw_data in raw_data_list:
            data_id = f"{raw_data.source}:{raw_data.source_id}"
            content = f"{raw_data.title or ''}\n{raw_data.content}"
            documents.append((data_id, content))
        
        # Fit semantic matcher
        if documents:
            self.semantic_matcher.fit_documents(documents)
        
        # Process each item
        for raw_data in raw_data_list:
            data_id = f"{raw_data.source}:{raw_data.source_id}"
            duplicates = await self.detect_duplicates(raw_data)
            if duplicates:
                results[data_id] = duplicates
        
        logger.info(f"Found duplicates for {len(results)}/{len(raw_data_list)} items")
        return results
    
    async def _find_semantic_duplicates(self, raw_data: RawData, data_id: str) -> List[DuplicateMatch]:
        """Find semantic duplicates using vector database."""
        if not self.vector_db:
            return []
        
        try:
            # Create content for similarity search
            content = f"{raw_data.title or ''}\n{raw_data.content}"
            
            # Search for similar content in vector database
            similar_items = await self.vector_db.similarity_search(
                content,
                namespace="market_signals",
                top_k=10,
                threshold=self.semantic_threshold
            )
            
            duplicates = []
            for item in similar_items:
                if item.get('id') != data_id and item.get('score', 0) >= self.semantic_threshold:
                    duplicates.append(DuplicateMatch(
                        original_id=item['id'],
                        duplicate_id=data_id,
                        similarity_score=item['score'],
                        match_type="semantic",
                        confidence=item['score']
                    ))
            
            return duplicates
            
        except Exception as e:
            logger.error(f"Error finding semantic duplicates: {e}")
            return []
    
    def mark_as_duplicate(self, duplicate_match: DuplicateMatch) -> None:
        """Mark an item as a duplicate of another."""
        # This would typically update a database or cache
        logger.info(f"Marked {duplicate_match.duplicate_id} as duplicate of {duplicate_match.original_id}")
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """Get statistics about duplicate detection."""
        return {
            "content_hashes": len(self._content_hashes),
            "fuzzy_hashes": len(self._fuzzy_hashes),
            "source_hashes": len(self._source_hashes),
            "semantic_threshold": self.semantic_threshold,
            "fuzzy_threshold": self.fuzzy_threshold
        }
    
    def cleanup_old_hashes(self, hours: int = 24) -> None:
        """Clean up old hash entries (this is a simplified version)."""
        # In a real implementation, you'd track timestamps and remove old entries
        # For now, we'll just clear everything if it gets too large
        max_size = 10000
        
        if len(self._content_hashes) > max_size:
            self._content_hashes.clear()
            logger.info("Cleared content hashes cache")
        
        if len(self._fuzzy_hashes) > max_size:
            self._fuzzy_hashes.clear()
            logger.info("Cleared fuzzy hashes cache")
        
        if len(self._source_hashes) > max_size:
            self._source_hashes.clear()
            logger.info("Cleared source hashes cache")


class DeduplicationService:
    """Service for managing deduplication across the system."""
    
    def __init__(self, vector_db: Optional[VectorDBService] = None):
        self.detector = DuplicateDetector(vector_db)
        self.duplicate_store: Dict[str, List[DuplicateMatch]] = {}
    
    async def process_raw_data(self, raw_data: RawData) -> Tuple[bool, List[DuplicateMatch]]:
        """Process raw data and return whether it's a duplicate."""
        duplicates = await self.detector.detect_duplicates(raw_data)
        
        data_id = f"{raw_data.source}:{raw_data.source_id}"
        
        if duplicates:
            self.duplicate_store[data_id] = duplicates
            return True, duplicates
        
        return False, []
    
    async def process_batch(self, raw_data_list: List[RawData]) -> Tuple[List[RawData], Dict[str, List[DuplicateMatch]]]:
        """Process a batch and return deduplicated data."""
        duplicate_results = await self.detector.batch_detect_duplicates(raw_data_list)
        
        # Filter out duplicates
        unique_data = []
        for raw_data in raw_data_list:
            data_id = f"{raw_data.source}:{raw_data.source_id}"
            if data_id not in duplicate_results:
                unique_data.append(raw_data)
        
        # Store duplicate information
        self.duplicate_store.update(duplicate_results)
        
        logger.info(f"Deduplicated {len(raw_data_list)} -> {len(unique_data)} items")
        return unique_data, duplicate_results
    
    def get_duplicate_info(self, data_id: str) -> Optional[List[DuplicateMatch]]:
        """Get duplicate information for a data item."""
        return self.duplicate_store.get(data_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        stats = self.detector.get_deduplication_stats()
        stats.update({
            "total_duplicates_found": len(self.duplicate_store),
            "duplicate_items": sum(len(matches) for matches in self.duplicate_store.values())
        })
        return stats


# Task queue integration functions
async def detect_duplicates_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Task handler for duplicate detection."""
    try:
        # Extract raw data from payload
        raw_data_dict = payload.get('raw_data')
        if not raw_data_dict:
            raise ValueError("No raw data provided")
        
        raw_data = RawData(**raw_data_dict)
        
        # Initialize deduplication service
        dedup_service = DeduplicationService()
        
        # Process data
        is_duplicate, duplicates = await dedup_service.process_raw_data(raw_data)
        
        return {
            'success': True,
            'is_duplicate': is_duplicate,
            'duplicate_count': len(duplicates),
            'duplicates': [
                {
                    'original_id': dup.original_id,
                    'similarity_score': dup.similarity_score,
                    'match_type': dup.match_type,
                    'confidence': dup.confidence
                }
                for dup in duplicates
            ],
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Duplicate detection task failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'processed_at': datetime.now().isoformat()
        }


async def batch_deduplicate_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Task handler for batch deduplication."""
    try:
        # Extract raw data list from payload
        raw_data_list = payload.get('raw_data_list', [])
        if not raw_data_list:
            raise ValueError("No raw data list provided")
        
        # Convert to RawData objects
        raw_data_objects = [RawData(**item) for item in raw_data_list]
        
        # Initialize deduplication service
        dedup_service = DeduplicationService()
        
        # Process batch
        unique_data, duplicate_results = await dedup_service.process_batch(raw_data_objects)
        
        return {
            'success': True,
            'input_count': len(raw_data_objects),
            'unique_count': len(unique_data),
            'duplicate_count': len(duplicate_results),
            'unique_data': [item.dict() for item in unique_data],
            'duplicate_info': {
                data_id: [
                    {
                        'original_id': dup.original_id,
                        'similarity_score': dup.similarity_score,
                        'match_type': dup.match_type,
                        'confidence': dup.confidence
                    }
                    for dup in duplicates
                ]
                for data_id, duplicates in duplicate_results.items()
            },
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch deduplication task failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'processed_at': datetime.now().isoformat()
        }