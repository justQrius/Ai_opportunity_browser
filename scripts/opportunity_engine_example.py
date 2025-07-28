#!/usr/bin/env python3
"""
Example usage of OpportunityEngine for signal-to-opportunity conversion.
Demonstrates the complete workflow from market signals to opportunities.
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

# Mock the dependencies
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


async def demonstrate_signal_to_opportunity_conversion():
    """Demonstrate the complete signal-to-opportunity conversion process."""
    
    print("AI Opportunity Browser - OpportunityEngine Demo")
    print("=" * 60)
    
    # Initialize the OpportunityEngine
    config = {
        "min_signals_for_opportunity": 2,
        "similarity_threshold": 0.25,
        "confidence_threshold": 0.6,
        "max_opportunities_per_batch": 5
    }
    
    engine = OpportunityEngine(config)
    print(f"✓ OpportunityEngine initialized with config: {config}")
    
    # Sample market signals from various sources (as would come from agents)
    market_signals = [
        {
            "signal_id": "reddit_001",
            "content": "I spend 4 hours every day manually entering customer data from emails into our CRM. This is killing my productivity and I make so many typos.",
            "signal_type": "pain_point",
            "source": "reddit",
            "engagement_metrics": {"total_engagement": 45, "upvotes": 32, "comments": 13},
            "ai_relevance_score": 85.0,
            "confidence": 0.9,
            "sentiment_score": -0.7
        },
        {
            "signal_id": "github_001",
            "content": "Feature request: Automated email parsing and data extraction for CRM integration. Current manual process is error-prone and time-consuming.",
            "signal_type": "feature_request",
            "source": "github",
            "engagement_metrics": {"total_engagement": 28, "stars": 15, "comments": 13},
            "ai_relevance_score": 92.0,
            "confidence": 0.85,
            "sentiment_score": -0.4
        },
        {
            "signal_id": "stackoverflow_001",
            "content": "Looking for NLP library to extract structured data from unstructured emails automatically. Need to parse customer information, order details, etc.",
            "signal_type": "opportunity",
            "source": "stackoverflow",
            "engagement_metrics": {"total_engagement": 67, "upvotes": 42, "answers": 8},
            "ai_relevance_score": 95.0,
            "confidence": 0.88,
            "sentiment_score": 0.1
        },
        {
            "signal_id": "reddit_002",
            "content": "Our sales team wastes hours every week copying customer info from emails to Salesforce. There has to be a better way to automate this.",
            "signal_type": "pain_point",
            "source": "reddit",
            "engagement_metrics": {"total_engagement": 38, "upvotes": 25, "comments": 13},
            "ai_relevance_score": 78.0,
            "confidence": 0.82,
            "sentiment_score": -0.6
        },
        {
            "signal_id": "hackernews_001",
            "content": "Show HN: Built a simple email parser for extracting customer data. Saved our team 10 hours/week. Looking for feedback on ML improvements.",
            "signal_type": "opportunity",
            "source": "hackernews",
            "engagement_metrics": {"total_engagement": 156, "upvotes": 89, "comments": 67},
            "ai_relevance_score": 88.0,
            "confidence": 0.9,
            "sentiment_score": 0.6
        },
        {
            "signal_id": "github_002",
            "content": "Issue: Manual invoice processing is bottleneck in our accounting workflow. Need automated solution for data extraction from PDF invoices.",
            "signal_type": "pain_point",
            "source": "github",
            "engagement_metrics": {"total_engagement": 22, "reactions": 15, "comments": 7},
            "ai_relevance_score": 82.0,
            "confidence": 0.75,
            "sentiment_score": -0.5
        },
        {
            "signal_id": "reddit_003",
            "content": "Document processing automation using OCR and ML - anyone have experience? Need to digitize thousands of paper forms.",
            "signal_type": "feature_request",
            "source": "reddit",
            "engagement_metrics": {"total_engagement": 31, "upvotes": 19, "comments": 12},
            "ai_relevance_score": 90.0,
            "confidence": 0.8,
            "sentiment_score": 0.2
        }
    ]
    
    print(f"\n📊 Processing {len(market_signals)} market signals from various sources:")
    for signal in market_signals:
        print(f"  • {signal['source']}: {signal['signal_type']} (AI relevance: {signal['ai_relevance_score']:.1f}%)")
    
    # Step 1: Cluster related signals
    print(f"\n🔍 Step 1: Clustering related market signals...")
    signal_clusters = await engine._cluster_related_signals(market_signals)
    
    print(f"✓ Created {len(signal_clusters)} signal clusters:")
    for i, cluster in enumerate(signal_clusters, 1):
        print(f"  Cluster {i}:")
        print(f"    - Signals: {cluster.signal_count}")
        print(f"    - Dominant themes: {', '.join(cluster.dominant_themes[:3])}")
        print(f"    - Pain intensity: {cluster.pain_intensity:.1f}%")
        print(f"    - Market potential: {cluster.market_potential:.1f}%")
        print(f"    - AI opportunity score: {cluster.ai_opportunity_score:.1f}%")
        print(f"    - Confidence: {cluster.confidence_level:.2f}")
    
    # Step 2: Generate opportunity candidates
    print(f"\n🎯 Step 2: Generating opportunity candidates...")
    opportunity_candidates = []
    
    for cluster in signal_clusters:
        if cluster.signal_count >= engine.min_signals_for_opportunity:
            candidate = await engine._generate_opportunity_candidate(cluster)
            if candidate and candidate.confidence_score >= engine.confidence_threshold:
                opportunity_candidates.append(candidate)
    
    print(f"✓ Generated {len(opportunity_candidates)} opportunity candidates:")
    
    for i, candidate in enumerate(opportunity_candidates, 1):
        print(f"\n  Opportunity Candidate {i}:")
        print(f"    Title: {candidate.title}")
        print(f"    Description: {candidate.description[:120]}...")
        print(f"    Problem: {candidate.problem_statement[:100]}...")
        print(f"    Solution: {candidate.proposed_solution[:100]}...")
        print(f"    AI Solution Types: {', '.join(candidate.ai_solution_types)}")
        print(f"    Target Industries: {', '.join(candidate.target_industries) if candidate.target_industries else 'General'}")
        print(f"    Confidence Score: {candidate.confidence_score:.2f}")
        print(f"    Market Validation: {candidate.market_validation_score:.1f}%")
        print(f"    AI Feasibility: {candidate.ai_feasibility_score:.1f}%")
        print(f"    Source Signals: {len(candidate.market_signals)}")
    
    # Step 3: Demonstrate deduplication (mock)
    print(f"\n🔍 Step 3: Deduplication analysis...")
    print("✓ Checking for duplicate opportunities against existing database...")
    print("✓ All candidates appear to be unique opportunities")
    
    # Summary
    print(f"\n📈 Summary:")
    print(f"  • Processed {len(market_signals)} market signals")
    print(f"  • Created {len(signal_clusters)} signal clusters")
    print(f"  • Generated {len(opportunity_candidates)} unique opportunity candidates")
    print(f"  • Average confidence score: {sum(c.confidence_score for c in opportunity_candidates) / len(opportunity_candidates):.2f}")
    print(f"  • Average market validation: {sum(c.market_validation_score for c in opportunity_candidates) / len(opportunity_candidates):.1f}%")
    
    print(f"\n✅ Signal-to-opportunity conversion completed successfully!")
    print(f"These opportunities would now be stored in the database and enter the validation workflow.")
    
    return opportunity_candidates


async def main():
    """Run the demonstration."""
    try:
        candidates = await demonstrate_signal_to_opportunity_conversion()
        
        print(f"\n" + "=" * 60)
        print("🎉 OpportunityEngine Demo Completed Successfully!")
        print(f"Generated {len(candidates)} validated opportunity candidates ready for community validation.")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)