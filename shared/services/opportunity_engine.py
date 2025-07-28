"""
OpportunityEngine core implementation for the AI Opportunity Browser system.
Implements signal-to-opportunity conversion and opportunity deduplication logic.

This module implements:
- Signal-to-opportunity conversion algorithms
- Opportunity deduplication using semantic similarity
- Integration with existing agent analysis results
- Opportunity scoring and validation workflows

Supports Requirements 5.1.1 (Create OpportunityEngine core) from the implementation plan.
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import statistics

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.market_signal import MarketSignal, SignalType
from shared.models.validation import ValidationResult
from shared.schemas.opportunity import OpportunityCreate
# Removed circular import - will use direct database operations
from shared.vector_db import (
    vector_db_manager, 
    opportunity_vector_service, 
    market_signal_vector_service
)
from shared.cache import cache_manager, CacheKeys
from shared.services.scoring_algorithms import (
    advanced_scoring_engine,
    MarketValidationScorer,
    CompetitiveAnalysisEngine,
    AdvancedScoringEngine
)

logger = logging.getLogger(__name__)


@dataclass
class SignalCluster:
    """Represents a cluster of related market signals"""
    cluster_id: str
    signals: List[Dict[str, Any]]
    dominant_themes: List[str]
    pain_intensity: float
    market_potential: float
    ai_opportunity_score: float
    signal_count: int
    total_engagement: int
    avg_sentiment: float
    confidence_level: float


@dataclass
class OpportunityCandidate:
    """Represents a candidate opportunity generated from signals"""
    candidate_id: str
    title: str
    description: str
    problem_statement: str
    proposed_solution: str
    ai_solution_types: List[str]
    target_industries: List[str]
    market_signals: List[str]  # Signal IDs
    confidence_score: float
    market_validation_score: float
    ai_feasibility_score: float
    source_cluster: SignalCluster


@dataclass
class DuplicationResult:
    """Result of opportunity deduplication analysis"""
    is_duplicate: bool
    similarity_score: float
    existing_opportunity_id: Optional[str] = None
    similarity_type: str = "none"  # exact, semantic, partial
    confidence: float = 0.0


class OpportunityEngine:
    """
    Core engine for converting market signals into validated opportunities.
    Implements signal-to-opportunity conversion and deduplication logic.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Configuration parameters
        self.min_signals_for_opportunity = self.config.get("min_signals_for_opportunity", 3)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.85)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.7)
        self.max_opportunities_per_batch = self.config.get("max_opportunities_per_batch", 10)
        
        # Deduplication settings
        self.exact_match_threshold = self.config.get("exact_match_threshold", 0.95)
        self.semantic_similarity_threshold = self.config.get("semantic_similarity_threshold", 0.80)
        self.partial_similarity_threshold = self.config.get("partial_similarity_threshold", 0.65)
        
        # AI solution type keywords for classification
        self.ai_solution_keywords = {
            "machine_learning": ["ml", "machine learning", "predictive", "classification", "regression"],
            "natural_language_processing": ["nlp", "text analysis", "sentiment", "language", "chatbot"],
            "computer_vision": ["cv", "image", "vision", "recognition", "detection", "visual"],
            "speech_recognition": ["speech", "voice", "audio", "transcription", "recognition"],
            "recommendation_systems": ["recommendation", "personalization", "collaborative filtering"],
            "predictive_analytics": ["prediction", "forecasting", "analytics", "trends"],
            "automation": ["automation", "workflow", "process", "robotic"],
            "optimization": ["optimization", "efficiency", "resource", "scheduling"]
        }
        
        # Initialize advanced scoring engine
        self.scoring_engine = AdvancedScoringEngine(self.config.get("scoring", {}))
        
        logger.info("OpportunityEngine initialized", config=self.config)
    
    async def process_signals_to_opportunities(
        self, 
        db: AsyncSession,
        signals: List[Dict[str, Any]],
        batch_id: Optional[str] = None
    ) -> List[Opportunity]:
        """
        Main method to convert market signals into opportunities.
        
        Args:
            db: Database session
            signals: List of market signal data from agents
            batch_id: Optional batch identifier for tracking
            
        Returns:
            List of created opportunities
        """
        batch_id = batch_id or f"batch_{datetime.utcnow().timestamp()}"
        
        logger.info(
            "Starting signal-to-opportunity conversion",
            batch_id=batch_id,
            signal_count=len(signals)
        )
        
        try:
            # Step 1: Cluster related signals
            signal_clusters = await self._cluster_related_signals(signals)
            logger.info(f"Created {len(signal_clusters)} signal clusters")
            
            # Step 2: Generate opportunity candidates from clusters
            opportunity_candidates = []
            for cluster in signal_clusters:
                if cluster.signal_count >= self.min_signals_for_opportunity:
                    candidate = await self._generate_opportunity_candidate(cluster)
                    if candidate and candidate.confidence_score >= self.confidence_threshold:
                        opportunity_candidates.append(candidate)
            
            logger.info(f"Generated {len(opportunity_candidates)} opportunity candidates")
            
            # Step 3: Deduplicate opportunities
            unique_candidates = await self._deduplicate_opportunities(db, opportunity_candidates)
            logger.info(f"After deduplication: {len(unique_candidates)} unique opportunities")
            
            # Step 4: Create opportunities in database
            created_opportunities = []
            for candidate in unique_candidates[:self.max_opportunities_per_batch]:
                opportunity = await self._create_opportunity_from_candidate(db, candidate)
                if opportunity:
                    created_opportunities.append(opportunity)
            
            logger.info(
                "Signal-to-opportunity conversion completed",
                batch_id=batch_id,
                created_count=len(created_opportunities)
            )
            
            return created_opportunities
            
        except Exception as e:
            logger.error(f"Signal-to-opportunity conversion failed: {e}", exc_info=True)
            raise
    
    async def _cluster_related_signals(
        self, 
        signals: List[Dict[str, Any]]
    ) -> List[SignalCluster]:
        """
        Cluster related market signals using semantic similarity.
        
        Args:
            signals: List of market signal data
            
        Returns:
            List of signal clusters
        """
        if not signals:
            return []
        
        # Group signals by basic similarity first
        clusters = []
        processed_signals = set()
        
        for i, signal in enumerate(signals):
            if i in processed_signals:
                continue
            
            # Start new cluster with this signal
            cluster_signals = [signal]
            processed_signals.add(i)
            
            # Find similar signals
            for j, other_signal in enumerate(signals[i+1:], i+1):
                if j in processed_signals:
                    continue
                
                similarity = await self._calculate_signal_similarity(signal, other_signal)
                if similarity >= self.similarity_threshold:
                    cluster_signals.append(other_signal)
                    processed_signals.add(j)
            
            # Create cluster if it has enough signals
            if len(cluster_signals) >= 2:  # Minimum cluster size
                cluster = await self._create_signal_cluster(cluster_signals)
                clusters.append(cluster)
        
        # Sort clusters by potential (highest first)
        clusters.sort(key=lambda c: c.market_potential, reverse=True)
        
        return clusters
    
    async def _calculate_signal_similarity(
        self, 
        signal1: Dict[str, Any], 
        signal2: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity between two signals.
        
        Args:
            signal1: First signal
            signal2: Second signal
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Extract content for comparison
        content1 = signal1.get("content", "").lower()
        content2 = signal2.get("content", "").lower()
        
        if not content1 or not content2:
            return 0.0
        
        # Simple keyword-based similarity (in production, use embeddings)
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # Boost similarity for same signal type
        type_bonus = 0.1 if signal1.get("signal_type") == signal2.get("signal_type") else 0.0
        
        # Boost similarity for same source
        source_bonus = 0.05 if signal1.get("source") == signal2.get("source") else 0.0
        
        total_similarity = min(1.0, jaccard_similarity + type_bonus + source_bonus)
        
        return total_similarity
    
    async def _create_signal_cluster(
        self, 
        cluster_signals: List[Dict[str, Any]]
    ) -> SignalCluster:
        """
        Create a signal cluster from grouped signals.
        
        Args:
            cluster_signals: List of signals in the cluster
            
        Returns:
            SignalCluster instance
        """
        cluster_id = f"cluster_{hashlib.md5(str(cluster_signals).encode()).hexdigest()[:8]}"
        
        # Extract dominant themes (keywords that appear frequently)
        all_content = " ".join(signal.get("content", "") for signal in cluster_signals)
        words = all_content.lower().split()
        word_freq = defaultdict(int)
        
        for word in words:
            if len(word) > 3:  # Skip short words
                word_freq[word] += 1
        
        # Get top themes
        dominant_themes = [
            word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # Calculate cluster metrics
        pain_intensity = await self._calculate_pain_intensity(cluster_signals)
        market_potential = await self._calculate_market_potential(cluster_signals)
        ai_opportunity_score = await self._calculate_ai_opportunity_score(cluster_signals)
        
        # Aggregate engagement metrics
        total_engagement = sum(
            signal.get("engagement_metrics", {}).get("total_engagement", 0)
            for signal in cluster_signals
        )
        
        # Calculate average sentiment
        sentiments = [
            signal.get("sentiment_score", 0.0) for signal in cluster_signals
            if signal.get("sentiment_score") is not None
        ]
        avg_sentiment = statistics.mean(sentiments) if sentiments else 0.0
        
        # Calculate confidence level
        confidence_level = await self._calculate_cluster_confidence(cluster_signals)
        
        return SignalCluster(
            cluster_id=cluster_id,
            signals=cluster_signals,
            dominant_themes=dominant_themes,
            pain_intensity=pain_intensity,
            market_potential=market_potential,
            ai_opportunity_score=ai_opportunity_score,
            signal_count=len(cluster_signals),
            total_engagement=total_engagement,
            avg_sentiment=avg_sentiment,
            confidence_level=confidence_level
        )
    
    async def _calculate_pain_intensity(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate pain intensity score for signal cluster."""
        pain_indicators = ["problem", "issue", "difficult", "hard", "struggle", "pain", "frustrating"]
        
        total_pain_score = 0.0
        for signal in signals:
            content = signal.get("content", "").lower()
            pain_count = sum(1 for indicator in pain_indicators if indicator in content)
            
            # Weight by engagement
            engagement = signal.get("engagement_metrics", {}).get("total_engagement", 1)
            signal_pain_score = pain_count * (1 + engagement / 100)
            total_pain_score += signal_pain_score
        
        # Normalize to 0-100 scale
        max_possible_score = len(signals) * len(pain_indicators) * 2  # Rough estimate
        normalized_score = min(100.0, (total_pain_score / max_possible_score) * 100)
        
        return normalized_score
    
    async def _calculate_market_potential(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate market potential score for signal cluster."""
        # Factors: signal diversity, engagement, source credibility
        
        # Source diversity
        unique_sources = len(set(signal.get("source", "unknown") for signal in signals))
        source_diversity_score = min(50.0, unique_sources * 10)
        
        # Engagement score
        total_engagement = sum(
            signal.get("engagement_metrics", {}).get("total_engagement", 0)
            for signal in signals
        )
        engagement_score = min(30.0, total_engagement / 10)
        
        # Signal type diversity
        signal_types = set(signal.get("signal_type", "unknown") for signal in signals)
        type_diversity_score = min(20.0, len(signal_types) * 5)
        
        market_potential = source_diversity_score + engagement_score + type_diversity_score
        return min(100.0, market_potential)
    
    async def _calculate_ai_opportunity_score(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate AI opportunity score for signal cluster."""
        ai_relevance_scores = [
            signal.get("ai_relevance_score", 0.0) for signal in signals
            if signal.get("ai_relevance_score") is not None
        ]
        
        if not ai_relevance_scores:
            return 0.0
        
        # Average AI relevance with bonus for consistency
        avg_relevance = statistics.mean(ai_relevance_scores)
        
        # Bonus for consistent AI relevance across signals
        relevance_variance = statistics.variance(ai_relevance_scores) if len(ai_relevance_scores) > 1 else 0
        consistency_bonus = max(0, 20 - relevance_variance)  # Lower variance = higher bonus
        
        ai_opportunity_score = min(100.0, avg_relevance + consistency_bonus)
        return ai_opportunity_score
    
    async def _calculate_cluster_confidence(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate confidence level for signal cluster."""
        confidence_factors = []
        
        # Signal count factor
        signal_count_factor = min(1.0, len(signals) / 10)  # Max confidence at 10+ signals
        confidence_factors.append(signal_count_factor)
        
        # Average signal confidence
        signal_confidences = [
            signal.get("confidence", 0.5) for signal in signals
            if signal.get("confidence") is not None
        ]
        avg_signal_confidence = statistics.mean(signal_confidences) if signal_confidences else 0.5
        confidence_factors.append(avg_signal_confidence)
        
        # Source credibility
        credible_sources = ["github", "stackoverflow", "reddit", "hackernews"]
        credible_signal_count = sum(
            1 for signal in signals
            if signal.get("source", "").lower() in credible_sources
        )
        source_credibility = credible_signal_count / len(signals)
        confidence_factors.append(source_credibility)
        
        # Overall confidence
        overall_confidence = statistics.mean(confidence_factors)
        return overall_confidence
    
    async def _generate_opportunity_candidate(
        self, 
        cluster: SignalCluster
    ) -> Optional[OpportunityCandidate]:
        """
        Generate an opportunity candidate from a signal cluster.
        
        Args:
            cluster: Signal cluster to convert
            
        Returns:
            OpportunityCandidate instance or None
        """
        try:
            # Generate title from dominant themes
            title = await self._generate_opportunity_title(cluster)
            
            # Generate description
            description = await self._generate_opportunity_description(cluster)
            
            # Generate problem statement
            problem_statement = await self._generate_problem_statement(cluster)
            
            # Generate proposed solution
            proposed_solution = await self._generate_proposed_solution(cluster)
            
            # Classify AI solution types
            ai_solution_types = await self._classify_ai_solution_types(cluster)
            
            # Identify target industries
            target_industries = await self._identify_target_industries(cluster)
            
            # Calculate scores
            confidence_score = cluster.confidence_level
            market_validation_score = (cluster.market_potential + cluster.pain_intensity) / 2
            ai_feasibility_score = cluster.ai_opportunity_score
            
            candidate_id = f"candidate_{datetime.utcnow().timestamp()}"
            
            return OpportunityCandidate(
                candidate_id=candidate_id,
                title=title,
                description=description,
                problem_statement=problem_statement,
                proposed_solution=proposed_solution,
                ai_solution_types=ai_solution_types,
                target_industries=target_industries,
                market_signals=[signal.get("signal_id", "") for signal in cluster.signals],
                confidence_score=confidence_score,
                market_validation_score=market_validation_score,
                ai_feasibility_score=ai_feasibility_score,
                source_cluster=cluster
            )
            
        except Exception as e:
            logger.error(f"Failed to generate opportunity candidate: {e}")
            return None
    
    async def _generate_opportunity_title(self, cluster: SignalCluster) -> str:
        """Generate opportunity title from cluster themes."""
        themes = cluster.dominant_themes[:3]  # Top 3 themes
        
        if not themes:
            return f"AI Opportunity from {cluster.signal_count} Market Signals"
        
        # Create title from themes
        title_parts = []
        for theme in themes:
            if theme in ["ai", "automation", "ml", "algorithm"]:
                title_parts.append("AI-Powered")
            elif theme in ["problem", "issue", "difficulty"]:
                title_parts.append("Solution for")
            else:
                title_parts.append(theme.title())
        
        title = " ".join(title_parts[:2])  # Keep it concise
        
        # Ensure it's a reasonable length
        if len(title) < 10:
            title = f"AI Solution for {themes[0].title()} Challenges"
        elif len(title) > 100:
            title = title[:97] + "..."
        
        return title
    
    async def _generate_opportunity_description(self, cluster: SignalCluster) -> str:
        """Generate opportunity description from cluster data."""
        description_parts = []
        
        # Market validation
        description_parts.append(
            f"This opportunity is validated by {cluster.signal_count} market signals "
            f"with a combined engagement of {cluster.total_engagement} interactions."
        )
        
        # Pain intensity
        if cluster.pain_intensity > 60:
            description_parts.append(
                "Market signals indicate high pain intensity, suggesting strong demand for solutions."
            )
        
        # AI suitability
        if cluster.ai_opportunity_score > 70:
            description_parts.append(
                "The problem characteristics make it highly suitable for AI-based solutions."
            )
        
        # Market potential
        if cluster.market_potential > 70:
            description_parts.append(
                "Strong market potential indicated by diverse sources and high engagement."
            )
        
        return " ".join(description_parts)
    
    async def _generate_problem_statement(self, cluster: SignalCluster) -> str:
        """Generate problem statement from cluster signals."""
        # Extract common pain points from signals
        pain_points = []
        for signal in cluster.signals:
            content = signal.get("content", "")
            if any(word in content.lower() for word in ["problem", "issue", "difficult", "struggle"]):
                # Extract the sentence containing the pain point
                sentences = content.split(".")
                for sentence in sentences:
                    if any(word in sentence.lower() for word in ["problem", "issue", "difficult"]):
                        pain_points.append(sentence.strip())
                        break
        
        if pain_points:
            # Use the most common pain point pattern
            return f"Users consistently report challenges with {cluster.dominant_themes[0]} " \
                   f"as evidenced by {len(pain_points)} specific complaints and discussions."
        else:
            return f"Market analysis reveals unmet needs in {cluster.dominant_themes[0]} " \
                   f"based on {cluster.signal_count} market signals."
    
    async def _generate_proposed_solution(self, cluster: SignalCluster) -> str:
        """Generate proposed AI solution from cluster analysis."""
        ai_types = await self._classify_ai_solution_types(cluster)
        
        if not ai_types:
            return "An AI-powered solution could address the identified market needs."
        
        primary_ai_type = ai_types[0].replace("_", " ").title()
        
        solution = f"A {primary_ai_type}-based solution could automate and optimize "
        
        if cluster.dominant_themes:
            solution += f"{cluster.dominant_themes[0]} processes, "
        
        solution += f"potentially serving the {cluster.signal_count} identified use cases "
        solution += f"with an estimated market validation score of {cluster.market_potential:.1f}%."
        
        return solution
    
    async def _classify_ai_solution_types(self, cluster: SignalCluster) -> List[str]:
        """Classify AI solution types based on cluster content."""
        all_content = " ".join(signal.get("content", "") for signal in cluster.signals).lower()
        
        detected_types = []
        for ai_type, keywords in self.ai_solution_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in all_content)
            if keyword_count > 0:
                detected_types.append((ai_type, keyword_count))
        
        # Sort by relevance and return top types
        detected_types.sort(key=lambda x: x[1], reverse=True)
        return [ai_type for ai_type, _ in detected_types[:3]]
    
    async def _identify_target_industries(self, cluster: SignalCluster) -> List[str]:
        """Identify target industries from cluster signals."""
        industry_keywords = {
            "healthcare": ["health", "medical", "patient", "doctor", "hospital"],
            "finance": ["finance", "banking", "payment", "trading", "investment"],
            "retail": ["retail", "shopping", "ecommerce", "customer", "sales"],
            "manufacturing": ["manufacturing", "production", "factory", "supply"],
            "education": ["education", "learning", "student", "teacher", "course"],
            "technology": ["software", "development", "programming", "tech", "app"]
        }
        
        all_content = " ".join(signal.get("content", "") for signal in cluster.signals).lower()
        
        detected_industries = []
        for industry, keywords in industry_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in all_content)
            if keyword_count > 0:
                detected_industries.append((industry, keyword_count))
        
        # Sort by relevance and return top industries
        detected_industries.sort(key=lambda x: x[1], reverse=True)
        return [industry for industry, _ in detected_industries[:2]]
    
    async def _deduplicate_opportunities(
        self, 
        db: AsyncSession,
        candidates: List[OpportunityCandidate]
    ) -> List[OpportunityCandidate]:
        """
        Deduplicate opportunity candidates against existing opportunities.
        
        Args:
            db: Database session
            candidates: List of opportunity candidates
            
        Returns:
            List of unique opportunity candidates
        """
        unique_candidates = []
        
        for candidate in candidates:
            duplication_result = await self._check_opportunity_duplication(db, candidate)
            
            if not duplication_result.is_duplicate:
                unique_candidates.append(candidate)
                logger.debug(f"Opportunity candidate {candidate.candidate_id} is unique")
            else:
                logger.info(
                    f"Opportunity candidate {candidate.candidate_id} is duplicate",
                    similarity_score=duplication_result.similarity_score,
                    existing_id=duplication_result.existing_opportunity_id,
                    similarity_type=duplication_result.similarity_type
                )
        
        return unique_candidates
    
    async def _check_opportunity_duplication(
        self, 
        db: AsyncSession,
        candidate: OpportunityCandidate
    ) -> DuplicationResult:
        """
        Check if opportunity candidate is a duplicate of existing opportunities.
        
        Args:
            db: Database session
            candidate: Opportunity candidate to check
            
        Returns:
            DuplicationResult with duplication analysis
        """
        # Get recent opportunities for comparison (last 90 days)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        query = select(Opportunity).where(
            and_(
                Opportunity.created_at >= cutoff_date,
                Opportunity.status != OpportunityStatus.REJECTED
            )
        ).order_by(desc(Opportunity.created_at)).limit(100)  # Limit for performance
        
        result = await db.execute(query)
        existing_opportunities = result.scalars().all()
        
        if not existing_opportunities:
            return DuplicationResult(is_duplicate=False, similarity_score=0.0)
        
        # Check for duplicates
        for existing_opp in existing_opportunities:
            # Exact title match
            if self._normalize_text(candidate.title) == self._normalize_text(existing_opp.title):
                return DuplicationResult(
                    is_duplicate=True,
                    similarity_score=1.0,
                    existing_opportunity_id=existing_opp.id,
                    similarity_type="exact",
                    confidence=1.0
                )
            
            # Semantic similarity check
            semantic_similarity = await self._calculate_semantic_similarity(
                candidate, existing_opp
            )
            
            if semantic_similarity >= self.exact_match_threshold:
                return DuplicationResult(
                    is_duplicate=True,
                    similarity_score=semantic_similarity,
                    existing_opportunity_id=existing_opp.id,
                    similarity_type="semantic",
                    confidence=0.9
                )
            elif semantic_similarity >= self.semantic_similarity_threshold:
                return DuplicationResult(
                    is_duplicate=True,
                    similarity_score=semantic_similarity,
                    existing_opportunity_id=existing_opp.id,
                    similarity_type="semantic",
                    confidence=0.8
                )
            elif semantic_similarity >= self.partial_similarity_threshold:
                # Partial similarity - might be related but not duplicate
                # For now, we'll allow it but log it
                logger.info(
                    f"Partial similarity detected",
                    candidate_id=candidate.candidate_id,
                    existing_id=existing_opp.id,
                    similarity=semantic_similarity
                )
        
        return DuplicationResult(is_duplicate=False, similarity_score=0.0)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        
        # Convert to lowercase, remove extra spaces, remove punctuation
        import re
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    async def _calculate_semantic_similarity(
        self, 
        candidate: OpportunityCandidate,
        existing_opportunity: Opportunity
    ) -> float:
        """
        Calculate semantic similarity between candidate and existing opportunity.
        
        Args:
            candidate: Opportunity candidate
            existing_opportunity: Existing opportunity
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # For now, use simple text similarity
        # In production, this would use vector embeddings
        
        candidate_text = f"{candidate.title} {candidate.description}".lower()
        existing_text = f"{existing_opportunity.title} {existing_opportunity.description}".lower()
        
        # Simple word-based similarity
        candidate_words = set(candidate_text.split())
        existing_words = set(existing_text.split())
        
        if not candidate_words or not existing_words:
            return 0.0
        
        intersection = len(candidate_words.intersection(existing_words))
        union = len(candidate_words.union(existing_words))
        
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # Boost similarity for same AI solution types
        candidate_ai_types = set(candidate.ai_solution_types)
        existing_ai_types = set()
        
        if existing_opportunity.ai_solution_types:
            try:
                existing_ai_types = set(json.loads(existing_opportunity.ai_solution_types))
            except json.JSONDecodeError:
                pass
        
        ai_type_similarity = 0.0
        if candidate_ai_types and existing_ai_types:
            ai_intersection = len(candidate_ai_types.intersection(existing_ai_types))
            ai_union = len(candidate_ai_types.union(existing_ai_types))
            ai_type_similarity = ai_intersection / ai_union if ai_union > 0 else 0.0
        
        # Combined similarity
        combined_similarity = (jaccard_similarity * 0.7) + (ai_type_similarity * 0.3)
        
        return combined_similarity
    
    async def _create_opportunity_from_candidate(
        self, 
        db: AsyncSession,
        candidate: OpportunityCandidate
    ) -> Optional[Opportunity]:
        """
        Create an opportunity in the database from a candidate.
        
        Args:
            db: Database session
            candidate: Opportunity candidate
            
        Returns:
            Created Opportunity instance or None
        """
        try:
            # Prepare JSON fields
            ai_solution_types_json = json.dumps(candidate.ai_solution_types) if candidate.ai_solution_types else None
            target_industries_json = json.dumps(candidate.target_industries) if candidate.target_industries else None
            tags_json = json.dumps(candidate.source_cluster.dominant_themes) if candidate.source_cluster.dominant_themes else None
            
            # Create opportunity directly
            opportunity = Opportunity(
                title=candidate.title,
                description=candidate.description,
                summary=candidate.problem_statement[:500] if candidate.problem_statement else None,
                ai_solution_types=ai_solution_types_json,
                target_industries=target_industries_json,
                discovery_method="OpportunityEngine",
                tags=tags_json,
                status=OpportunityStatus.DISCOVERED,
                validation_score=candidate.market_validation_score / 10,  # Convert to 0-10 scale
                ai_feasibility_score=candidate.ai_feasibility_score / 10,  # Convert to 0-10 scale
                confidence_rating=candidate.confidence_score * 10  # Convert to 0-10 scale
            )
            
            db.add(opportunity)
            await db.commit()
            await db.refresh(opportunity)
            
            logger.info(
                "Opportunity created from candidate",
                opportunity_id=opportunity.id,
                candidate_id=candidate.candidate_id,
                title=opportunity.title
            )
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Failed to create opportunity from candidate: {e}", exc_info=True)
            await db.rollback()
            return None


# Global opportunity engine instance
opportunity_engine = OpportunityEngine()