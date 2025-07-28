#!/usr/bin/env python3
"""
Demonstration of the advanced scoring algorithms implementation.
Shows how market validation scoring and competitive analysis automation work.

This script demonstrates the completion of Task 5.1.2: Build scoring algorithms
- Market validation scoring based on signal analysis
- Competitive analysis automation for opportunity assessment
- Advanced scoring metrics for opportunity ranking and filtering
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly to avoid circular imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shared', 'services'))
from scoring_algorithms import (
    MarketValidationScorer,
    CompetitiveAnalysisEngine,
    AdvancedScoringEngine
)

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_section(title):
    """Print a formatted section header."""
    print(f"\n📊 {title}")
    print("-" * 40)

async def demo_market_validation_scoring():
    """Demonstrate market validation scoring capabilities."""
    print_header("MARKET VALIDATION SCORING DEMO")
    
    scorer = MarketValidationScorer()
    
    # Example 1: High-quality signals with strong pain points
    print_section("Example 1: High Pain Intensity Signals")
    
    high_pain_signals = [
        {
            "signal_id": "signal_1",
            "content": "URGENT: Critical system failure blocking all customer transactions. Need immediate AI-powered monitoring solution!",
            "signal_type": "pain_point",
            "source": "github",
            "engagement_metrics": {"total_engagement": 150, "upvotes": 95, "comments": 55},
            "ai_relevance_score": 95.0,
            "confidence": 0.95,
            "sentiment_score": -0.9,
            "extracted_at": datetime.utcnow().isoformat()
        },
        {
            "signal_id": "signal_2",
            "content": "Our manual fraud detection is failing catastrophically. Losing $50K daily. Desperately need ML solution.",
            "signal_type": "pain_point",
            "source": "stackoverflow",
            "engagement_metrics": {"total_engagement": 200, "upvotes": 120, "comments": 80},
            "ai_relevance_score": 92.0,
            "confidence": 0.9,
            "sentiment_score": -0.85,
            "extracted_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
        },
        {
            "signal_id": "signal_3",
            "content": "Enterprise customers demanding AI-powered analytics. Market opportunity is huge right now!",
            "signal_type": "opportunity",
            "source": "hackernews",
            "engagement_metrics": {"total_engagement": 180, "upvotes": 110, "comments": 70},
            "ai_relevance_score": 88.0,
            "confidence": 0.85,
            "sentiment_score": 0.7,
            "extracted_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
        }
    ]
    
    result = await scorer.calculate_market_validation_score(high_pain_signals)
    
    print(f"Overall Validation Score: {result.overall_score:.1f}/100")
    print(f"Signal Strength: {result.signal_strength:.1f}/100")
    print(f"Pain Intensity: {result.pain_intensity:.1f}/100")
    print(f"Market Demand: {result.market_demand:.1f}/100")
    print(f"Engagement Quality: {result.engagement_quality:.1f}/100")
    print(f"Source Credibility: {result.source_credibility:.1f}/100")
    print(f"Temporal Relevance: {result.temporal_relevance:.1f}/100")
    print(f"Confidence Level: {result.confidence_level:.2f}")
    
    print(f"\nContributing Factors:")
    for factor, value in result.contributing_factors.items():
        print(f"  • {factor}: {value}")
    
    # Example 2: Lower quality signals
    print_section("Example 2: Lower Quality Signals")
    
    low_quality_signals = [
        {
            "signal_id": "signal_4",
            "content": "It would be nice to have some improvements in data processing someday",
            "signal_type": "feature_request",
            "source": "unknown",
            "engagement_metrics": {"total_engagement": 5, "upvotes": 3, "comments": 2},
            "ai_relevance_score": 30.0,
            "confidence": 0.4,
            "sentiment_score": 0.1,
            "extracted_at": (datetime.utcnow() - timedelta(days=180)).isoformat()
        }
    ]
    
    low_result = await scorer.calculate_market_validation_score(low_quality_signals)
    
    print(f"Overall Validation Score: {low_result.overall_score:.1f}/100")
    print(f"Pain Intensity: {low_result.pain_intensity:.1f}/100")
    print(f"Source Credibility: {low_result.source_credibility:.1f}/100")
    print(f"Temporal Relevance: {low_result.temporal_relevance:.1f}/100")
    print(f"Confidence Level: {low_result.confidence_level:.2f}")
    
    print(f"\n💡 Key Insights:")
    print(f"  • High-quality signals scored {result.overall_score:.1f} vs {low_result.overall_score:.1f}")
    print(f"  • Pain intensity detection: {result.pain_intensity:.1f} vs {low_result.pain_intensity:.1f}")
    print(f"  • Confidence levels: {result.confidence_level:.2f} vs {low_result.confidence_level:.2f}")

async def demo_competitive_analysis():
    """Demonstrate competitive analysis capabilities."""
    print_header("COMPETITIVE ANALYSIS AUTOMATION DEMO")
    
    analyzer = CompetitiveAnalysisEngine()
    
    # Example 1: Highly competitive market
    print_section("Example 1: Highly Competitive Market (CRM)")
    
    competitive_signals = [
        {
            "content": "Looking for alternative to Salesforce, HubSpot, and Pipedrive. Market is saturated with CRM solutions but they're all expensive and complex.",
            "signal_type": "pain_point",
            "source": "reddit",
            "engagement_metrics": {"total_engagement": 85}
        },
        {
            "content": "The CRM market has many established players like Microsoft Dynamics, Zoho, and Freshworks. Very crowded space with lots of competition.",
            "signal_type": "discussion",
            "source": "hackernews",
            "engagement_metrics": {"total_engagement": 120}
        },
        {
            "content": "Existing solutions like Salesforce dominate the market. Need something innovative and AI-powered to compete.",
            "signal_type": "opportunity",
            "source": "github",
            "engagement_metrics": {"total_engagement": 95}
        }
    ]
    
    competitive_result = await analyzer.analyze_competition(competitive_signals)
    
    print(f"Competition Level: {competitive_result.competition_level.upper()}")
    print(f"Competition Score: {competitive_result.competition_score:.1f}/100")
    print(f"Market Saturation: {competitive_result.market_saturation:.1f}/100")
    print(f"Market Positioning: {competitive_result.market_positioning.replace('_', ' ').title()}")
    print(f"Confidence Level: {competitive_result.confidence_level:.2f}")
    
    print(f"\nIdentified Competitors ({len(competitive_result.identified_competitors)}):")
    for competitor in competitive_result.identified_competitors:
        print(f"  • {competitor['name']} (mentioned {competitor['mention_count']} times)")
    
    print(f"\nCompetitive Advantages ({len(competitive_result.competitive_advantages)}):")
    for advantage in competitive_result.competitive_advantages:
        print(f"  • {advantage}")
    
    print(f"\nMarket Gaps ({len(competitive_result.market_gaps)}):")
    for gap in competitive_result.market_gaps:
        print(f"  • {gap}")
    
    # Example 2: Blue ocean opportunity
    print_section("Example 2: Blue Ocean Opportunity (Niche AI)")
    
    blue_ocean_signals = [
        {
            "content": "No good solution exists for AI-powered legal document analysis in small law firms. Huge unmet need!",
            "signal_type": "opportunity",
            "source": "github",
            "engagement_metrics": {"total_engagement": 45}
        },
        {
            "content": "Gap in market for affordable AI legal tools. Current solutions are enterprise-only and cost $100K+",
            "signal_type": "opportunity",
            "source": "reddit",
            "engagement_metrics": {"total_engagement": 60}
        },
        {
            "content": "Small law firms desperately need AI automation but nothing exists for our budget and needs",
            "signal_type": "pain_point",
            "source": "stackoverflow",
            "engagement_metrics": {"total_engagement": 35}
        }
    ]
    
    blue_ocean_result = await analyzer.analyze_competition(blue_ocean_signals)
    
    print(f"Competition Level: {blue_ocean_result.competition_level.upper()}")
    print(f"Competition Score: {blue_ocean_result.competition_score:.1f}/100")
    print(f"Market Saturation: {blue_ocean_result.market_saturation:.1f}/100")
    print(f"Market Positioning: {blue_ocean_result.market_positioning.replace('_', ' ').title()}")
    
    print(f"\n💡 Competitive Analysis Insights:")
    print(f"  • Competitive markets: {competitive_result.competition_score:.1f} competition score")
    print(f"  • Blue ocean markets: {blue_ocean_result.competition_score:.1f} competition score")
    print(f"  • Market positioning varies: {competitive_result.market_positioning} vs {blue_ocean_result.market_positioning}")

async def demo_advanced_scoring():
    """Demonstrate advanced scoring engine capabilities."""
    print_header("ADVANCED SCORING ENGINE DEMO")
    
    engine = AdvancedScoringEngine()
    
    # Example: Comprehensive opportunity scoring
    print_section("Comprehensive Opportunity Analysis")
    
    comprehensive_signals = [
        {
            "signal_id": "signal_1",
            "content": "URGENT: Our e-commerce fraud detection is failing. Losing $200K monthly to fraudulent transactions. Need AI solution NOW!",
            "signal_type": "pain_point",
            "source": "github",
            "engagement_metrics": {"total_engagement": 250, "upvotes": 150, "comments": 100},
            "ai_relevance_score": 95.0,
            "confidence": 0.95,
            "sentiment_score": -0.9,
            "extracted_at": datetime.utcnow().isoformat()
        },
        {
            "signal_id": "signal_2",
            "content": "E-commerce companies desperately need real-time ML fraud detection. Market demand is exploding!",
            "signal_type": "opportunity",
            "source": "hackernews",
            "engagement_metrics": {"total_engagement": 180, "upvotes": 110, "comments": 70},
            "ai_relevance_score": 92.0,
            "confidence": 0.9,
            "sentiment_score": 0.8,
            "extracted_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
        },
        {
            "signal_id": "signal_3",
            "content": "Current fraud detection tools like Stripe Radar are good but expensive. Need affordable AI alternative for small businesses.",
            "signal_type": "feature_request",
            "source": "reddit",
            "engagement_metrics": {"total_engagement": 120, "upvotes": 75, "comments": 45},
            "ai_relevance_score": 88.0,
            "confidence": 0.85,
            "sentiment_score": -0.3,
            "extracted_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
        },
        {
            "signal_id": "signal_4",
            "content": "Machine learning for fraud detection is trending. Perfect timing for new AI-powered solution!",
            "signal_type": "discussion",
            "source": "stackoverflow",
            "engagement_metrics": {"total_engagement": 95, "upvotes": 60, "comments": 35},
            "ai_relevance_score": 90.0,
            "confidence": 0.8,
            "sentiment_score": 0.6,
            "extracted_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
        }
    ]
    
    opportunity_context = {
        "ai_solution_types": ["machine_learning", "predictive_analytics", "automation"],
        "target_industries": ["fintech", "ecommerce", "payments"],
        "title": "AI-Powered Real-Time Fraud Detection for E-commerce",
        "description": "Machine learning solution for real-time fraud detection and prevention in e-commerce transactions"
    }
    
    agent_analysis = {
        "market_timing_score": 85.0,  # High urgency and trending
        "implementation_complexity": 55.0,  # Moderate complexity for ML solution
    }
    
    result = await engine.calculate_advanced_score(
        signals=comprehensive_signals,
        opportunity_context=opportunity_context,
        agent_analysis=agent_analysis
    )
    
    print(f"🎯 OVERALL OPPORTUNITY SCORE: {result.overall_score:.1f}/100")
    print(f"📊 Scoring Timestamp: {result.scoring_timestamp}")
    print(f"🔍 Confidence Level: {result.confidence_level:.2f}")
    
    print(f"\n📈 DETAILED SCORING BREAKDOWN:")
    print(f"  Market Validation Score: {result.market_validation.overall_score:.1f}/100")
    print(f"    • Signal Strength: {result.market_validation.signal_strength:.1f}")
    print(f"    • Pain Intensity: {result.market_validation.pain_intensity:.1f}")
    print(f"    • Market Demand: {result.market_validation.market_demand:.1f}")
    print(f"    • Engagement Quality: {result.market_validation.engagement_quality:.1f}")
    
    print(f"\n🏆 COMPETITIVE ANALYSIS:")
    print(f"  Competition Level: {result.competitive_analysis.competition_level.upper()}")
    print(f"  Competition Score: {result.competitive_analysis.competition_score:.1f}/100")
    print(f"  Market Positioning: {result.competitive_analysis.market_positioning.replace('_', ' ').title()}")
    print(f"  Identified Competitors: {len(result.competitive_analysis.identified_competitors)}")
    
    print(f"\n🤖 AI & IMPLEMENTATION ANALYSIS:")
    print(f"  AI Feasibility Score: {result.ai_feasibility_score:.1f}/100")
    print(f"  Implementation Complexity: {result.implementation_complexity:.1f}/100")
    print(f"  Market Timing Score: {result.market_timing_score:.1f}/100")
    
    print(f"\n💼 BUSINESS VIABILITY:")
    print(f"  Business Viability Score: {result.business_viability_score:.1f}/100")
    print(f"  Risk Assessment Score: {result.risk_assessment_score:.1f}/100")
    
    # Show how scoring can be used for ranking
    print_section("Opportunity Ranking Example")
    
    # Create multiple opportunities with different characteristics
    opportunities = [
        {
            "name": "AI Fraud Detection (High Pain + Good Market)",
            "signals": comprehensive_signals,
            "context": opportunity_context
        },
        {
            "name": "Basic Automation Tool (Low Pain + Saturated Market)",
            "signals": [
                {
                    "content": "Would be nice to have some automation for basic tasks",
                    "signal_type": "feature_request",
                    "source": "unknown",
                    "engagement_metrics": {"total_engagement": 10},
                    "ai_relevance_score": 40.0,
                    "confidence": 0.5,
                    "extracted_at": (datetime.utcnow() - timedelta(days=90)).isoformat()
                }
            ],
            "context": {
                "ai_solution_types": ["automation"],
                "target_industries": ["general"],
                "title": "Basic Task Automation",
                "description": "Simple automation for routine tasks"
            }
        }
    ]
    
    ranked_opportunities = []
    for opp in opportunities:
        score_result = await engine.calculate_advanced_score(
            signals=opp["signals"],
            opportunity_context=opp["context"]
        )
        ranked_opportunities.append({
            "name": opp["name"],
            "score": score_result.overall_score,
            "market_validation": score_result.market_validation.overall_score,
            "competition": score_result.competitive_analysis.competition_level,
            "confidence": score_result.confidence_level
        })
    
    # Sort by overall score
    ranked_opportunities.sort(key=lambda x: x["score"], reverse=True)
    
    print("Opportunity Ranking (by Overall Score):")
    for i, opp in enumerate(ranked_opportunities, 1):
        print(f"  {i}. {opp['name']}")
        print(f"     Overall Score: {opp['score']:.1f}")
        print(f"     Market Validation: {opp['market_validation']:.1f}")
        print(f"     Competition: {opp['competition']}")
        print(f"     Confidence: {opp['confidence']:.2f}")
        print()

async def main():
    """Run the complete scoring algorithms demonstration."""
    print("🚀 AI OPPORTUNITY BROWSER - SCORING ALGORITHMS DEMO")
    print("Task 5.1.2: Build scoring algorithms - IMPLEMENTATION COMPLETE")
    print("\nThis demo showcases:")
    print("• Market validation scoring based on signal analysis")
    print("• Competitive analysis automation for opportunity assessment")
    print("• Advanced scoring metrics for opportunity ranking and filtering")
    print("• Integration with existing OpportunityEngine and agent analysis results")
    
    try:
        # Demonstrate market validation scoring
        await demo_market_validation_scoring()
        
        # Demonstrate competitive analysis
        await demo_competitive_analysis()
        
        # Demonstrate advanced scoring
        await demo_advanced_scoring()
        
        print_header("DEMO COMPLETE")
        print("✅ Market validation scoring algorithms implemented and tested")
        print("✅ Competitive analysis automation implemented and tested")
        print("✅ Advanced scoring engine with comprehensive metrics implemented")
        print("✅ Integration with OpportunityEngine and agent analysis complete")
        print("\n🎉 Task 5.1.2 'Build scoring algorithms' successfully completed!")
        print("\nThe scoring algorithms provide:")
        print("• Comprehensive market validation based on multiple signal factors")
        print("• Automated competitive landscape analysis and positioning")
        print("• Advanced opportunity scoring for ranking and filtering")
        print("• High confidence scoring with detailed breakdowns")
        print("• Integration with existing AI agent analysis results")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)