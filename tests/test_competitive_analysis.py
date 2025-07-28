"""
Test suite for competitive analysis functionality in BusinessIntelligenceService.

Tests the Phase 7.1.3 implementation of competitive intelligence features.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any

from shared.services.business_intelligence_service import (
    BusinessIntelligenceService,
    CompetitiveIntelligence
)
from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.market_signal import MarketSignal, SignalType
from shared.models.user import User


@pytest.fixture
def business_intelligence_service():
    """Create BusinessIntelligenceService instance."""
    return BusinessIntelligenceService()


@pytest.fixture
def mock_opportunity():
    """Create mock opportunity for testing."""
    opportunity = MagicMock(spec=Opportunity)
    opportunity.id = "test-opportunity-123"
    opportunity.title = "AI Document Processing Solution"
    opportunity.description = "Innovative AI-powered document processing platform using advanced NLP and computer vision"
    opportunity.ai_solution_types = json.dumps(["nlp", "computer_vision", "machine_learning"])
    opportunity.target_industries = json.dumps(["finance", "healthcare", "legal"])
    opportunity.required_capabilities = json.dumps(["transformer", "deep_learning", "neural_networks", "api_integration"])
    opportunity.status = OpportunityStatus.VALIDATED
    return opportunity


@pytest.fixture
def mock_market_signals():
    """Create mock market signals for testing."""
    signals = []
    
    # Signal mentioning competitors
    signal1 = MagicMock(spec=MarketSignal)
    signal1.content = "OpenAI has launched a new NLP platform that competes with traditional document processing solutions"
    signal1.engagement_score = 0.8
    signal1.keywords = json.dumps(["openai", "nlp", "document processing", "ai platform"])
    signal1.created_at = datetime.utcnow() - timedelta(days=5)
    signals.append(signal1)
    
    # Signal mentioning another competitor
    signal2 = MagicMock(spec=MarketSignal)
    signal2.content = "Anthropic company released Claude for document analysis, competing with existing AI solutions"
    signal2.engagement_score = 0.7
    signal2.keywords = json.dumps(["anthropic", "claude", "document analysis", "ai competition"])
    signal2.created_at = datetime.utcnow() - timedelta(days=10)
    signals.append(signal2)
    
    # Signal about market demand
    signal3 = MagicMock(spec=MarketSignal)
    signal3.content = "Growing demand for automated document processing in finance industry. Companies need better AI tools."
    signal3.engagement_score = 0.6
    signal3.keywords = json.dumps(["document processing", "finance", "automation", "ai tools"])
    signal3.created_at = datetime.utcnow() - timedelta(days=15)
    signals.append(signal3)
    
    # Signal about technology trends
    signal4 = MagicMock(spec=MarketSignal)
    signal4.content = "DataRobot and H2O.ai are expanding their machine learning platforms to include document AI"
    signal4.engagement_score = 0.9
    signal4.keywords = json.dumps(["datarobot", "h2o.ai", "machine learning", "document ai"])
    signal4.created_at = datetime.utcnow() - timedelta(days=20)
    signals.append(signal4)
    
    # Signal about regulatory requirements
    signal5 = MagicMock(spec=MarketSignal)
    signal5.content = "New compliance regulations require financial institutions to improve document processing accuracy"
    signal5.engagement_score = 0.5
    signal5.keywords = json.dumps(["compliance", "regulations", "financial", "document processing"])
    signal5.created_at = datetime.utcnow() - timedelta(days=25)
    signals.append(signal5)
    
    return signals


@pytest.mark.asyncio
class TestCompetitiveAnalysis:
    """Test competitive analysis functionality."""
    
    async def test_identify_competitors_from_signals(self, business_intelligence_service, mock_opportunity, mock_market_signals):
        """Test competitor identification from market signals."""
        mock_db = AsyncMock()
        
        competitors = await business_intelligence_service._identify_competitors(
            mock_db, mock_opportunity, mock_market_signals
        )
        
        # Verify competitors were identified
        assert len(competitors) > 0
        
        # Check that known AI companies were identified
        competitor_names = [c['name'] for c in competitors]
        assert 'OpenAI' in competitor_names
        assert 'Anthropic' in competitor_names
        assert 'DataRobot' in competitor_names
        
        # Verify competitor structure
        for competitor in competitors:
            assert 'name' in competitor
            assert 'mentions' in competitor
            assert 'estimated_market_share' in competitor
            assert 'strength' in competitor
            assert 'position' in competitor
            assert 'threat_level' in competitor
            
            # Verify data types and ranges
            assert isinstance(competitor['mentions'], int)
            assert 0 <= competitor['estimated_market_share'] <= 1
            assert competitor['strength'] in ['low', 'medium', 'high']
            assert competitor['position'] in ['emerging', 'established']
            assert competitor['threat_level'] in ['low', 'medium', 'high']
    
    async def test_analyze_competitive_positioning(self, business_intelligence_service, mock_opportunity):
        """Test competitive positioning analysis."""
        competitors = [
            {'name': 'OpenAI', 'strength': 'high', 'estimated_market_share': 0.20},
            {'name': 'Anthropic', 'strength': 'high', 'estimated_market_share': 0.15},
            {'name': 'DataRobot', 'strength': 'medium', 'estimated_market_share': 0.10},
            {'name': 'Startup AI', 'strength': 'low', 'estimated_market_share': 0.03}
        ]
        
        positioning = await business_intelligence_service._analyze_competitive_positioning(
            mock_opportunity, competitors
        )
        
        # Verify positioning analysis structure
        assert 'competitive_intensity' in positioning
        assert 'recommended_position' in positioning
        assert 'positioning_strategy' in positioning
        assert 'unique_value_propositions' in positioning
        assert 'barriers_to_entry' in positioning
        assert 'competitive_advantages' in positioning
        assert 'market_entry_difficulty' in positioning
        
        # Verify competitive intensity assessment
        assert positioning['competitive_intensity'] in ['low', 'medium', 'high', 'very_high']
        
        # Verify positioning strategy is appropriate
        assert positioning['recommended_position'] in ['niche_differentiation', 'cost_leadership', 'innovation_leader']
        
        # With multiple high-strength competitors, should recommend niche differentiation
        assert positioning['recommended_position'] == 'niche_differentiation'
        assert positioning['competitive_intensity'] == 'medium'  # 4 competitors = medium intensity
    
    async def test_analyze_market_share(self, business_intelligence_service):
        """Test market share analysis."""
        competitors = [
            {'name': 'Leader Corp', 'estimated_market_share': 0.25},
            {'name': 'Challenger Inc', 'estimated_market_share': 0.15},
            {'name': 'Follower Ltd', 'estimated_market_share': 0.08},
            {'name': 'Niche Player', 'estimated_market_share': 0.03}
        ]
        
        market_share = await business_intelligence_service._analyze_market_share(
            competitors, []
        )
        
        # Verify market share categories
        expected_positions = ['leader', 'challenger', 'follower', 'niche']
        for position in expected_positions:
            assert position in market_share
            assert isinstance(market_share[position], float)
            assert 0 <= market_share[position] <= 1
        
        # Verify total market share is reasonable
        total_share = sum(market_share.values())
        assert 0.8 <= total_share <= 1.2  # Allow some variance
    
    async def test_identify_competitive_advantages(self, business_intelligence_service, mock_opportunity):
        """Test competitive advantage identification."""
        competitors = [
            {'name': 'GenericAI', 'strength': 'medium'},
            {'name': 'BasicML', 'strength': 'low'}
        ]
        
        advantages = await business_intelligence_service._identify_competitive_advantages(
            mock_opportunity, competitors
        )
        
        # Verify advantages were identified
        assert len(advantages) > 0
        assert len(advantages) <= 5  # Should return top 5
        
        # Should identify technology advantages from opportunity capabilities
        advantage_text = ' '.join(advantages).lower()
        assert any(tech in advantage_text for tech in ['transformer', 'deep learning', 'neural'])
        
        # Should identify early market advantage (few competitors)
        assert any('early market' in adv.lower() for adv in advantages)
        
        # Should identify multi-AI capabilities
        assert any('multi' in adv.lower() for adv in advantages)
    
    async def test_analyze_competitive_threats(self, business_intelligence_service, mock_opportunity):
        """Test competitive threat analysis."""
        competitors = [
            {'name': 'OpenAI', 'strength': 'high'},
            {'name': 'Google AI', 'strength': 'high'},
            {'name': 'Startup AI', 'strength': 'low'}
        ]
        
        threats = await business_intelligence_service._analyze_competitive_threats(
            mock_opportunity, competitors
        )
        
        # Verify threats were identified
        assert len(threats) > 0
        
        # Verify threat structure
        for threat in threats:
            assert 'threat' in threat
            assert 'type' in threat
            assert 'probability' in threat
            assert 'impact' in threat
            assert 'timeline' in threat
            assert 'mitigation' in threat
            
            # Verify valid values
            assert threat['probability'] in ['low', 'medium', 'high']
            assert threat['impact'] in ['low', 'medium', 'high', 'very_high']
            assert threat['type'] in ['direct_competition', 'technology_disruption', 'market_saturation', 'big_tech_entry', 'regulatory']
        
        # Should identify direct competition threats from high-strength competitors
        direct_threats = [t for t in threats if t['type'] == 'direct_competition']
        assert len(direct_threats) > 0
        
        # Should identify big tech entry threat
        big_tech_threats = [t for t in threats if t['type'] == 'big_tech_entry']
        assert len(big_tech_threats) > 0
        
        # Should identify regulatory threats for finance/healthcare industries
        regulatory_threats = [t for t in threats if t['type'] == 'regulatory']
        assert len(regulatory_threats) > 0
    
    async def test_generate_strategic_recommendations(self, business_intelligence_service, mock_opportunity):
        """Test strategic recommendation generation."""
        competitors = [
            {'name': 'OpenAI', 'strength': 'high'},
            {'name': 'Anthropic', 'strength': 'high'},
            {'name': 'DataRobot', 'strength': 'medium'}
        ]
        
        positioning = {
            'recommended_position': 'niche_differentiation',
            'competitive_intensity': 'high'
        }
        
        recommendations = await business_intelligence_service._generate_strategic_recommendations(
            mock_opportunity, competitors, positioning
        )
        
        # Verify recommendations were generated
        assert len(recommendations) > 0
        assert len(recommendations) <= 8  # Should return top 8
        
        # With high competition, should recommend niche focus
        recommendation_text = ' '.join(recommendations).lower()
        assert any('niche' in rec.lower() for rec in recommendations)
        
        # Should include technology-specific recommendations
        assert any('nlp' in rec.lower() or 'language' in rec.lower() for rec in recommendations)
        
        # Should include general strategic recommendations
        assert any('partnership' in rec.lower() for rec in recommendations)
        assert any('r&d' in rec.lower() or 'research' in rec.lower() for rec in recommendations)
    
    async def test_identify_market_gaps(self, business_intelligence_service, mock_opportunity, mock_market_signals):
        """Test market gap identification."""
        competitors = [
            {'name': 'EnterpriseAI', 'strength': 'high'},
            {'name': 'VisionTech', 'strength': 'medium'},
            {'name': 'DataCorp', 'strength': 'medium'}
        ]
        
        gaps = await business_intelligence_service._identify_market_gaps(
            mock_opportunity, competitors, mock_market_signals
        )
        
        # Verify gaps were identified
        assert len(gaps) > 0
        assert len(gaps) <= 6  # Should return top 6
        
        # Verify gap structure
        for gap in gaps:
            assert 'gap' in gap
            assert 'description' in gap
            assert 'size' in gap
            assert 'difficulty' in gap
            assert 'opportunity_type' in gap
            
            # Verify valid values
            assert gap['size'] in ['small', 'medium', 'large', 'very_large']
            assert gap['difficulty'] in ['low', 'medium', 'high', 'very_high']
            assert gap['opportunity_type'] in ['industry_vertical', 'technology_gap', 'market_segment', 'geographic', 'user_experience']
        
        # Should identify industry-specific gaps
        industry_gaps = [g for g in gaps if g['opportunity_type'] == 'industry_vertical']
        assert len(industry_gaps) > 0
        
        # Should identify SME market gap
        sme_gaps = [g for g in gaps if 'sme' in g['gap'].lower() or 'small' in g['gap'].lower()]
        assert len(sme_gaps) > 0
        
        # Should identify international market gap
        international_gaps = [g for g in gaps if 'international' in g['gap'].lower()]
        assert len(international_gaps) > 0
    
    async def test_identify_differentiation_opportunities(self, business_intelligence_service, mock_opportunity):
        """Test differentiation opportunity identification."""
        competitors = [
            {'name': 'TechAI', 'strength': 'high'},
            {'name': 'DataML', 'strength': 'medium'},
            {'name': 'VisionCorp', 'strength': 'medium'},
            {'name': 'NLPTech', 'strength': 'low'}
        ]
        
        opportunities = await business_intelligence_service._identify_differentiation_opportunities(
            mock_opportunity, competitors
        )
        
        # Verify opportunities were identified
        assert len(opportunities) > 0
        assert len(opportunities) <= 8  # Should return top 8
        
        # Should identify multi-modal AI differentiation
        multimodal_opps = [o for o in opportunities if 'multi-modal' in o.lower() or 'integrated' in o.lower()]
        assert len(multimodal_opps) > 0
        
        # Should identify industry-specific differentiation
        industry_opps = [o for o in opportunities if any(ind in o.lower() for ind in ['finance', 'healthcare', 'legal'])]
        assert len(industry_opps) > 0
        
        # Should identify UX differentiation for crowded market
        ux_opps = [o for o in opportunities if 'no-code' in o.lower() or 'drag-and-drop' in o.lower()]
        assert len(ux_opps) > 0
        
        # Should identify business model differentiation
        business_opps = [o for o in opportunities if 'pricing' in o.lower() or 'service' in o.lower()]
        assert len(business_opps) > 0
    
    async def test_generate_competitive_intelligence_full(self, business_intelligence_service, mock_opportunity, mock_market_signals):
        """Test complete competitive intelligence generation."""
        mock_db = AsyncMock()
        
        competitive_intelligence = await business_intelligence_service.generate_competitive_intelligence(
            mock_db, mock_opportunity, mock_market_signals
        )
        
        # Verify the competitive intelligence object
        assert isinstance(competitive_intelligence, CompetitiveIntelligence)
        assert competitive_intelligence.analysis_id.startswith('competitive_')
        assert competitive_intelligence.market_segment == "AI-powered business solutions"
        
        # Verify all components are present
        assert len(competitive_intelligence.competitors) > 0
        assert isinstance(competitive_intelligence.competitive_positioning, dict)
        assert isinstance(competitive_intelligence.market_share_analysis, dict)
        assert len(competitive_intelligence.competitive_advantages) > 0
        assert len(competitive_intelligence.threats_analysis) > 0
        assert len(competitive_intelligence.strategic_recommendations) > 0
        assert len(competitive_intelligence.market_gaps) > 0
        assert len(competitive_intelligence.differentiation_opportunities) > 0
        
        # Verify data quality
        assert all(isinstance(comp, dict) for comp in competitive_intelligence.competitors)
        assert all(isinstance(adv, str) for adv in competitive_intelligence.competitive_advantages)
        assert all(isinstance(rec, str) for rec in competitive_intelligence.strategic_recommendations)
        assert all(isinstance(diff, str) for diff in competitive_intelligence.differentiation_opportunities)


@pytest.mark.asyncio
class TestCompetitiveAnalysisEdgeCases:
    """Test edge cases for competitive analysis."""
    
    async def test_no_competitors_scenario(self, business_intelligence_service):
        """Test competitive analysis with no identified competitors."""
        mock_opportunity = MagicMock(spec=Opportunity)
        mock_opportunity.ai_solution_types = json.dumps(["custom_ai"])
        mock_opportunity.target_industries = json.dumps(["niche_industry"])
        mock_opportunity.description = "Unique AI solution"
        
        empty_signals = []
        mock_db = AsyncMock()
        
        competitors = await business_intelligence_service._identify_competitors(
            mock_db, mock_opportunity, empty_signals
        )
        
        # Should still provide analysis even with no competitors
        market_share = await business_intelligence_service._analyze_market_share(competitors, empty_signals)
        assert 'new_market' in market_share or 'unaddressed_market' in market_share
        
        positioning = await business_intelligence_service._analyze_competitive_positioning(
            mock_opportunity, competitors
        )
        assert positioning['competitive_intensity'] == 'low'
        assert positioning['recommended_position'] == 'innovation_leader'
    
    async def test_high_competition_scenario(self, business_intelligence_service, mock_opportunity):
        """Test competitive analysis with many strong competitors."""
        many_competitors = [
            {'name': f'Competitor{i}', 'strength': 'high', 'estimated_market_share': 0.08}
            for i in range(10)
        ]
        
        positioning = await business_intelligence_service._analyze_competitive_positioning(
            mock_opportunity, many_competitors
        )
        
        assert positioning['competitive_intensity'] == 'very_high'
        assert positioning['recommended_position'] == 'niche_differentiation'
        assert positioning['market_entry_difficulty'] == 'high'
        
        recommendations = await business_intelligence_service._generate_strategic_recommendations(
            mock_opportunity, many_competitors, positioning
        )
        
        # Should focus on niche strategies
        recommendation_text = ' '.join(recommendations).lower()
        assert 'niche' in recommendation_text
        assert 'partnership' in recommendation_text
    
    async def test_malformed_opportunity_data(self, business_intelligence_service):
        """Test handling of malformed opportunity data."""
        mock_opportunity = MagicMock(spec=Opportunity)
        mock_opportunity.ai_solution_types = "invalid_json"
        mock_opportunity.target_industries = None
        mock_opportunity.required_capabilities = "also_invalid"
        mock_opportunity.description = None
        
        mock_db = AsyncMock()
        
        # Should handle malformed data gracefully
        competitors = await business_intelligence_service._identify_competitors(
            mock_db, mock_opportunity, []
        )
        
        # Should return empty list or default competitors
        assert isinstance(competitors, list)
        
        advantages = await business_intelligence_service._identify_competitive_advantages(
            mock_opportunity, competitors
        )
        
        # Should provide default advantages
        assert len(advantages) > 0
        assert any('ai-native' in adv.lower() for adv in advantages)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])