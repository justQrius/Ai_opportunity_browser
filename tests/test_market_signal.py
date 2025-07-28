"""Tests for MarketSignal model and service."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, Mock

from shared.models.market_signal import MarketSignal, SignalType
from shared.schemas.market_signal import MarketSignalCreate, MarketSignalSearch
from shared.services.market_signal_service import MarketSignalService


class TestMarketSignalModel:
    """Test MarketSignal model functionality."""
    
    def test_market_signal_model_creation(self):
        """Test MarketSignal model instance creation."""
        signal = MarketSignal(
            source="reddit",
            signal_type=SignalType.PAIN_POINT,
            content="Users are struggling with manual data entry tasks",
            extracted_at=datetime.utcnow(),
            sentiment_score=-0.6,
            confidence_level=0.8
        )
        
        assert signal.source == "reddit"
        assert signal.signal_type == SignalType.PAIN_POINT
        assert signal.sentiment_score == -0.6
        assert signal.confidence_level == 0.8
        assert signal.upvotes == 0  # Default value
    
    def test_signal_type_enum(self):
        """Test signal type enumeration."""
        assert SignalType.PAIN_POINT == "pain_point"
        assert SignalType.FEATURE_REQUEST == "feature_request"
        assert SignalType.COMPLAINT == "complaint"
        assert SignalType.OPPORTUNITY == "opportunity"
        assert SignalType.TREND == "trend"
        assert SignalType.DISCUSSION == "discussion"
    
    def test_market_signal_repr(self):
        """Test MarketSignal string representation."""
        signal = MarketSignal(
            id="test-id",
            source="github",
            signal_type=SignalType.FEATURE_REQUEST,
            content="Test content",
            extracted_at=datetime.utcnow()
        )
        
        repr_str = repr(signal)
        assert "github" in repr_str
        assert "feature_request" in repr_str


class TestMarketSignalService:
    """Test MarketSignalService functionality."""
    
    @pytest.fixture
    def signal_service(self):
        """Create MarketSignalService instance."""
        return MarketSignalService()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock()
    
    @pytest.fixture
    def sample_signal_create(self):
        """Sample market signal creation data."""
        return MarketSignalCreate(
            source="reddit",
            source_id="reddit_post_123",
            source_url="https://reddit.com/r/MachineLearning/comments/123",
            signal_type=SignalType.PAIN_POINT,
            title="Struggling with ML model deployment",
            content="I've built a great ML model but can't figure out how to deploy it to production. The existing tools are too complex and require DevOps expertise I don't have.",
            author="ml_researcher",
            author_reputation=85.5,
            upvotes=45,
            downvotes=3,
            comments_count=12,
            extracted_at=datetime.utcnow(),
            keywords=["ml", "deployment", "production", "devops"],
            categories=["machine_learning", "deployment", "pain_point"]
        )
    
    @pytest.mark.asyncio
    async def test_create_market_signal(self, signal_service, mock_db_session, sample_signal_create):
        """Test market signal creation."""
        # Mock database operations
        mock_db_session.add = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()
        
        with patch.object(signal_service, '_clear_signal_caches', return_value=None), \
             patch.object(signal_service, '_trigger_analysis_workflow', return_value=None):
            
            signal = await signal_service.create_market_signal(
                mock_db_session, 
                sample_signal_create,
                agent_name="reddit_monitoring_agent"
            )
            
            assert signal.source == sample_signal_create.source
            assert signal.signal_type == sample_signal_create.signal_type
            assert signal.content == sample_signal_create.content
            assert signal.upvotes == 45
            assert signal.processing_version == "agent_reddit_monitoring_agent"
            
            # Verify JSON fields are properly serialized
            assert signal.keywords is not None
            assert signal.categories is not None
    
    @pytest.mark.asyncio
    async def test_process_signal_analysis(self, signal_service, mock_db_session):
        """Test processing AI analysis results."""
        signal_id = "test-signal-id"
        
        # Mock existing signal
        existing_signal = MarketSignal(
            id=signal_id,
            source="reddit",
            signal_type=SignalType.PAIN_POINT,
            content="Test content",
            extracted_at=datetime.utcnow()
        )
        
        analysis_results = {
            "sentiment_score": -0.7,
            "confidence_level": 0.85,
            "pain_point_intensity": 0.8,
            "ai_relevance_score": 0.9,
            "market_validation_signals": ["high_engagement", "expert_discussion"],
            "extracted_keywords": ["ai", "automation", "deployment"],
            "categories": ["artificial_intelligence", "automation"]
        }
        
        with patch.object(signal_service, 'get_signal_by_id', return_value=existing_signal), \
             patch.object(signal_service, '_clear_signal_caches', return_value=None), \
             patch.object(signal_service, '_evaluate_opportunity_generation', return_value=None):
            
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            updated_signal = await signal_service.process_signal_analysis(
                mock_db_session, signal_id, analysis_results, "analysis_agent_v1"
            )
            
            assert updated_signal is not None
            assert updated_signal.sentiment_score == -0.7
            assert updated_signal.confidence_level == 0.85
            assert updated_signal.pain_point_intensity == 0.8
            assert updated_signal.ai_relevance_score == 0.9
            assert updated_signal.processed_at is not None
            assert updated_signal.processing_version == "analysis_analysis_agent_v1"
    
    @pytest.mark.asyncio
    async def test_get_signal_by_id(self, signal_service, mock_db_session):
        """Test getting signal by ID."""
        signal_id = "test-signal-id"
        
        # Mock database result
        mock_signal = MarketSignal(
            id=signal_id,
            source="github",
            signal_type=SignalType.FEATURE_REQUEST,
            content="Feature request content",
            extracted_at=datetime.utcnow()
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_signal
        mock_db_session.execute.return_value = mock_result
        
        signal = await signal_service.get_signal_by_id(mock_db_session, signal_id)
        
        assert signal is not None
        assert signal.id == signal_id
        assert signal.source == "github"
        mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_signals_with_filters(self, signal_service, mock_db_session):
        """Test searching signals with various filters."""
        search_params = MarketSignalSearch(
            source="reddit",
            signal_type=SignalType.PAIN_POINT,
            min_sentiment_score=-1.0,
            max_sentiment_score=-0.5,
            min_confidence_level=0.7,
            date_from=datetime.utcnow() - timedelta(days=7),
            date_to=datetime.utcnow()
        )
        
        # Mock search results
        mock_signals = [
            MarketSignal(
                id="signal1",
                source="reddit",
                signal_type=SignalType.PAIN_POINT,
                content="Pain point 1",
                sentiment_score=-0.8,
                confidence_level=0.9,
                extracted_at=datetime.utcnow() - timedelta(days=2)
            ),
            MarketSignal(
                id="signal2",
                source="reddit",
                signal_type=SignalType.PAIN_POINT,
                content="Pain point 2",
                sentiment_score=-0.6,
                confidence_level=0.8,
                extracted_at=datetime.utcnow() - timedelta(days=1)
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_signals
        mock_db_session.execute.return_value = mock_result
        
        signals = await signal_service.search_signals(
            mock_db_session, search_params, limit=10
        )
        
        assert len(signals) == 2
        assert signals[0].source == "reddit"
        assert signals[0].signal_type == SignalType.PAIN_POINT
        assert signals[1].sentiment_score == -0.6
    
    @pytest.mark.asyncio
    async def test_find_similar_signals(self, signal_service, mock_db_session):
        """Test finding similar signals using keyword overlap."""
        reference_signal_id = "ref-signal-id"
        
        # Mock reference signal
        reference_signal = MarketSignal(
            id=reference_signal_id,
            source="reddit",
            signal_type=SignalType.PAIN_POINT,
            content="ML deployment issues",
            keywords='["ml", "deployment", "production"]',
            extracted_at=datetime.utcnow()
        )
        
        # Mock candidate signals
        candidate_signals = [
            MarketSignal(
                id="candidate1",
                source="reddit",
                signal_type=SignalType.PAIN_POINT,
                content="Production ML problems",
                keywords='["ml", "production", "issues"]',  # 2/4 overlap = 0.5
                extracted_at=datetime.utcnow()
            ),
            MarketSignal(
                id="candidate2",
                source="reddit",
                signal_type=SignalType.FEATURE_REQUEST,
                content="Better deployment tools",
                keywords='["deployment", "tools", "automation"]',  # 1/5 overlap = 0.2
                extracted_at=datetime.utcnow()
            ),
            MarketSignal(
                id="candidate3",
                source="reddit",
                signal_type=SignalType.PAIN_POINT,
                content="ML deployment automation",
                keywords='["ml", "deployment", "automation", "production"]',  # 3/4 overlap = 0.75
                extracted_at=datetime.utcnow()
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = candidate_signals
        mock_db_session.execute.return_value = mock_result
        
        with patch.object(signal_service, 'get_signal_by_id', return_value=reference_signal):
            similar_signals = await signal_service.find_similar_signals(
                mock_db_session, reference_signal_id, similarity_threshold=0.6, limit=5
            )
            
            # Should return candidate3 (0.75 similarity) but not others
            assert len(similar_signals) == 1
            assert similar_signals[0].id == "candidate3"
    
    @pytest.mark.asyncio
    async def test_get_trending_signals(self, signal_service, mock_db_session):
        """Test getting trending signals based on engagement."""
        # Mock trending signals
        trending_signals = [
            MarketSignal(
                id="trending1",
                source="reddit",
                signal_type=SignalType.PAIN_POINT,
                content="High engagement pain point",
                upvotes=150,
                comments_count=45,
                shares_count=20,
                pain_point_intensity=0.9,
                extracted_at=datetime.utcnow() - timedelta(hours=2)
            ),
            MarketSignal(
                id="trending2",
                source="github",
                signal_type=SignalType.FEATURE_REQUEST,
                content="Popular feature request",
                upvotes=80,
                comments_count=30,
                shares_count=15,
                pain_point_intensity=0.7,
                extracted_at=datetime.utcnow() - timedelta(hours=1)
            )
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = trending_signals
        mock_db_session.execute.return_value = mock_result
        
        signals = await signal_service.get_trending_signals(
            mock_db_session, timeframe_hours=24, min_engagement=10, limit=10
        )
        
        assert len(signals) == 2
        assert signals[0].id == "trending1"
        assert signals[0].upvotes == 150
        assert signals[1].comments_count == 30
    
    @pytest.mark.asyncio
    async def test_get_signal_analytics(self, signal_service, mock_db_session):
        """Test signal analytics generation."""
        # Mock database queries for analytics
        mock_total_count = AsyncMock()
        mock_total_count.scalar.return_value = 250
        
        mock_source_stats = [
            Mock(source="reddit", count=120),
            Mock(source="github", count=80),
            Mock(source="twitter", count=50)
        ]
        
        mock_type_stats = [
            Mock(signal_type=SignalType.PAIN_POINT, count=100),
            Mock(signal_type=SignalType.FEATURE_REQUEST, count=80),
            Mock(signal_type=SignalType.COMPLAINT, count=70)
        ]
        
        mock_avg_stats = Mock(avg_sentiment=-0.3, avg_confidence=0.75)
        
        # Mock database execution sequence
        mock_db_session.execute.side_effect = [
            mock_total_count,
            mock_source_stats,
            mock_type_stats,
            AsyncMock(first=lambda: mock_avg_stats)
        ]
        
        analytics = await signal_service.get_signal_analytics(
            mock_db_session, timeframe_days=7
        )
        
        assert analytics["total_signals"] == 250
        assert analytics["signals_by_source"]["reddit"] == 120
        assert analytics["signals_by_type"]["pain_point"] == 100
        assert analytics["average_sentiment"] == -0.3
        assert analytics["average_confidence"] == 0.75
        assert analytics["timeframe_days"] == 7
        assert "generated_at" in analytics
    
    @pytest.mark.asyncio
    async def test_trigger_analysis_workflow(self, signal_service, mock_db_session):
        """Test analysis workflow triggering."""
        signal = MarketSignal(
            id="test-signal",
            source="reddit",
            signal_type=SignalType.PAIN_POINT,
            content="Test content for analysis",
            extracted_at=datetime.utcnow()
        )
        
        # Should not raise any exceptions
        await signal_service._trigger_analysis_workflow(mock_db_session, signal)
        
        # In a real implementation, this would queue the signal for AI analysis
        # For now, we just verify it doesn't crash
    
    @pytest.mark.asyncio
    async def test_evaluate_opportunity_generation(self, signal_service, mock_db_session):
        """Test opportunity generation evaluation."""
        # High-quality signal that should trigger opportunity generation
        high_quality_signal = MarketSignal(
            id="high-quality-signal",
            source="reddit",
            signal_type=SignalType.PAIN_POINT,
            content="High-quality pain point",
            pain_point_intensity=0.8,
            ai_relevance_score=0.7,
            confidence_level=0.9,
            extracted_at=datetime.utcnow()
        )
        
        # Should not raise any exceptions
        await signal_service._evaluate_opportunity_generation(mock_db_session, high_quality_signal)
        
        # Low-quality signal that should not trigger opportunity generation
        low_quality_signal = MarketSignal(
            id="low-quality-signal",
            source="reddit",
            signal_type=SignalType.DISCUSSION,
            content="Low-quality discussion",
            pain_point_intensity=0.3,
            ai_relevance_score=0.4,
            confidence_level=0.5,
            extracted_at=datetime.utcnow()
        )
        
        # Should not raise any exceptions
        await signal_service._evaluate_opportunity_generation(mock_db_session, low_quality_signal)