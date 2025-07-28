"""
Tests for OpportunityEngine core implementation.
Tests signal-to-opportunity conversion and deduplication logic.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from shared.services.opportunity_engine import (
    OpportunityEngine, 
    SignalCluster, 
    OpportunityCandidate,
    DuplicationResult
)
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.market_signal import MarketSignal, SignalType


class TestOpportunityEngine:
    """Test cases for OpportunityEngine core functionality."""
    
    @pytest.fixture
    def engine(self):
        """Create OpportunityEngine instance for testing."""
        config = {
            "min_signals_for_opportunity": 2,  # Lower for testing
            "similarity_threshold": 0.7,
            "confidence_threshold": 0.6,
            "max_opportunities_per_batch": 5
        }
        return OpportunityEngine(config)
    
    @pytest.fixture
    def sample_signals(self):
        """Sample market signals for testing."""
        return [
            {
                "signal_id": "signal_1",
                "content": "I'm struggling with manual data entry tasks that take hours every day",
                "signal_type": "pain_point",
                "source": "reddit",
                "engagement_metrics": {"total_engagement": 25},
                "ai_relevance_score": 85.0,
                "confidence": 0.8,
                "sentiment_score": -0.6
            },
            {
                "signal_id": "signal_2", 
                "content": "Need automation for repetitive data processing workflows",
                "signal_type": "feature_request",
                "source": "github",
                "engagement_metrics": {"total_engagement": 15},
                "ai_relevance_score": 90.0,
                "confidence": 0.9,
                "sentiment_score": -0.4
            },
            {
                "signal_id": "signal_3",
                "content": "Looking for ML solution to classify documents automatically",
                "signal_type": "opportunity",
                "source": "stackoverflow",
                "engagement_metrics": {"total_engagement": 30},
                "ai_relevance_score": 95.0,
                "confidence": 0.85,
                "sentiment_score": 0.2
            },
            {
                "signal_id": "signal_4",
                "content": "Manual invoice processing is killing our productivity",
                "signal_type": "pain_point",
                "source": "reddit",
                "engagement_metrics": {"total_engagement": 40},
                "ai_relevance_score": 75.0,
                "confidence": 0.7,
                "sentiment_score": -0.8
            }
        ]
    
    @pytest.fixture
    def sample_cluster(self, sample_signals):
        """Sample signal cluster for testing."""
        return SignalCluster(
            cluster_id="test_cluster_1",
            signals=sample_signals[:3],
            dominant_themes=["automation", "data", "processing"],
            pain_intensity=75.0,
            market_potential=80.0,
            ai_opportunity_score=85.0,
            signal_count=3,
            total_engagement=70,
            avg_sentiment=-0.3,
            confidence_level=0.8
        )
    
    @pytest.mark.asyncio
    async def test_signal_similarity_calculation(self, engine):
        """Test signal similarity calculation."""
        signal1 = {
            "content": "I need automation for data processing tasks",
            "signal_type": "pain_point",
            "source": "reddit"
        }
        
        signal2 = {
            "content": "Looking for automated data processing solutions",
            "signal_type": "feature_request", 
            "source": "github"
        }
        
        signal3 = {
            "content": "How to build a mobile app for iOS",
            "signal_type": "question",
            "source": "stackoverflow"
        }
        
        # Similar signals should have high similarity
        similarity_12 = await engine._calculate_signal_similarity(signal1, signal2)
        assert similarity_12 > 0.5, f"Expected high similarity, got {similarity_12}"
        
        # Dissimilar signals should have low similarity
        similarity_13 = await engine._calculate_signal_similarity(signal1, signal3)
        assert similarity_13 < 0.3, f"Expected low similarity, got {similarity_13}"
    
    @pytest.mark.asyncio
    async def test_signal_clustering(self, engine, sample_signals):
        """Test signal clustering functionality."""
        clusters = await engine._cluster_related_signals(sample_signals)
        
        assert len(clusters) > 0, "Should create at least one cluster"
        
        # Check cluster properties
        for cluster in clusters:
            assert cluster.signal_count >= 2, "Clusters should have at least 2 signals"
            assert len(cluster.dominant_themes) > 0, "Clusters should have dominant themes"
            assert 0 <= cluster.pain_intensity <= 100, "Pain intensity should be 0-100"
            assert 0 <= cluster.market_potential <= 100, "Market potential should be 0-100"
            assert 0 <= cluster.ai_opportunity_score <= 100, "AI opportunity score should be 0-100"
    
    @pytest.mark.asyncio
    async def test_opportunity_candidate_generation(self, engine, sample_cluster):
        """Test opportunity candidate generation from cluster."""
        candidate = await engine._generate_opportunity_candidate(sample_cluster)
        
        assert candidate is not None, "Should generate opportunity candidate"
        assert len(candidate.title) > 0, "Candidate should have title"
        assert len(candidate.description) > 0, "Candidate should have description"
        assert len(candidate.problem_statement) > 0, "Candidate should have problem statement"
        assert len(candidate.proposed_solution) > 0, "Candidate should have proposed solution"
        assert len(candidate.ai_solution_types) > 0, "Candidate should have AI solution types"
        assert 0 <= candidate.confidence_score <= 1, "Confidence score should be 0-1"
    
    @pytest.mark.asyncio
    async def test_ai_solution_type_classification(self, engine, sample_cluster):
        """Test AI solution type classification."""
        ai_types = await engine._classify_ai_solution_types(sample_cluster)
        
        assert len(ai_types) > 0, "Should classify at least one AI solution type"
        
        # Check that classified types are valid
        valid_types = set(engine.ai_solution_keywords.keys())
        for ai_type in ai_types:
            assert ai_type in valid_types, f"Invalid AI solution type: {ai_type}"
    
    @pytest.mark.asyncio
    async def test_target_industry_identification(self, engine, sample_cluster):
        """Test target industry identification."""
        industries = await engine._identify_target_industries(sample_cluster)
        
        # Should identify at least one industry or return empty list
        assert isinstance(industries, list), "Should return list of industries"
        
        # If industries identified, they should be valid
        valid_industries = ["healthcare", "finance", "retail", "manufacturing", "education", "technology"]
        for industry in industries:
            assert industry in valid_industries, f"Invalid industry: {industry}"
    
    @pytest.mark.asyncio
    async def test_text_normalization(self, engine):
        """Test text normalization for deduplication."""
        text1 = "AI-Powered Solution for Data Processing!"
        text2 = "ai powered solution for data processing"
        text3 = "  AI   Powered   Solution   for   Data   Processing  "
        
        norm1 = engine._normalize_text(text1)
        norm2 = engine._normalize_text(text2)
        norm3 = engine._normalize_text(text3)
        
        assert norm1 == norm2 == norm3, "Normalized texts should be identical"
        assert norm1 == "ai powered solution for data processing"
    
    @pytest.mark.asyncio
    async def test_semantic_similarity_calculation(self, engine):
        """Test semantic similarity calculation between opportunities."""
        candidate = OpportunityCandidate(
            candidate_id="test_candidate",
            title="AI-Powered Data Processing Automation",
            description="Automate manual data entry and processing tasks using machine learning",
            problem_statement="Users struggle with manual data processing",
            proposed_solution="ML-based automation solution",
            ai_solution_types=["machine_learning", "automation"],
            target_industries=["technology"],
            market_signals=["signal_1", "signal_2"],
            confidence_score=0.8,
            market_validation_score=75.0,
            ai_feasibility_score=85.0,
            source_cluster=None
        )
        
        # Create mock existing opportunity
        existing_opp = MagicMock()
        existing_opp.title = "Automated Data Processing with AI"
        existing_opp.description = "Machine learning solution for automating data entry tasks"
        existing_opp.ai_solution_types = '["machine_learning", "automation"]'
        
        similarity = await engine._calculate_semantic_similarity(candidate, existing_opp)
        
        assert 0 <= similarity <= 1, "Similarity should be between 0 and 1"
        assert similarity > 0.5, "Similar opportunities should have high similarity score"
    
    @pytest.mark.asyncio
    async def test_duplication_detection_exact_match(self, engine):
        """Test exact duplicate detection."""
        candidate = OpportunityCandidate(
            candidate_id="test_candidate",
            title="AI Data Processing Solution",
            description="Test description",
            problem_statement="Test problem",
            proposed_solution="Test solution",
            ai_solution_types=["machine_learning"],
            target_industries=["technology"],
            market_signals=["signal_1"],
            confidence_score=0.8,
            market_validation_score=75.0,
            ai_feasibility_score=85.0,
            source_cluster=None
        )
        
        # Mock database session and existing opportunity
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_existing_opp = MagicMock()
        mock_existing_opp.id = "existing_opp_1"
        mock_existing_opp.title = "AI Data Processing Solution"  # Exact match
        mock_existing_opp.description = "Existing description"
        mock_existing_opp.created_at = datetime.utcnow()
        
        mock_result.scalars.return_value.all.return_value = [mock_existing_opp]
        mock_db.execute.return_value = mock_result
        
        duplication_result = await engine._check_opportunity_duplication(mock_db, candidate)
        
        assert duplication_result.is_duplicate, "Should detect exact duplicate"
        assert duplication_result.similarity_type == "exact"
        assert duplication_result.similarity_score == 1.0
        assert duplication_result.existing_opportunity_id == "existing_opp_1"
    
    @pytest.mark.asyncio
    async def test_duplication_detection_no_match(self, engine):
        """Test no duplicate detection."""
        candidate = OpportunityCandidate(
            candidate_id="test_candidate",
            title="Unique AI Solution for Healthcare",
            description="Completely different solution",
            problem_statement="Different problem",
            proposed_solution="Different solution",
            ai_solution_types=["computer_vision"],
            target_industries=["healthcare"],
            market_signals=["signal_1"],
            confidence_score=0.8,
            market_validation_score=75.0,
            ai_feasibility_score=85.0,
            source_cluster=None
        )
        
        # Mock database session with different existing opportunity
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_existing_opp = MagicMock()
        mock_existing_opp.id = "existing_opp_1"
        mock_existing_opp.title = "Finance Trading Bot"  # Completely different
        mock_existing_opp.description = "Automated trading solution"
        mock_existing_opp.ai_solution_types = '["machine_learning"]'
        mock_existing_opp.created_at = datetime.utcnow()
        
        mock_result.scalars.return_value.all.return_value = [mock_existing_opp]
        mock_db.execute.return_value = mock_result
        
        duplication_result = await engine._check_opportunity_duplication(mock_db, candidate)
        
        assert not duplication_result.is_duplicate, "Should not detect duplicate"
        assert duplication_result.similarity_score < 0.5, "Similarity should be low"
    
    @pytest.mark.asyncio
    async def test_empty_signals_handling(self, engine):
        """Test handling of empty signal list."""
        clusters = await engine._cluster_related_signals([])
        assert len(clusters) == 0, "Empty signals should produce no clusters"
    
    @pytest.mark.asyncio
    async def test_insufficient_signals_for_opportunity(self, engine):
        """Test handling when insufficient signals for opportunity creation."""
        # Single signal (below minimum threshold)
        single_signal = [{
            "signal_id": "signal_1",
            "content": "Single signal content",
            "signal_type": "pain_point",
            "source": "reddit",
            "engagement_metrics": {"total_engagement": 10},
            "ai_relevance_score": 80.0,
            "confidence": 0.8
        }]
        
        clusters = await engine._cluster_related_signals(single_signal)
        
        # Should not create clusters with insufficient signals
        valid_clusters = [c for c in clusters if c.signal_count >= engine.min_signals_for_opportunity]
        assert len(valid_clusters) == 0, "Should not create opportunities from insufficient signals"
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, engine):
        """Test that low-confidence candidates are filtered out."""
        # Create low-confidence cluster
        low_confidence_cluster = SignalCluster(
            cluster_id="low_confidence",
            signals=[{"signal_id": "s1", "content": "test"}],
            dominant_themes=["test"],
            pain_intensity=30.0,
            market_potential=25.0,
            ai_opportunity_score=20.0,
            signal_count=2,
            total_engagement=5,
            avg_sentiment=0.0,
            confidence_level=0.3  # Below threshold
        )
        
        candidate = await engine._generate_opportunity_candidate(low_confidence_cluster)
        
        # Candidate should be generated but with low confidence
        assert candidate is not None
        assert candidate.confidence_score < engine.confidence_threshold
    
    def test_engine_initialization(self):
        """Test OpportunityEngine initialization with custom config."""
        custom_config = {
            "min_signals_for_opportunity": 5,
            "similarity_threshold": 0.9,
            "confidence_threshold": 0.8
        }
        
        engine = OpportunityEngine(custom_config)
        
        assert engine.min_signals_for_opportunity == 5
        assert engine.similarity_threshold == 0.9
        assert engine.confidence_threshold == 0.8
        assert engine.config == custom_config
    
    def test_engine_default_initialization(self):
        """Test OpportunityEngine initialization with default config."""
        engine = OpportunityEngine()
        
        assert engine.min_signals_for_opportunity == 3  # Default value
        assert engine.similarity_threshold == 0.85  # Default value
        assert engine.confidence_threshold == 0.7  # Default value


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])