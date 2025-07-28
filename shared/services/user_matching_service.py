"""User matching service for connecting users with complementary skills and interests.

Supports Requirements 9.1-9.2 (Marketplace and Networking Features):
- Interest-based matching for co-founder connections
- Complementary skill identification for team formation
- User compatibility scoring and recommendations
"""

import json
import math
from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.orm import selectinload

from shared.models.user import User, UserRole
from shared.models.user_interaction import UserInteraction, UserPreference, InteractionType
from shared.models.opportunity import Opportunity
from shared.cache import cache_manager, CacheKeys
import structlog

logger = structlog.get_logger(__name__)


class MatchingType(str, Enum):
    """Types of user matching algorithms."""
    INTEREST_BASED = "interest_based"
    SKILL_COMPLEMENTARY = "skill_complementary"
    COLLABORATION_HISTORY = "collaboration_history"
    EXPERTISE_OVERLAP = "expertise_overlap"


@dataclass
class UserMatch:
    """Represents a user match with scoring details."""
    user_id: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    match_score: float  # 0.0 to 1.0
    match_type: MatchingType
    match_reasons: List[str]
    common_interests: List[str]
    complementary_skills: List[str]
    expertise_domains: List[str]
    reputation_score: float
    compatibility_factors: Dict[str, float]


@dataclass
class SkillGap:
    """Represents a skill gap that could be filled by another user."""
    skill_category: str
    skill_name: str
    importance_score: float  # 0.0 to 1.0
    gap_severity: float  # 0.0 to 1.0 (higher = more critical gap)


@dataclass
class InterestProfile:
    """User's interest profile derived from interactions."""
    ai_solution_preferences: Dict[str, float]  # ai_type -> preference_score
    industry_preferences: Dict[str, float]  # industry -> preference_score
    complexity_preference: Optional[str]
    market_size_preference: Optional[str]
    activity_patterns: Dict[str, Any]
    engagement_level: float


