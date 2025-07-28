"""
Advanced Scoring Algorithms for the AI Opportunity Browser system.
Implements market validation scoring and competitive analysis automation.

This module implements:
- Market validation scoring algorithms based on signal analysis
- Competitive analysis automation for opportunity assessment
- Advanced scoring metrics for opportunity ranking and filtering
- Integration with existing OpportunityEngine and agent analysis results

Supports Requirements 5.1.2 (Build scoring algorithms) from the implementation plan.
Addresses Requirements 5.2, 6.2, 8.3 from the requirements document.
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import re
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from shared.models.opportunity import Opportunity, OpportunityStatus
from shared.models.market_signal import MarketSignal, SignalType
from shared.models.validation import ValidationResult
from shared.cache import cache_manager, CacheKeys

logger = logging.getLogger(__name__)


@dataclass
class MarketValidationScore:
    """Comprehensive market validation scoring result"""
    overall_score: float  # 0-100
    signal_strength: float  # 0-100
    pain_intensity: float  # 0-100
    market_demand: float  # 0-100
    engagement_quality: float  # 0-100
    source_credibility: float  # 0-100
    temporal_relevance: float  # 0-100
    confidence_level: float  # 0-1
    contributing_factors: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "signal_strength": self.signal_strength,
            "pain_intensity": self.pain_intensity,
            "market_demand": self.market_demand,
            "engagement_quality": self.engagement_quality,
            "source_credibility": self.source_credibility,
            "temporal_relevance": self.temporal_relevance,
            "confidence_level": self.confidence_level,
            "contributing_factors": self.contributing_factors
        }


@dataclass
class CompetitiveAnalysis:
    """Comprehensive competitive analysis result"""
    competition_level: str  # low, medium, high
    competition_score: float  # 0-100 (higher = more competition)
    identified_competitors: List[Dict[str, Any]]
    market_saturation: float  # 0-100
    competitive_advantages: List[str]
    market_gaps: List[str]
    differentiation_opportunities: List[str]
    competitive_threats: List[str]
    market_positioning: str  # blue_ocean, red_ocean, niche
    confidence_level: float  # 0-1    

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competition_level": self.competition_level,
            "competition_score": self.competition_score,
            "identified_competitors": self.identified_competitors,
            "market_saturation": self.market_saturation,
            "competitive_advantages": self.competitive_advantages,
            "market_gaps": self.market_gaps,
            "differentiation_opportunities": self.differentiation_opportunities,
            "competitive_threats": self.competitive_threats,
            "market_positioning": self.market_positioning,
            "confidence_level": self.confidence_level
        }


@dataclass
class AdvancedOpportunityScore:
    """Advanced opportunity scoring with detailed breakdown"""
    overall_score: float  # 0-100
    market_validation: MarketValidationScore
    competitive_analysis: CompetitiveAnalysis
    ai_feasibility_score: float  # 0-100
    implementation_complexity: float  # 0-100 (higher = more complex)
    market_timing_score: float  # 0-100
    business_viability_score: float  # 0-100
    risk_assessment_score: float  # 0-100 (higher = more risky)
    confidence_level: float  # 0-1
    scoring_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "market_validation": self.market_validation.to_dict(),
            "competitive_analysis": self.competitive_analysis.to_dict(),
            "ai_feasibility_score": self.ai_feasibility_score,
            "implementation_complexity": self.implementation_complexity,
            "market_timing_score": self.market_timing_score,
            "business_viability_score": self.business_viability_score,
            "risk_assessment_score": self.risk_assessment_score,
            "confidence_level": self.confidence_level,
            "scoring_timestamp": self.scoring_timestamp.isoformat()
        }


class MarketValidationScorer:
    """
    Advanced market validation scoring algorithms.
    Implements Requirement 5.2 (market validation signals and pain point intensity).
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Scoring weights for different validation factors
        self.validation_weights = self.config.get("validation_weights", {
            "signal_strength": 0.25,
            "pain_intensity": 0.20,
            "market_demand": 0.20,
            "engagement_quality": 0.15,
            "source_credibility": 0.10,
            "temporal_relevance": 0.10
        })
        
        # Source credibility ratings
        self.source_credibility_scores = self.config.get("source_credibility", {
            "github": 0.9,
            "stackoverflow": 0.85,
            "hackernews": 0.8,
            "reddit": 0.7,
            "twitter": 0.6,
            "linkedin": 0.75,
            "medium": 0.65,
            "unknown": 0.3
        })
        
        # Pain point indicators with intensity weights
        self.pain_indicators = {
            "critical": ["critical", "urgent", "blocking", "broken", "failing", "disaster"],
            "high": ["problem", "issue", "difficult", "hard", "struggle", "pain", "frustrating"],
            "medium": ["annoying", "inconvenient", "slow", "inefficient", "tedious"],
            "low": ["would be nice", "improvement", "enhancement", "optimization"]
        }
        
        logger.info("MarketValidationScorer initialized", config=self.config)
    
    async def calculate_market_validation_score(
        self, 
        signals: List[Dict[str, Any]],
        opportunity_context: Optional[Dict[str, Any]] = None
    ) -> MarketValidationScore:
        """
        Calculate comprehensive market validation score from signals.
        
        Args:
            signals: List of market signals
            opportunity_context: Additional context about the opportunity
            
        Returns:
            MarketValidationScore with detailed breakdown
        """
        if not signals:
            return MarketValidationScore(
                overall_score=0.0,
                signal_strength=0.0,
                pain_intensity=0.0,
                market_demand=0.0,
                engagement_quality=0.0,
                source_credibility=0.0,
                temporal_relevance=0.0,
                confidence_level=0.0,
                contributing_factors={}
            )
        
        # Calculate individual scoring components
        signal_strength = await self._calculate_signal_strength(signals)
        pain_intensity = await self._calculate_pain_intensity(signals)
        market_demand = await self._calculate_market_demand(signals)
        engagement_quality = await self._calculate_engagement_quality(signals)
        source_credibility = await self._calculate_source_credibility(signals)
        temporal_relevance = await self._calculate_temporal_relevance(signals)
        
        # Calculate weighted overall score
        overall_score = (
            signal_strength * self.validation_weights["signal_strength"] +
            pain_intensity * self.validation_weights["pain_intensity"] +
            market_demand * self.validation_weights["market_demand"] +
            engagement_quality * self.validation_weights["engagement_quality"] +
            source_credibility * self.validation_weights["source_credibility"] +
            temporal_relevance * self.validation_weights["temporal_relevance"]
        )
        
        # Calculate confidence level based on signal quality and quantity
        confidence_level = await self._calculate_validation_confidence(signals)
        
        # Contributing factors for transparency
        contributing_factors = {
            "signal_count": len(signals),
            "unique_sources": len(set(s.get("source", "unknown") for s in signals)),
            "avg_engagement": statistics.mean([
                s.get("engagement_metrics", {}).get("total_engagement", 0) for s in signals
            ]) if signals else 0,
            "recent_signals": len([
                s for s in signals 
                if self._is_recent_signal(s.get("extracted_at"))
            ])
        }
        
        return MarketValidationScore(
            overall_score=min(100.0, overall_score),
            signal_strength=signal_strength,
            pain_intensity=pain_intensity,
            market_demand=market_demand,
            engagement_quality=engagement_quality,
            source_credibility=source_credibility,
            temporal_relevance=temporal_relevance,
            confidence_level=confidence_level,
            contributing_factors=contributing_factors
        )
    
    async def _calculate_signal_strength(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate signal strength based on quantity and diversity."""
        if not signals:
            return 0.0
        
        # Base score from signal count (logarithmic scaling)
        signal_count_score = min(50.0, 10 * math.log10(len(signals) + 1))
        
        # Diversity bonus from different sources
        unique_sources = len(set(s.get("source", "unknown") for s in signals))
        diversity_bonus = min(25.0, unique_sources * 5)
        
        # Signal type diversity
        signal_types = set(s.get("signal_type", "unknown") for s in signals)
        type_diversity_bonus = min(25.0, len(signal_types) * 8)
        
        return min(100.0, signal_count_score + diversity_bonus + type_diversity_bonus)
    
    async def _calculate_pain_intensity(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate pain intensity from signal content analysis."""
        if not signals:
            return 0.0
        
        total_pain_score = 0.0
        pain_signal_count = 0
        
        for signal in signals:
            content = signal.get("content", "").lower()
            signal_pain_score = 0.0
            
            # Check for different levels of pain indicators
            for level, indicators in self.pain_indicators.items():
                indicator_count = sum(1 for indicator in indicators if indicator in content)
                
                if level == "critical":
                    signal_pain_score += indicator_count * 25
                elif level == "high":
                    signal_pain_score += indicator_count * 15
                elif level == "medium":
                    signal_pain_score += indicator_count * 8
                elif level == "low":
                    signal_pain_score += indicator_count * 3
            
            # Weight by engagement if available
            engagement = signal.get("engagement_metrics", {}).get("total_engagement", 1)
            weighted_pain_score = signal_pain_score * (1 + engagement / 100)
            
            total_pain_score += weighted_pain_score
            if signal_pain_score > 0:
                pain_signal_count += 1
        
        if pain_signal_count == 0:
            return 0.0
        
        # Normalize and apply pain signal ratio
        avg_pain_score = total_pain_score / len(signals)
        pain_ratio = pain_signal_count / len(signals)
        
        return min(100.0, avg_pain_score * pain_ratio)
    
    async def _calculate_market_demand(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate market demand indicators from signals."""
        if not signals:
            return 0.0
        
        demand_indicators = [
            "need", "want", "looking for", "searching", "require", "demand",
            "market for", "customers want", "users need", "business opportunity"
        ]
        
        total_demand_score = 0.0
        
        for signal in signals:
            content = signal.get("content", "").lower()
            demand_count = sum(1 for indicator in demand_indicators if indicator in content)
            
            # Weight by signal type (feature requests and opportunities indicate higher demand)
            signal_type = signal.get("signal_type", "unknown")
            type_multiplier = {
                "feature_request": 1.5,
                "opportunity": 1.3,
                "pain_point": 1.2,
                "complaint": 1.1,
                "discussion": 1.0
            }.get(signal_type, 1.0)
            
            # Weight by engagement
            engagement = signal.get("engagement_metrics", {}).get("total_engagement", 1)
            engagement_multiplier = 1 + (engagement / 50)
            
            signal_demand_score = demand_count * type_multiplier * engagement_multiplier
            total_demand_score += signal_demand_score
        
        # Normalize to 0-100 scale
        avg_demand_score = total_demand_score / len(signals)
        return min(100.0, avg_demand_score * 10)
    
    async def _calculate_engagement_quality(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate engagement quality score."""
        if not signals:
            return 0.0
        
        engagement_scores = []
        
        for signal in signals:
            engagement_metrics = signal.get("engagement_metrics", {})
            total_engagement = engagement_metrics.get("total_engagement", 0)
            
            # Different engagement types have different quality weights
            upvotes = engagement_metrics.get("upvotes", 0) * 1.0
            comments = engagement_metrics.get("comments", 0) * 1.5  # Comments indicate higher engagement
            shares = engagement_metrics.get("shares", 0) * 2.0  # Shares indicate strong interest
            
            weighted_engagement = upvotes + comments + shares
            
            # Normalize by content length (longer content naturally gets more engagement)
            content_length = len(signal.get("content", ""))
            normalized_engagement = weighted_engagement / max(1, content_length / 100)
            
            engagement_scores.append(min(100.0, normalized_engagement))
        
        return statistics.mean(engagement_scores) if engagement_scores else 0.0
    
    async def _calculate_source_credibility(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate source credibility score."""
        if not signals:
            return 0.0
        
        credibility_scores = []
        
        for signal in signals:
            source = signal.get("source", "unknown").lower()
            base_credibility = self.source_credibility_scores.get(source, 0.3)
            
            # Adjust credibility based on signal confidence if available
            signal_confidence = signal.get("confidence", 0.5)
            adjusted_credibility = base_credibility * (0.5 + signal_confidence)
            
            credibility_scores.append(adjusted_credibility * 100)
        
        return statistics.mean(credibility_scores) if credibility_scores else 0.0
    
    async def _calculate_temporal_relevance(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate temporal relevance (how recent and relevant the signals are)."""
        if not signals:
            return 0.0
        
        current_time = datetime.utcnow()
        relevance_scores = []
        
        for signal in signals:
            extracted_at = signal.get("extracted_at")
            if not extracted_at:
                relevance_scores.append(50.0)  # Neutral score for unknown dates
                continue
            
            # Parse extraction time
            if isinstance(extracted_at, str):
                try:
                    extracted_time = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
                except:
                    extracted_time = current_time - timedelta(days=30)  # Default to 30 days ago
            else:
                extracted_time = extracted_at
            
            # Calculate age in days
            age_days = (current_time - extracted_time).days
            
            # Relevance decreases with age (exponential decay)
            if age_days <= 7:
                relevance = 100.0  # Very recent
            elif age_days <= 30:
                relevance = 80.0 * math.exp(-age_days / 30)  # Recent
            elif age_days <= 90:
                relevance = 60.0 * math.exp(-age_days / 90)  # Moderately recent
            else:
                relevance = 20.0 * math.exp(-age_days / 365)  # Old
            
            relevance_scores.append(max(5.0, relevance))  # Minimum 5% relevance
        
        return statistics.mean(relevance_scores) if relevance_scores else 0.0
    
    async def _calculate_validation_confidence(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate confidence level for the validation score."""
        if not signals:
            return 0.0
        
        confidence_factors = []
        
        # Signal quantity factor
        signal_count_confidence = min(1.0, len(signals) / 10)  # Max confidence at 10+ signals
        confidence_factors.append(signal_count_confidence)
        
        # Signal quality factor (average confidence of individual signals)
        signal_confidences = [s.get("confidence", 0.5) for s in signals]
        avg_signal_confidence = statistics.mean(signal_confidences)
        confidence_factors.append(avg_signal_confidence)
        
        # Source diversity factor
        unique_sources = len(set(s.get("source", "unknown") for s in signals))
        source_diversity_confidence = min(1.0, unique_sources / 5)  # Max confidence at 5+ sources
        confidence_factors.append(source_diversity_confidence)
        
        # Engagement factor
        total_engagement = sum(
            s.get("engagement_metrics", {}).get("total_engagement", 0) for s in signals
        )
        engagement_confidence = min(1.0, total_engagement / 100)  # Max confidence at 100+ total engagement
        confidence_factors.append(engagement_confidence)
        
        return statistics.mean(confidence_factors)
    
    def _is_recent_signal(self, extracted_at: Any) -> bool:
        """Check if a signal is recent (within last 30 days)."""
        if not extracted_at:
            return False
        
        try:
            if isinstance(extracted_at, str):
                extracted_time = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
            else:
                extracted_time = extracted_at
            
            age_days = (datetime.utcnow() - extracted_time).days
            return age_days <= 30
        except:
            return False


class CompetitiveAnalysisEngine:
    """
    Automated competitive analysis algorithms.
    Implements Requirement 8.3 (identify existing solutions and competitive advantages).
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Competition indicators and patterns
        self.competition_indicators = {
            "direct_competitors": [
                "competitor", "alternative", "similar to", "like", "versus", "vs",
                "compared to", "better than", "instead of", "replace"
            ],
            "existing_solutions": [
                "solution", "tool", "platform", "service", "app", "software",
                "system", "product", "framework", "library"
            ],
            "market_saturation": [
                "saturated", "crowded", "many options", "lots of", "plenty of",
                "numerous", "established players", "market leaders"
            ],
            "market_gaps": [
                "no solution", "nothing available", "gap in market", "unmet need",
                "missing", "lacking", "no good options", "underserved"
            ]
        }
        
        # Known competitive landscapes for different domains
        self.domain_competition_levels = self.config.get("domain_competition", {
            "social_media": 0.9,  # Highly competitive
            "ecommerce": 0.85,
            "productivity": 0.8,
            "finance": 0.75,
            "healthcare": 0.6,  # Regulated, less competitive
            "education": 0.65,
            "enterprise": 0.7,
            "gaming": 0.8,
            "ai_tools": 0.75,
            "developer_tools": 0.7
        })
        
        logger.info("CompetitiveAnalysisEngine initialized", config=self.config)
    
    async def analyze_competition(
        self,
        signals: List[Dict[str, Any]],
        opportunity_context: Optional[Dict[str, Any]] = None
    ) -> CompetitiveAnalysis:
        """
        Perform automated competitive analysis from market signals.
        
        Args:
            signals: List of market signals
            opportunity_context: Additional context about the opportunity
            
        Returns:
            CompetitiveAnalysis with detailed competitive landscape
        """
        if not signals:
            return self._create_empty_analysis()
        
        # Extract competitive intelligence from signals
        competitors = await self._identify_competitors(signals)
        market_saturation = await self._assess_market_saturation(signals, opportunity_context)
        competitive_advantages = await self._identify_competitive_advantages(signals)
        market_gaps = await self._identify_market_gaps(signals)
        differentiation_opportunities = await self._find_differentiation_opportunities(signals)
        competitive_threats = await self._assess_competitive_threats(signals)
        
        # Calculate overall competition score
        competition_score = await self._calculate_competition_score(
            competitors, market_saturation, signals, opportunity_context
        )
        
        # Determine competition level
        competition_level = self._determine_competition_level(competition_score)
        
        # Determine market positioning
        market_positioning = await self._determine_market_positioning(
            competition_score, market_gaps, competitive_advantages
        )
        
        # Calculate confidence level
        confidence_level = await self._calculate_competitive_confidence(signals, competitors)
        
        return CompetitiveAnalysis(
            competition_level=competition_level,
            competition_score=competition_score,
            identified_competitors=competitors,
            market_saturation=market_saturation,
            competitive_advantages=competitive_advantages,
            market_gaps=market_gaps,
            differentiation_opportunities=differentiation_opportunities,
            competitive_threats=competitive_threats,
            market_positioning=market_positioning,
            confidence_level=confidence_level
        )
    
    async def _identify_competitors(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify competitors mentioned in signals."""
        competitors = []
        competitor_mentions = defaultdict(int)
        competitor_contexts = defaultdict(list)
        
        for signal in signals:
            content = signal.get("content", "").lower()
            
            # Look for competitor indicators
            for indicator in self.competition_indicators["direct_competitors"]:
                if indicator in content:
                    # Extract potential competitor names (simplified pattern matching)
                    sentences = content.split('.')
                    for sentence in sentences:
                        if indicator in sentence:
                            # Extract company/product names (basic pattern)
                            words = sentence.split()
                            for i, word in enumerate(words):
                                if indicator in word and i + 1 < len(words):
                                    potential_competitor = words[i + 1].strip('.,!?')
                                    if len(potential_competitor) > 2:
                                        competitor_mentions[potential_competitor] += 1
                                        competitor_contexts[potential_competitor].append(sentence.strip())
        
        # Convert to structured competitor data
        for competitor, mentions in competitor_mentions.items():
            if mentions >= 2:  # Only include competitors mentioned multiple times
                competitors.append({
                    "name": competitor.title(),
                    "mention_count": mentions,
                    "contexts": competitor_contexts[competitor][:3],  # Top 3 contexts
                    "threat_level": min(10.0, mentions * 2),  # Simple threat scoring
                    "identified_from": "signal_analysis"
                })
        
        # Sort by mention count
        competitors.sort(key=lambda x: x["mention_count"], reverse=True)
        
        return competitors[:10]  # Top 10 competitors
    
    async def _assess_market_saturation(
        self, 
        signals: List[Dict[str, Any]], 
        opportunity_context: Optional[Dict[str, Any]]
    ) -> float:
        """Assess market saturation level."""
        saturation_score = 0.0
        
        # Check for saturation indicators in signals
        saturation_mentions = 0
        total_content_length = 0
        
        for signal in signals:
            content = signal.get("content", "").lower()
            total_content_length += len(content)
            
            for indicator in self.competition_indicators["market_saturation"]:
                if indicator in content:
                    saturation_mentions += 1
        
        # Base saturation from mentions
        if total_content_length > 0:
            mention_density = saturation_mentions / (total_content_length / 1000)  # Per 1000 chars
            saturation_score += min(40.0, mention_density * 20)
        
        # Domain-based saturation (if we can infer the domain)
        if opportunity_context:
            ai_solution_types = opportunity_context.get("ai_solution_types", [])
            target_industries = opportunity_context.get("target_industries", [])
            
            # Estimate domain competition
            domain_competition = 0.5  # Default
            for industry in target_industries:
                if industry in self.domain_competition_levels:
                    domain_competition = max(domain_competition, self.domain_competition_levels[industry])
            
            saturation_score += domain_competition * 40
        
        # Existing solutions mentions
        solution_mentions = 0
        for signal in signals:
            content = signal.get("content", "").lower()
            for indicator in self.competition_indicators["existing_solutions"]:
                if indicator in content:
                    solution_mentions += 1
        
        solution_density = solution_mentions / len(signals) if signals else 0
        saturation_score += min(20.0, solution_density * 10)
        
        return min(100.0, saturation_score)
    
    async def _identify_competitive_advantages(self, signals: List[Dict[str, Any]]) -> List[str]:
        """Identify potential competitive advantages from signals."""
        advantages = []
        
        advantage_indicators = {
            "ai_native": ["ai-powered", "machine learning", "intelligent", "smart", "automated"],
            "user_experience": ["easy to use", "intuitive", "user-friendly", "simple", "seamless"],
            "performance": ["fast", "efficient", "scalable", "reliable", "robust"],
            "cost": ["affordable", "cheap", "free", "cost-effective", "budget-friendly"],
            "innovation": ["novel", "innovative", "unique", "first", "breakthrough"],
            "integration": ["integrates with", "compatible", "works with", "connects to"]
        }
        
        advantage_scores = defaultdict(int)
        
        for signal in signals:
            content = signal.get("content", "").lower()
            
            for advantage_type, indicators in advantage_indicators.items():
                for indicator in indicators:
                    if indicator in content:
                        advantage_scores[advantage_type] += 1
        
        # Convert to advantage descriptions
        for advantage_type, score in advantage_scores.items():
            if score >= 2:  # Mentioned in at least 2 signals
                advantage_descriptions = {
                    "ai_native": "AI-native approach with advanced automation capabilities",
                    "user_experience": "Superior user experience and ease of use",
                    "performance": "High performance and scalability advantages",
                    "cost": "Cost-effective solution with competitive pricing",
                    "innovation": "Innovative approach with unique features",
                    "integration": "Strong integration capabilities with existing tools"
                }
                
                if advantage_type in advantage_descriptions:
                    advantages.append(advantage_descriptions[advantage_type])
        
        return advantages
    
    async def _identify_market_gaps(self, signals: List[Dict[str, Any]]) -> List[str]:
        """Identify market gaps from signals."""
        gaps = []
        gap_indicators = defaultdict(list)
        
        for signal in signals:
            content = signal.get("content", "").lower()
            
            for indicator in self.competition_indicators["market_gaps"]:
                if indicator in content:
                    # Extract the context around the gap indicator
                    sentences = content.split('.')
                    for sentence in sentences:
                        if indicator in sentence:
                            gap_indicators[indicator].append(sentence.strip())
        
        # Convert to structured gap descriptions
        for indicator, contexts in gap_indicators.items():
            if len(contexts) >= 2:  # Mentioned in multiple contexts
                gap_description = f"Market gap identified: {indicator} mentioned in {len(contexts)} signals"
                gaps.append(gap_description)
        
        return gaps[:5]  # Top 5 gaps
    
    async def _find_differentiation_opportunities(self, signals: List[Dict[str, Any]]) -> List[str]:
        """Find differentiation opportunities from signal analysis."""
        opportunities = []
        
        # Look for unmet needs and pain points that could be differentiation opportunities
        unmet_needs = []
        
        for signal in signals:
            content = signal.get("content", "").lower()
            signal_type = signal.get("signal_type", "")
            
            # Pain points and feature requests indicate differentiation opportunities
            if signal_type in ["pain_point", "feature_request"]:
                # Extract key phrases that indicate unmet needs
                if any(phrase in content for phrase in ["wish", "would be great", "need", "missing"]):
                    # Simplified extraction of the need
                    sentences = content.split('.')
                    for sentence in sentences:
                        if any(phrase in sentence for phrase in ["wish", "would be great", "need", "missing"]):
                            unmet_needs.append(sentence.strip())
        
        # Convert unmet needs to differentiation opportunities
        if unmet_needs:
            opportunities.append(f"Address unmet needs identified in {len(unmet_needs)} signals")
        
        # Look for technology differentiation opportunities
        ai_mentions = sum(1 for s in signals if "ai" in s.get("content", "").lower())
        if ai_mentions >= len(signals) * 0.3:  # 30% of signals mention AI
            opportunities.append("AI-first approach as key differentiator")
        
        return opportunities
    
    async def _assess_competitive_threats(self, signals: List[Dict[str, Any]]) -> List[str]:
        """Assess competitive threats from signals."""
        threats = []
        
        threat_indicators = [
            "established player", "market leader", "dominant", "monopoly",
            "big tech", "well-funded", "venture backed", "unicorn"
        ]
        
        threat_mentions = 0
        for signal in signals:
            content = signal.get("content", "").lower()
            for indicator in threat_indicators:
                if indicator in content:
                    threat_mentions += 1
        
        if threat_mentions > 0:
            threats.append(f"Established competitors mentioned in {threat_mentions} signals")
        
        # Network effects threat
        network_indicators = ["network effect", "viral", "social", "community"]
        network_mentions = sum(
            1 for s in signals 
            for indicator in network_indicators 
            if indicator in s.get("content", "").lower()
        )
        
        if network_mentions >= 2:
            threats.append("Network effects may create barriers to entry")
        
        return threats
    
    async def _calculate_competition_score(
        self,
        competitors: List[Dict[str, Any]],
        market_saturation: float,
        signals: List[Dict[str, Any]],
        opportunity_context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate overall competition score."""
        
        # Base score from identified competitors
        competitor_score = min(40.0, len(competitors) * 8)
        
        # Market saturation contribution
        saturation_contribution = market_saturation * 0.3
        
        # Signal-based competition indicators
        competition_mentions = 0
        for signal in signals:
            content = signal.get("content", "").lower()
            for indicator in self.competition_indicators["direct_competitors"]:
                if indicator in content:
                    competition_mentions += 1
        
        mention_score = min(20.0, competition_mentions * 2)
        
        # Domain-based competition baseline
        domain_score = 10.0  # Default baseline
        if opportunity_context:
            target_industries = opportunity_context.get("target_industries", [])
            for industry in target_industries:
                if industry in self.domain_competition_levels:
                    domain_score = max(domain_score, self.domain_competition_levels[industry] * 30)
        
        total_score = competitor_score + saturation_contribution + mention_score + domain_score
        return min(100.0, total_score)
    
    def _determine_competition_level(self, competition_score: float) -> str:
        """Determine competition level from score."""
        if competition_score >= 75:
            return "high"
        elif competition_score >= 45:
            return "medium"
        else:
            return "low"
    
    async def _determine_market_positioning(
        self,
        competition_score: float,
        market_gaps: List[str],
        competitive_advantages: List[str]
    ) -> str:
        """Determine market positioning strategy."""
        
        # Blue ocean: low competition + identified gaps + strong advantages
        if competition_score < 40 and len(market_gaps) >= 2 and len(competitive_advantages) >= 2:
            return "blue_ocean"
        
        # Niche: medium competition + specific advantages
        elif competition_score < 70 and len(competitive_advantages) >= 1:
            return "niche"
        
        # Red ocean: high competition
        else:
            return "red_ocean"
    
    async def _calculate_competitive_confidence(
        self,
        signals: List[Dict[str, Any]],
        competitors: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence level for competitive analysis."""
        confidence_factors = []
        
        # Signal quantity factor
        signal_confidence = min(1.0, len(signals) / 8)
        confidence_factors.append(signal_confidence)
        
        # Competitor identification confidence
        competitor_confidence = min(1.0, len(competitors) / 3) if competitors else 0.3
        confidence_factors.append(competitor_confidence)
        
        # Signal quality factor
        avg_signal_confidence = statistics.mean([
            s.get("confidence", 0.5) for s in signals
        ]) if signals else 0.5
        confidence_factors.append(avg_signal_confidence)
        
        return statistics.mean(confidence_factors)
    
    def _create_empty_analysis(self) -> CompetitiveAnalysis:
        """Create empty competitive analysis for edge cases."""
        return CompetitiveAnalysis(
            competition_level="unknown",
            competition_score=50.0,  # Neutral score
            identified_competitors=[],
            market_saturation=50.0,
            competitive_advantages=[],
            market_gaps=[],
            differentiation_opportunities=[],
            competitive_threats=[],
            market_positioning="unknown",
            confidence_level=0.0
        )

class AdvancedScoringEngine:
    """
    Advanced scoring engine that combines market validation and competitive analysis.
    Provides comprehensive opportunity scoring for ranking and filtering.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize component scorers
        self.market_validator = MarketValidationScorer(self.config.get("market_validation", {}))
        self.competitive_analyzer = CompetitiveAnalysisEngine(self.config.get("competitive_analysis", {}))
        
        # Overall scoring weights
        self.scoring_weights = self.config.get("scoring_weights", {
            "market_validation": 0.35,
            "competitive_analysis": 0.25,
            "ai_feasibility": 0.20,
            "implementation_complexity": 0.10,
            "market_timing": 0.10
        })
        
        logger.info("AdvancedScoringEngine initialized", config=self.config)
    
    async def calculate_advanced_score(
        self,
        signals: List[Dict[str, Any]],
        opportunity_context: Optional[Dict[str, Any]] = None,
        agent_analysis: Optional[Dict[str, Any]] = None
    ) -> AdvancedOpportunityScore:
        """
        Calculate comprehensive advanced opportunity score.
        
        Args:
            signals: List of market signals
            opportunity_context: Opportunity context information
            agent_analysis: Analysis results from AI agents
            
        Returns:
            AdvancedOpportunityScore with detailed breakdown
        """
        # Calculate market validation score
        market_validation = await self.market_validator.calculate_market_validation_score(
            signals, opportunity_context
        )
        
        # Calculate competitive analysis
        competitive_analysis = await self.competitive_analyzer.analyze_competition(
            signals, opportunity_context
        )
        
        # Calculate AI feasibility score (from agent analysis or signals)
        ai_feasibility_score = await self._calculate_ai_feasibility_score(
            signals, opportunity_context, agent_analysis
        )
        
        # Calculate implementation complexity
        implementation_complexity = await self._calculate_implementation_complexity(
            signals, opportunity_context, agent_analysis
        )
        
        # Calculate market timing score
        market_timing_score = await self._calculate_market_timing_score(
            signals, opportunity_context, agent_analysis
        )
        
        # Calculate business viability score
        business_viability_score = await self._calculate_business_viability_score(
            market_validation, competitive_analysis, ai_feasibility_score
        )
        
        # Calculate risk assessment score
        risk_assessment_score = await self._calculate_risk_assessment_score(
            competitive_analysis, implementation_complexity, market_timing_score
        )
        
        # Calculate overall score
        overall_score = (
            market_validation.overall_score * self.scoring_weights["market_validation"] +
            (100 - competitive_analysis.competition_score) * self.scoring_weights["competitive_analysis"] +
            ai_feasibility_score * self.scoring_weights["ai_feasibility"] +
            (100 - implementation_complexity) * self.scoring_weights["implementation_complexity"] +
            market_timing_score * self.scoring_weights["market_timing"]
        )
        
        # Calculate overall confidence
        confidence_level = statistics.mean([
            market_validation.confidence_level,
            competitive_analysis.confidence_level,
            0.8  # Base confidence for other components
        ])
        
        return AdvancedOpportunityScore(
            overall_score=min(100.0, overall_score),
            market_validation=market_validation,
            competitive_analysis=competitive_analysis,
            ai_feasibility_score=ai_feasibility_score,
            implementation_complexity=implementation_complexity,
            market_timing_score=market_timing_score,
            business_viability_score=business_viability_score,
            risk_assessment_score=risk_assessment_score,
            confidence_level=confidence_level,
            scoring_timestamp=datetime.utcnow()
        )
    
    async def _calculate_ai_feasibility_score(
        self,
        signals: List[Dict[str, Any]],
        opportunity_context: Optional[Dict[str, Any]],
        agent_analysis: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate AI feasibility score."""
        
        # Use agent analysis if available
        if agent_analysis and "ai_feasibility_score" in agent_analysis:
            return agent_analysis["ai_feasibility_score"]
        
        # Calculate from signals and context
        ai_relevance_scores = [
            s.get("ai_relevance_score", 0) for s in signals
            if s.get("ai_relevance_score") is not None
        ]
        
        if ai_relevance_scores:
            base_score = statistics.mean(ai_relevance_scores)
        else:
            base_score = 50.0  # Neutral score
        
        # Adjust based on AI solution types if available
        if opportunity_context and opportunity_context.get("ai_solution_types"):
            ai_types = opportunity_context["ai_solution_types"]
            
            # More mature AI types get higher feasibility scores
            maturity_scores = {
                "machine_learning": 0.9,
                "natural_language_processing": 0.85,
                "computer_vision": 0.8,
                "recommendation_systems": 0.9,
                "predictive_analytics": 0.85,
                "automation": 0.8,
                "speech_recognition": 0.75,
                "optimization": 0.8
            }
            
            type_scores = [maturity_scores.get(ai_type, 0.6) for ai_type in ai_types]
            if type_scores:
                type_adjustment = statistics.mean(type_scores) * 20  # Up to 20 point adjustment
                base_score = min(100.0, base_score + type_adjustment)
        
        return base_score
    
    async def _calculate_implementation_complexity(
        self,
        signals: List[Dict[str, Any]],
        opportunity_context: Optional[Dict[str, Any]],
        agent_analysis: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate implementation complexity score (higher = more complex)."""
        
        # Use agent analysis if available
        if agent_analysis and "implementation_complexity" in agent_analysis:
            return agent_analysis["implementation_complexity"]
        
        complexity_score = 50.0  # Base complexity
        
        # Adjust based on AI solution types
        if opportunity_context and opportunity_context.get("ai_solution_types"):
            ai_types = opportunity_context["ai_solution_types"]
            
            # Different AI types have different complexity levels
            complexity_levels = {
                "automation": 30.0,  # Lower complexity
                "recommendation_systems": 40.0,
                "predictive_analytics": 45.0,
                "natural_language_processing": 60.0,
                "machine_learning": 65.0,
                "computer_vision": 70.0,
                "speech_recognition": 75.0,
                "optimization": 55.0
            }
            
            type_complexities = [complexity_levels.get(ai_type, 50.0) for ai_type in ai_types]
            if type_complexities:
                complexity_score = statistics.mean(type_complexities)
        
        # Adjust based on signal complexity indicators
        complexity_indicators = [
            "complex", "difficult", "challenging", "advanced", "sophisticated",
            "enterprise", "scalable", "real-time", "distributed"
        ]
        
        complexity_mentions = 0
        for signal in signals:
            content = signal.get("content", "").lower()
            for indicator in complexity_indicators:
                if indicator in content:
                    complexity_mentions += 1
        
        if complexity_mentions > 0:
            complexity_adjustment = min(20.0, complexity_mentions * 3)
            complexity_score = min(100.0, complexity_score + complexity_adjustment)
        
        return complexity_score
    
    async def _calculate_market_timing_score(
        self,
        signals: List[Dict[str, Any]],
        opportunity_context: Optional[Dict[str, Any]],
        agent_analysis: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate market timing score."""
        
        # Use agent analysis if available
        if agent_analysis and "market_timing_score" in agent_analysis:
            return agent_analysis["market_timing_score"]
        
        timing_score = 50.0  # Base timing score
        
        # Check for timing indicators in signals
        timing_indicators = {
            "urgent": 20,
            "now": 15,
            "immediate": 18,
            "asap": 15,
            "trending": 12,
            "growing": 10,
            "emerging": 8,
            "future": -5,
            "someday": -10,
            "eventually": -8
        }
        
        timing_adjustments = []
        for signal in signals:
            content = signal.get("content", "").lower()
            for indicator, adjustment in timing_indicators.items():
                if indicator in content:
                    timing_adjustments.append(adjustment)
        
        if timing_adjustments:
            avg_adjustment = statistics.mean(timing_adjustments)
            timing_score = max(0.0, min(100.0, timing_score + avg_adjustment))
        
        # Boost score for recent signals (good timing)
        recent_signals = sum(
            1 for s in signals 
            if self._is_recent_signal(s.get("extracted_at"))
        )
        
        if signals:
            recent_ratio = recent_signals / len(signals)
            timing_score += recent_ratio * 20  # Up to 20 point boost
        
        return min(100.0, timing_score)
    
    async def _calculate_business_viability_score(
        self,
        market_validation: MarketValidationScore,
        competitive_analysis: CompetitiveAnalysis,
        ai_feasibility_score: float
    ) -> float:
        """Calculate business viability score."""
        
        # Combine key factors for business viability
        viability_factors = [
            market_validation.market_demand * 0.4,  # Market demand is crucial
            (100 - competitive_analysis.competition_score) * 0.3,  # Lower competition is better
            ai_feasibility_score * 0.2,  # Technical feasibility
            market_validation.pain_intensity * 0.1  # Pain intensity indicates willingness to pay
        ]
        
        viability_score = sum(viability_factors)
        
        # Bonus for identified competitive advantages
        if len(competitive_analysis.competitive_advantages) >= 2:
            viability_score += 10.0
        
        # Bonus for market gaps
        if len(competitive_analysis.market_gaps) >= 1:
            viability_score += 5.0
        
        return min(100.0, viability_score)
    
    async def _calculate_risk_assessment_score(
        self,
        competitive_analysis: CompetitiveAnalysis,
        implementation_complexity: float,
        market_timing_score: float
    ) -> float:
        """Calculate risk assessment score (higher = more risky)."""
        
        risk_factors = [
            competitive_analysis.competition_score * 0.4,  # High competition = high risk
            implementation_complexity * 0.3,  # High complexity = high risk
            (100 - market_timing_score) * 0.2,  # Poor timing = high risk
            competitive_analysis.market_saturation * 0.1  # Market saturation = risk
        ]
        
        risk_score = sum(risk_factors)
        
        # Additional risk from competitive threats
        if len(competitive_analysis.competitive_threats) >= 2:
            risk_score += 10.0
        
        # Risk reduction from competitive advantages
        if len(competitive_analysis.competitive_advantages) >= 2:
            risk_score = max(0.0, risk_score - 15.0)
        
        return min(100.0, risk_score)
    
    def _is_recent_signal(self, extracted_at: Any) -> bool:
        """Check if a signal is recent (within last 30 days)."""
        if not extracted_at:
            return False
        
        try:
            if isinstance(extracted_at, str):
                extracted_time = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
            else:
                extracted_time = extracted_at
            
            age_days = (datetime.utcnow() - extracted_time).days
            return age_days <= 30
        except:
            return False


# Global scoring engine instance
advanced_scoring_engine = AdvancedScoringEngine()