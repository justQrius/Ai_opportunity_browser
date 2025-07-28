#!/usr/bin/env python3
"""
Simple test script for OpportunityEngine core functionality.
Tests the core signal-to-opportunity conversion logic without database dependencies.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly to avoid circular dependencies
import importlib.util
import sys
import os

# Load the module directly
spec = importlib.util.spec_from_file_location(
    "opportunity_engine", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                 "shared", "services", "opportunity_engine.py")
)
opportunity_engine_module = importlib.util.module_from_spec(spec)

# Mock the dependencies that cause circular imports
class MockOpportunityService:
    pass

class MockCacheManager:
    async def get(self, key): return None
    async def set(self, key, value, expire=None): pass
    async def delete(self, key): pass

class MockCacheKeys:
    @staticmethod
    def format_key(template, **kwargs): return f"mock_key_{kwargs}"

# Patch the imports before loading
sys.modules['shared.cache'] = type('MockModule', (), {
    'cache_manager': MockCacheManager(),
    'CacheKeys': MockCacheKeys()
})()

sys.modules['shared.vector_db'] = type('MockModule', (), {
    'vector_db_manager': None,
    'opportunity_vector_service': None,
    'market_signal_vector_service': None
})()

sys.modules['shared.schemas.opportunity'] = type('MockModule', (), {
    'OpportunityCreate': dict
})()

# Now load the module
spec.loader.exec_module(opportunity_engine_module)

OpportunityEngine = opportunity_engine_module.OpportunityEngine
SignalCluster = opportunity_engine_module.SignalCluster


async def test_signal_similarity():
    """Test signal similarity calculation."""
    print("Testing signal similarity calculation...")
    
    engine = OpportunityEngine()
    
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
    print(f"Similarity between similar signals: {similarity_12:.3f}")
    
    # Dissimilar signals should have low similarity
    similarity_13 = await engine._calculate_signal_similarity(signal1, signal3)
    print(f"Similarity between dissimilar signals: {similarity_13:.3f}")
    
    assert similarity_12 >= 0.25, f"Expected reasonable similarity, got {similarity_12}"
    assert similarity_13 < 0.15, f"Expected low similarity, got {similarity_13}"
    print("✓ Signal similarity test passed")


async def test_signal_clustering():
    """Test signal clustering functionality."""
    print("\nTesting signal clustering...")
    
    engine = OpportunityEngine({
        "min_signals_for_opportunity": 2,
        "similarity_threshold": 0.2  # Lower threshold for clustering
    })
    
    sample_signals = [
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
    
    clusters = await engine._cluster_related_signals(sample_signals)
    
    print(f"Created {len(clusters)} clusters from {len(sample_signals)} signals")
    
    for i, cluster in enumerate(clusters):
        print(f"Cluster {i+1}:")
        print(f"  - Signals: {cluster.signal_count}")
        print(f"  - Themes: {cluster.dominant_themes[:3]}")
        print(f"  - Pain intensity: {cluster.pain_intensity:.1f}")
        print(f"  - Market potential: {cluster.market_potential:.1f}")
        print(f"  - AI opportunity score: {cluster.ai_opportunity_score:.1f}")
        print(f"  - Confidence: {cluster.confidence_level:.2f}")
    
    assert len(clusters) > 0, "Should create at least one cluster"
    print("✓ Signal clustering test passed")


async def test_opportunity_candidate_generation():
    """Test opportunity candidate generation."""
    print("\nTesting opportunity candidate generation...")
    
    engine = OpportunityEngine()
    
    # Create a sample cluster
    sample_cluster = SignalCluster(
        cluster_id="test_cluster_1",
        signals=[
            {
                "signal_id": "s1",
                "content": "Manual data processing is time consuming and error prone",
                "signal_type": "pain_point"
            },
            {
                "signal_id": "s2", 
                "content": "Need ML automation for document classification",
                "signal_type": "feature_request"
            }
        ],
        dominant_themes=["automation", "data", "processing", "machine", "learning"],
        pain_intensity=75.0,
        market_potential=80.0,
        ai_opportunity_score=85.0,
        signal_count=2,
        total_engagement=70,
        avg_sentiment=-0.3,
        confidence_level=0.8
    )
    
    candidate = await engine._generate_opportunity_candidate(sample_cluster)
    
    assert candidate is not None, "Should generate opportunity candidate"
    
    print(f"Generated opportunity candidate:")
    print(f"  - Title: {candidate.title}")
    print(f"  - Description: {candidate.description[:100]}...")
    print(f"  - AI Solution Types: {candidate.ai_solution_types}")
    print(f"  - Target Industries: {candidate.target_industries}")
    print(f"  - Confidence Score: {candidate.confidence_score:.2f}")
    print(f"  - Market Validation Score: {candidate.market_validation_score:.1f}")
    print(f"  - AI Feasibility Score: {candidate.ai_feasibility_score:.1f}")
    
    assert len(candidate.title) > 0, "Candidate should have title"
    assert len(candidate.description) > 0, "Candidate should have description"
    assert 0 <= candidate.confidence_score <= 1, "Confidence score should be 0-1"
    
    print("✓ Opportunity candidate generation test passed")


async def test_ai_solution_classification():
    """Test AI solution type classification."""
    print("\nTesting AI solution type classification...")
    
    engine = OpportunityEngine()
    
    # Test cluster with ML content
    ml_cluster = SignalCluster(
        cluster_id="ml_test",
        signals=[
            {"content": "Need machine learning for predictive analytics"},
            {"content": "Classification algorithm for document processing"},
            {"content": "ML model for recommendation system"}
        ],
        dominant_themes=["machine", "learning", "prediction"],
        pain_intensity=60.0,
        market_potential=70.0,
        ai_opportunity_score=80.0,
        signal_count=3,
        total_engagement=50,
        avg_sentiment=0.1,
        confidence_level=0.7
    )
    
    ai_types = await engine._classify_ai_solution_types(ml_cluster)
    print(f"Detected AI solution types: {ai_types}")
    
    assert len(ai_types) > 0, "Should detect at least one AI solution type"
    assert "machine_learning" in ai_types, "Should detect machine learning"
    
    print("✓ AI solution classification test passed")


async def test_text_normalization():
    """Test text normalization for deduplication."""
    print("\nTesting text normalization...")
    
    engine = OpportunityEngine()
    
    text1 = "AI-Powered Solution for Data Processing!"
    text2 = "ai powered solution for data processing"
    text3 = "  AI   Powered   Solution   for   Data   Processing  "
    
    norm1 = engine._normalize_text(text1)
    norm2 = engine._normalize_text(text2)
    norm3 = engine._normalize_text(text3)
    
    print(f"Original texts:")
    print(f"  1: '{text1}'")
    print(f"  2: '{text2}'")
    print(f"  3: '{text3}'")
    print(f"Normalized: '{norm1}'")
    
    print(f"Normalized results: '{norm1}', '{norm2}', '{norm3}'")
    # The normalization should make similar texts more comparable
    # Text 2 and 3 should be identical (no punctuation differences)
    assert norm2 == norm3, "Texts without punctuation should normalize identically"
    # All should be lowercase and cleaned
    assert norm1.islower() and norm2.islower() and norm3.islower(), "Should be lowercase"
    
    print("✓ Text normalization test passed")


async def main():
    """Run all tests."""
    print("Running OpportunityEngine Core Tests")
    print("=" * 50)
    
    try:
        await test_signal_similarity()
        await test_signal_clustering()
        await test_opportunity_candidate_generation()
        await test_ai_solution_classification()
        await test_text_normalization()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed successfully!")
        print("OpportunityEngine core functionality is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)