class UserMatchingService:
    """Service for matching users based on interests and complementary skills."""
    
    async def find_interest_based_matches(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        min_match_score: float = 0.3
    ) -> List[UserMatch]:
        """Find users with similar interests for potential collaboration.
        
        Supports Requirement 9.1 (Interest-based matching).
        
        Args:
            db: Database session
            user_id: Target user ID
            limit: Maximum number of matches to return
            min_match_score: Minimum match score threshold
            
        Returns:
            List of user matches sorted by compatibility score
        """
        # Try cache first
        cache_key = CacheKeys.format_key(
            CacheKeys.USER_MATCHES,
            user_id=user_id,
            match_type="interest_based",
            limit=limit
        )
        
        cached_matches = None
        if cache_manager is not None:
            try:
                cached_matches = await cache_manager.get(cache_key)
                if cached_matches:
                    logger.info("Returning cached interest-based matches", user_id=user_id)
                    return [UserMatch(**match) for match in cached_matches]
            except Exception as e:
                logger.warning("Failed to retrieve cached matches", error=str(e))
        
        # Get user's interest profile
        user_profile = await self._build_user_interest_profile(db, user_id)
        if not user_profile:
            logger.warning("Could not build interest profile for user", user_id=user_id)
            return []
        
        # Get potential matches (active users with interactions)
        potential_matches = await self._get_potential_matches(db, user_id)
        
        # Calculate interest-based compatibility scores
        matches = []
        for candidate in potential_matches:
            candidate_profile = await self._build_user_interest_profile(db, candidate.id)
            if not candidate_profile:
                continue
            
            match_score = await self._calculate_interest_similarity(user_profile, candidate_profile)
            
            if match_score >= min_match_score:
                match = await self._create_user_match(
                    candidate,
                    match_score,
                    MatchingType.INTEREST_BASED,
                    user_profile,
                    candidate_profile
                )
                matches.append(match)
        
        # Sort by match score and limit results
        matches.sort(key=lambda x: x.match_score, reverse=True)
        final_matches = matches[:limit]
        
        # Cache results
        if cache_manager is not None and final_matches:
            try:
                cache_data = [match.__dict__ for match in final_matches]
                await cache_manager.set(cache_key, cache_data, expire=3600)  # 1 hour
            except Exception as e:
                logger.warning("Failed to cache matches", error=str(e))
        
        logger.info(
            "Found interest-based matches",
            user_id=user_id,
            match_count=len(final_matches),
            avg_score=sum(m.match_score for m in final_matches) / len(final_matches) if final_matches else 0
        )
        
        return final_matches
    
    async def find_complementary_skill_matches(
        self,
        db: AsyncSession,
        user_id: str,
        opportunity_id: Optional[str] = None,
        limit: int = 20,
        min_match_score: float = 0.4
    ) -> List[UserMatch]:
        """Find users with complementary skills for team formation.
        
        Supports Requirement 9.2 (Complementary skill identification).
        
        Args:
            db: Database session
            user_id: Target user ID
            opportunity_id: Optional opportunity context for skill requirements
            limit: Maximum number of matches to return
            min_match_score: Minimum match score threshold
            
        Returns:
            List of user matches with complementary skills
        """
        # Get user's current skills and identify gaps
        user_skills = await self._extract_user_skills(db, user_id)
        skill_gaps = await self._identify_skill_gaps(db, user_id, opportunity_id)
        
        if not skill_gaps:
            logger.info("No skill gaps identified for user", user_id=user_id)
            return []
        
        # Get potential matches
        potential_matches = await self._get_potential_matches(db, user_id)
        
        # Calculate complementary skill scores
        matches = []
        for candidate in potential_matches:
            candidate_skills = await self._extract_user_skills(db, candidate.id)
            
            match_score = await self._calculate_skill_complementarity(
                user_skills, candidate_skills, skill_gaps
            )
            
            if match_score >= min_match_score:
                match = await self._create_skill_match(
                    candidate,
                    match_score,
                    user_skills,
                    candidate_skills,
                    skill_gaps
                )
                matches.append(match)
        
        # Sort by match score and limit results
        matches.sort(key=lambda x: x.match_score, reverse=True)
        final_matches = matches[:limit]
        
        logger.info(
            "Found complementary skill matches",
            user_id=user_id,
            match_count=len(final_matches),
            skill_gaps=len(skill_gaps)
        )
        
        return final_matches
    
    async def find_hybrid_matches(
        self,
        db: AsyncSession,
        user_id: str,
        opportunity_id: Optional[str] = None,
        limit: int = 15,
        min_match_score: float = 0.35
    ) -> List[UserMatch]:
        """Find matches using both interest and skill complementarity.
        
        Args:
            db: Database session
            user_id: Target user ID
            opportunity_id: Optional opportunity context
            limit: Maximum number of matches to return
            min_match_score: Minimum match score threshold
            
        Returns:
            List of hybrid user matches
        """
        # Get both types of matches
        interest_matches = await self.find_interest_based_matches(
            db, user_id, limit * 2, min_match_score * 0.8
        )
        skill_matches = await self.find_complementary_skill_matches(
            db, user_id, opportunity_id, limit * 2, min_match_score * 0.8
        )
        
        # Combine and re-score matches
        all_matches = {}
        
        # Add interest matches
        for match in interest_matches:
            all_matches[match.user_id] = match
        
        # Add or enhance with skill matches
        for match in skill_matches:
            if match.user_id in all_matches:
                # Combine scores (weighted average)
                existing_match = all_matches[match.user_id]
                combined_score = (existing_match.match_score * 0.6) + (match.match_score * 0.4)
                
                # Merge match reasons and skills
                combined_reasons = list(set(existing_match.match_reasons + match.match_reasons))
                combined_skills = list(set(existing_match.complementary_skills + match.complementary_skills))
                
                # Update the match
                existing_match.match_score = combined_score
                existing_match.match_reasons = combined_reasons
                existing_match.complementary_skills = combined_skills
                existing_match.match_type = MatchingType.SKILL_COMPLEMENTARY  # Hybrid indicator
            else:
                all_matches[match.user_id] = match
        
        # Filter by minimum score and sort
        final_matches = [
            match for match in all_matches.values()
            if match.match_score >= min_match_score
        ]
        final_matches.sort(key=lambda x: x.match_score, reverse=True)
        
        return final_matches[:limit]
    
    async def _build_user_interest_profile(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[InterestProfile]:
        """Build a user's interest profile from their interactions."""
        
        # Get user interactions with opportunities
        interactions_query = select(UserInteraction).options(
            selectinload(UserInteraction.opportunity)
        ).where(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.opportunity_id.isnot(None)
            )
        ).order_by(desc(UserInteraction.created_at)).limit(100)
        
        result = await db.execute(interactions_query)
        interactions = result.scalars().all()
        
        if not interactions:
            return None
        
        # Analyze preferences
        ai_preferences = {}
        industry_preferences = {}
        complexity_counts = {}
        market_size_counts = {}
        total_weight = 0.0
        
        for interaction in interactions:
            if not interaction.opportunity:
                continue
            
            # Weight by interaction type and recency
            interaction_weight = {
                InteractionType.VIEW: 1.0,
                InteractionType.CLICK: 2.0,
                InteractionType.BOOKMARK: 3.0,
                InteractionType.VALIDATE: 2.5,
                InteractionType.SHARE: 2.0
            }.get(interaction.interaction_type, 1.0)
            
            # Apply recency decay
            days_ago = (datetime.utcnow() - interaction.created_at).days
            recency_weight = math.exp(-days_ago / 30.0)  # 30-day decay
            
            final_weight = interaction_weight * recency_weight
            total_weight += final_weight
            
            # Extract AI solution preferences
            if interaction.opportunity.ai_solution_types:
                try:
                    ai_types = json.loads(interaction.opportunity.ai_solution_types)
                    if isinstance(ai_types, list):
                        for ai_type in ai_types:
                            ai_preferences[ai_type] = ai_preferences.get(ai_type, 0) + final_weight
                except json.JSONDecodeError:
                    pass
            
            # Extract industry preferences
            if interaction.opportunity.target_industries:
                try:
                    industries = json.loads(interaction.opportunity.target_industries)
                    if isinstance(industries, list):
                        for industry in industries:
                            industry_preferences[industry] = industry_preferences.get(industry, 0) + final_weight
                except json.JSONDecodeError:
                    pass
            
            # Track complexity and market size preferences
            if interaction.opportunity.implementation_complexity:
                complexity_counts[interaction.opportunity.implementation_complexity] = \
                    complexity_counts.get(interaction.opportunity.implementation_complexity, 0) + final_weight
            
            if interaction.opportunity.market_size_estimate:
                market_size_counts[interaction.opportunity.market_size_estimate] = \
                    market_size_counts.get(interaction.opportunity.market_size_estimate, 0) + final_weight
        
        # Normalize preferences
        if total_weight > 0:
            for ai_type in ai_preferences:
                ai_preferences[ai_type] /= total_weight
            for industry in industry_preferences:
                industry_preferences[industry] /= total_weight
        
        # Determine preferred complexity and market size
        preferred_complexity = max(complexity_counts.items(), key=lambda x: x[1])[0] if complexity_counts else None
        preferred_market_size = max(market_size_counts.items(), key=lambda x: x[1])[0] if market_size_counts else None
        
        # Calculate engagement level
        engagement_level = min(1.0, len(interactions) / 50.0)  # Normalize to 0-1
        
        return InterestProfile(
            ai_solution_preferences=ai_preferences,
            industry_preferences=industry_preferences,
            complexity_preference=preferred_complexity,
            market_size_preference=preferred_market_size,
            activity_patterns={
                "total_interactions": len(interactions),
                "recent_interactions": len([i for i in interactions if (datetime.utcnow() - i.created_at).days <= 7]),
                "interaction_types": {t.value: len([i for i in interactions if i.interaction_type == t]) for t in InteractionType}
            },
            engagement_level=engagement_level
        )
    
    async def _get_potential_matches(
        self,
        db: AsyncSession,
        user_id: str,
        min_reputation: float = 1.0
    ) -> List[User]:
        """Get potential user matches (active users with sufficient reputation)."""
        
        query = select(User).where(
            and_(
                User.id != user_id,
                User.is_active == True,
                User.reputation_score >= min_reputation
            )
        ).limit(200)  # Reasonable limit for processing
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def _calculate_interest_similarity(
        self,
        user_profile: InterestProfile,
        candidate_profile: InterestProfile
    ) -> float:
        """Calculate similarity score between two interest profiles."""
        
        similarity_scores = []
        
        # AI solution type similarity (Cosine similarity)
        ai_similarity = self._calculate_cosine_similarity(
            user_profile.ai_solution_preferences,
            candidate_profile.ai_solution_preferences
        )
        similarity_scores.append(ai_similarity * 0.4)  # 40% weight
        
        # Industry similarity
        industry_similarity = self._calculate_cosine_similarity(
            user_profile.industry_preferences,
            candidate_profile.industry_preferences
        )
        similarity_scores.append(industry_similarity * 0.3)  # 30% weight
        
        # Complexity preference match
        complexity_match = 0.0
        if (user_profile.complexity_preference and 
            candidate_profile.complexity_preference and
            user_profile.complexity_preference == candidate_profile.complexity_preference):
            complexity_match = 1.0
        similarity_scores.append(complexity_match * 0.15)  # 15% weight
        
        # Market size preference match
        market_size_match = 0.0
        if (user_profile.market_size_preference and 
            candidate_profile.market_size_preference and
            user_profile.market_size_preference == candidate_profile.market_size_preference):
            market_size_match = 1.0
        similarity_scores.append(market_size_match * 0.15)  # 15% weight
        
        return sum(similarity_scores)
    
    def _calculate_cosine_similarity(self, dict1: Dict[str, float], dict2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two preference dictionaries."""
        
        if not dict1 or not dict2:
            return 0.0
        
        # Get all keys
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        if not all_keys:
            return 0.0
        
        # Create vectors
        vec1 = [dict1.get(key, 0.0) for key in all_keys]
        vec2 = [dict2.get(key, 0.0) for key in all_keys]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def _extract_user_skills(self, db: AsyncSession, user_id: str) -> Dict[str, float]:
        """Extract user skills from their profile and interactions."""
        
        # Get user profile
        user_query = select(User).where(User.id == user_id)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            return {}
        
        skills = {}
        
        # Extract from expertise domains
        if user.expertise_domains:
            try:
                domains = json.loads(user.expertise_domains)
                if isinstance(domains, list):
                    for domain in domains:
                        skills[f"expertise_{domain}"] = 1.0
            except json.JSONDecodeError:
                pass
        
        # Infer skills from interaction patterns
        interactions_query = select(UserInteraction).options(
            selectinload(UserInteraction.opportunity)
        ).where(
            and_(
                UserInteraction.user_id == user_id,
                UserInteraction.opportunity_id.isnot(None)
            )
        ).limit(50)
        
        result = await db.execute(interactions_query)
        interactions = result.scalars().all()
        
        # Analyze AI solution types user has engaged with
        ai_type_counts = {}
        for interaction in interactions:
            if interaction.opportunity and interaction.opportunity.ai_solution_types:
                try:
                    ai_types = json.loads(interaction.opportunity.ai_solution_types)
                    if isinstance(ai_types, list):
                        for ai_type in ai_types:
                            ai_type_counts[ai_type] = ai_type_counts.get(ai_type, 0) + 1
                except json.JSONDecodeError:
                    pass
        
        # Convert to skill scores (normalized by total interactions)
        total_interactions = len(interactions)
        if total_interactions > 0:
            for ai_type, count in ai_type_counts.items():
                skill_score = min(1.0, count / total_interactions * 2)  # Scale up engagement
                skills[f"ai_{ai_type}"] = skill_score
        
        # Add role-based skills
        role_skills = {
            UserRole.EXPERT: {"domain_expertise": 1.0, "validation": 0.9},
            UserRole.MODERATOR: {"moderation": 1.0, "community_management": 0.8},
            UserRole.ADMIN: {"platform_management": 1.0, "technical_oversight": 0.9}
        }
        
        if user.role in role_skills:
            skills.update(role_skills[user.role])
        
        return skills
    
    async def _identify_skill_gaps(
        self,
        db: AsyncSession,
        user_id: str,
        opportunity_id: Optional[str] = None
    ) -> List[SkillGap]:
        """Identify skill gaps for a user, optionally in context of an opportunity."""
        
        user_skills = await self._extract_user_skills(db, user_id)
        skill_gaps = []
        
        if opportunity_id:
            # Get opportunity-specific skill requirements
            opp_query = select(Opportunity).where(Opportunity.id == opportunity_id)
            result = await db.execute(opp_query)
            opportunity = result.scalar_one_or_none()
            
            if opportunity:
                required_skills = await self._extract_opportunity_skill_requirements(opportunity)
                
                for skill_category, required_skills_list in required_skills.items():
                    for skill in required_skills_list:
                        skill_key = f"{skill_category}_{skill}"
                        user_skill_level = user_skills.get(skill_key, 0.0)
                        
                        if user_skill_level < 0.5:  # Significant gap
                            gap_severity = 1.0 - user_skill_level
                            skill_gaps.append(SkillGap(
                                skill_category=skill_category,
                                skill_name=skill,
                                importance_score=0.8,  # High importance for opportunity-specific skills
                                gap_severity=gap_severity
                            ))
        else:
            # General skill gap analysis based on user's interests
            user_profile = await self._build_user_interest_profile(db, user_id)
            if user_profile:
                # Identify gaps in AI solution types user is interested in but lacks skills
                for ai_type, interest_score in user_profile.ai_solution_preferences.items():
                    skill_key = f"ai_{ai_type}"
                    user_skill_level = user_skills.get(skill_key, 0.0)
                    
                    if interest_score > 0.3 and user_skill_level < 0.4:  # High interest, low skill
                        gap_severity = interest_score - user_skill_level
                        skill_gaps.append(SkillGap(
                            skill_category="ai",
                            skill_name=ai_type,
                            importance_score=interest_score,
                            gap_severity=max(0.0, gap_severity)
                        ))
        
        # Add common complementary skills
        common_gaps = [
            SkillGap("business", "strategy", 0.7, 0.6),
            SkillGap("technical", "architecture", 0.8, 0.7),
            SkillGap("product", "management", 0.6, 0.5),
            SkillGap("marketing", "growth", 0.5, 0.4),
            SkillGap("finance", "fundraising", 0.6, 0.5)
        ]
        
        # Filter common gaps based on user's existing skills
        for gap in common_gaps:
            skill_key = f"{gap.skill_category}_{gap.skill_name}"
            if user_skills.get(skill_key, 0.0) < 0.3:
                skill_gaps.append(gap)
        
        return skill_gaps
    
    async def _extract_opportunity_skill_requirements(self, opportunity: Opportunity) -> Dict[str, List[str]]:
        """Extract skill requirements from an opportunity."""
        
        requirements = {
            "ai": [],
            "technical": [],
            "business": [],
            "domain": []
        }
        
        # AI solution types
        if opportunity.ai_solution_types:
            try:
                ai_types = json.loads(opportunity.ai_solution_types)
                if isinstance(ai_types, list):
                    requirements["ai"].extend(ai_types)
            except json.JSONDecodeError:
                pass
        
        # Technical complexity implies certain skills
        if opportunity.implementation_complexity:
            complexity_skills = {
                "low": ["basic_programming", "api_integration"],
                "medium": ["software_architecture", "database_design", "api_development"],
                "high": ["distributed_systems", "scalability", "performance_optimization"]
            }
            requirements["technical"].extend(complexity_skills.get(opportunity.implementation_complexity, []))
        
        # Industry-specific domain knowledge
        if opportunity.target_industries:
            try:
                industries = json.loads(opportunity.target_industries)
                if isinstance(industries, list):
                    requirements["domain"].extend(industries)
            except json.JSONDecodeError:
                pass
        
        # Business skills based on market size
        if opportunity.market_size_estimate:
            if opportunity.market_size_estimate in ["large", "enterprise"]:
                requirements["business"].extend(["enterprise_sales", "partnerships", "scaling"])
            else:
                requirements["business"].extend(["product_market_fit", "customer_development"])
        
        return requirements
    
    async def _calculate_skill_complementarity(
        self,
        user_skills: Dict[str, float],
        candidate_skills: Dict[str, float],
        skill_gaps: List[SkillGap]
    ) -> float:
        """Calculate how well a candidate's skills complement the user's gaps."""
        
        if not skill_gaps:
            return 0.0
        
        total_gap_importance = sum(gap.importance_score * gap.gap_severity for gap in skill_gaps)
        if total_gap_importance == 0:
            return 0.0
        
        filled_gap_score = 0.0
        
        for gap in skill_gaps:
            skill_key = f"{gap.skill_category}_{gap.skill_name}"
            candidate_skill_level = candidate_skills.get(skill_key, 0.0)
            
            # How well does the candidate fill this gap?
            gap_fill_score = min(1.0, candidate_skill_level / 0.7)  # Normalize to 70% threshold
            weighted_score = gap_fill_score * gap.importance_score * gap.gap_severity
            
            filled_gap_score += weighted_score
        
        # Normalize by total possible score
        complementarity_score = filled_gap_score / total_gap_importance
        
        # Bonus for non-overlapping skills (diversity)
        overlap_penalty = self._calculate_skill_overlap(user_skills, candidate_skills)
        diversity_bonus = max(0.0, 1.0 - overlap_penalty) * 0.2  # Up to 20% bonus
        
        return min(1.0, complementarity_score + diversity_bonus)
    
    def _calculate_skill_overlap(self, skills1: Dict[str, float], skills2: Dict[str, float]) -> float:
        """Calculate overlap between two skill sets (0 = no overlap, 1 = complete overlap)."""
        
        if not skills1 or not skills2:
            return 0.0
        
        common_skills = set(skills1.keys()) & set(skills2.keys())
        if not common_skills:
            return 0.0
        
        overlap_score = 0.0
        total_skills = len(set(skills1.keys()) | set(skills2.keys()))
        
        for skill in common_skills:
            # Higher overlap for skills where both users are strong
            skill_overlap = min(skills1[skill], skills2[skill])
            overlap_score += skill_overlap
        
        return overlap_score / total_skills if total_skills > 0 else 0.0
    
    async def _create_user_match(
        self,
        candidate: User,
        match_score: float,
        match_type: MatchingType,
        user_profile: InterestProfile,
        candidate_profile: InterestProfile
    ) -> UserMatch:
        """Create a UserMatch object for interest-based matching."""
        
        # Find common interests
        common_ai_types = set(user_profile.ai_solution_preferences.keys()) & \
                         set(candidate_profile.ai_solution_preferences.keys())
        common_industries = set(user_profile.industry_preferences.keys()) & \
                          set(candidate_profile.industry_preferences.keys())
        
        common_interests = list(common_ai_types) + list(common_industries)
        
        # Generate match reasons
        match_reasons = []
        if common_ai_types:
            match_reasons.append(f"Shared interest in {', '.join(list(common_ai_types)[:3])}")
        if common_industries:
            match_reasons.append(f"Common industry focus: {', '.join(list(common_industries)[:3])}")
        if (user_profile.complexity_preference == candidate_profile.complexity_preference and 
            user_profile.complexity_preference):
            match_reasons.append(f"Similar complexity preference: {user_profile.complexity_preference}")
        
        # Extract expertise domains
        expertise_domains = []
        if candidate.expertise_domains:
            try:
                domains = json.loads(candidate.expertise_domains)
                if isinstance(domains, list):
                    expertise_domains = domains
            except json.JSONDecodeError:
                pass
        
        return UserMatch(
            user_id=candidate.id,
            username=candidate.username,
            full_name=candidate.full_name,
            avatar_url=candidate.avatar_url,
            match_score=match_score,
            match_type=match_type,
            match_reasons=match_reasons,
            common_interests=common_interests,
            complementary_skills=[],  # Not applicable for interest-based matching
            expertise_domains=expertise_domains,
            reputation_score=candidate.reputation_score,
            compatibility_factors={
                "ai_similarity": self._calculate_cosine_similarity(
                    user_profile.ai_solution_preferences,
                    candidate_profile.ai_solution_preferences
                ),
                "industry_similarity": self._calculate_cosine_similarity(
                    user_profile.industry_preferences,
                    candidate_profile.industry_preferences
                ),
                "engagement_compatibility": abs(user_profile.engagement_level - candidate_profile.engagement_level)
            }
        )
    
    async def _create_skill_match(
        self,
        candidate: User,
        match_score: float,
        user_skills: Dict[str, float],
        candidate_skills: Dict[str, float],
        skill_gaps: List[SkillGap]
    ) -> UserMatch:
        """Create a UserMatch object for skill-based matching."""
        
        # Find complementary skills
        complementary_skills = []
        for gap in skill_gaps:
            skill_key = f"{gap.skill_category}_{gap.skill_name}"
            if candidate_skills.get(skill_key, 0.0) > 0.5:  # Candidate has this skill
                complementary_skills.append(f"{gap.skill_category}: {gap.skill_name}")
        
        # Generate match reasons
        match_reasons = []
        if complementary_skills:
            match_reasons.append(f"Fills skill gaps: {', '.join(complementary_skills[:3])}")
        
        skill_overlap = self._calculate_skill_overlap(user_skills, candidate_skills)
        if skill_overlap < 0.3:
            match_reasons.append("Diverse skill set with minimal overlap")
        
        # Extract expertise domains
        expertise_domains = []
        if candidate.expertise_domains:
            try:
                domains = json.loads(candidate.expertise_domains)
                if isinstance(domains, list):
                    expertise_domains = domains
            except json.JSONDecodeError:
                pass
        
        return UserMatch(
            user_id=candidate.id,
            username=candidate.username,
            full_name=candidate.full_name,
            avatar_url=candidate.avatar_url,
            match_score=match_score,
            match_type=MatchingType.SKILL_COMPLEMENTARY,
            match_reasons=match_reasons,
            common_interests=[],  # Not applicable for skill-based matching
            complementary_skills=complementary_skills,
            expertise_domains=expertise_domains,
            reputation_score=candidate.reputation_score,
            compatibility_factors={
                "skill_complementarity": match_score,
                "skill_overlap": skill_overlap,
                "gap_coverage": len(complementary_skills) / max(1, len(skill_gaps))
            }
        )


# Global service instance
user_matching_service = UserMatchingService()