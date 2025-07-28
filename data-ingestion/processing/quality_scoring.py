"""Data quality scoring and assessment for market signals."""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import math

try:
    from ..plugins.base import RawData
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from plugins.base import RawData


logger = logging.getLogger(__name__)


class QualityLevel(str, Enum):
    """Quality level enumeration."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    REJECTED = "rejected"


@dataclass
class QualityMetrics:
    """Quality metrics for a data item."""
    overall_score: float
    quality_level: QualityLevel
    content_quality: float
    engagement_quality: float
    source_credibility: float
    relevance_score: float
    freshness_score: float
    completeness_score: float
    confidence_level: float
    issues: List[str]
    strengths: List[str]


class ContentQualityAnalyzer:
    """Analyze content quality based on various factors."""
    
    def __init__(self):
        # Patterns that indicate low quality content
        self.low_quality_patterns = [
            r'^(yes|no|ok|okay|thanks?|thx)\.?$',
            r'^(me too|same here|agreed?|exactly|\+1|this)\.?$',
            r'^(lol|haha|lmao|rofl|lmfao)\.?$',
            r'^(first|second|third)\.?$',
            r'^\d+\.?$',
            r'^[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]+$',
        ]
        
        # Patterns that indicate high quality content
        self.high_quality_indicators = [
            r'\b(analysis|research|study|data|statistics|evidence)\b',
            r'\b(solution|approach|method|strategy|framework)\b',
            r'\b(experience|expertise|professional|industry)\b',
            r'\b(detailed|comprehensive|thorough|extensive)\b',
            r'\b(example|case study|implementation|results)\b',
        ]
        
        # Spam indicators
        self.spam_indicators = [
            r'\b(buy now|click here|limited time|act now|free trial)\b',
            r'\b(make money|earn \$|guaranteed|risk free)\b',
            r'\b(viagra|cialis|pharmacy|casino|lottery)\b',
            r'(https?://)?[a-z0-9-]+\.(tk|ml|ga|cf|bit\.ly|tinyurl)',
            r'\b(subscribe|follow|like|share)\b.*\b(channel|page|profile)\b',
        ]
    
    def analyze_content_quality(self, content: str, title: str = "") -> Tuple[float, List[str], List[str]]:
        """Analyze content quality and return score, issues, and strengths."""
        if not content:
            return 0.0, ["Empty content"], []
        
        issues = []
        strengths = []
        score = 5.0  # Start with neutral score
        
        # Check content length
        content_length = len(content.strip())
        if content_length < 10:
            issues.append("Content too short")
            score -= 3.0
        elif content_length < 50:
            issues.append("Content very short")
            score -= 1.5
        elif 100 <= content_length <= 2000:
            strengths.append("Good content length")
            score += 1.0
        elif content_length > 5000:
            issues.append("Content very long")
            score -= 0.5
        
        # Check for low quality patterns
        content_lower = content.lower()
        for pattern in self.low_quality_patterns:
            if re.match(pattern, content_lower.strip()):
                issues.append("Low quality content pattern")
                score -= 2.0
                break
        
        # Check for spam indicators
        spam_count = 0
        for pattern in self.spam_indicators:
            if re.search(pattern, content_lower):
                spam_count += 1
        
        if spam_count > 0:
            issues.append(f"Spam indicators detected ({spam_count})")
            score -= spam_count * 2.0
        
        # Check for high quality indicators
        quality_indicators = 0
        for pattern in self.high_quality_indicators:
            if re.search(pattern, content_lower):
                quality_indicators += 1
        
        if quality_indicators > 0:
            strengths.append(f"Quality indicators present ({quality_indicators})")
            score += quality_indicators * 0.5
        
        # Check sentence structure
        sentences = re.split(r'[.!?]+', content)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        
        if len(valid_sentences) >= 2:
            strengths.append("Well-structured content")
            score += 0.5
        elif len(valid_sentences) == 0:
            issues.append("No complete sentences")
            score -= 1.0
        
        # Check for excessive capitalization
        if content.isupper() and len(content) > 20:
            issues.append("Excessive capitalization")
            score -= 1.0
        
        # Check for excessive punctuation
        punct_ratio = sum(1 for c in content if c in '!?.,;:') / max(len(content), 1)
        if punct_ratio > 0.2:
            issues.append("Excessive punctuation")
            score -= 1.0
        
        # Check word diversity
        words = re.findall(r'\b\w+\b', content_lower)
        if len(words) > 10:
            unique_words = set(words)
            diversity_ratio = len(unique_words) / len(words)
            if diversity_ratio < 0.3:
                issues.append("Low word diversity")
                score -= 1.0
            elif diversity_ratio > 0.7:
                strengths.append("Good word diversity")
                score += 0.5
        
        # Check for coherence (basic)
        if title and content:
            title_words = set(re.findall(r'\b\w+\b', title.lower()))
            content_words = set(re.findall(r'\b\w+\b', content_lower))
            
            if title_words and content_words:
                overlap = len(title_words.intersection(content_words))
                if overlap > 0:
                    strengths.append("Title-content coherence")
                    score += 0.5
        
        return max(0.0, min(10.0, score)), issues, strengths


class EngagementQualityAnalyzer:
    """Analyze engagement quality based on metrics."""
    
    def analyze_engagement_quality(self, raw_data: RawData) -> Tuple[float, List[str], List[str]]:
        """Analyze engagement quality and return score, issues, and strengths."""
        issues = []
        strengths = []
        score = 5.0  # Start with neutral score
        
        upvotes = raw_data.upvotes or 0
        downvotes = raw_data.downvotes or 0
        comments = raw_data.comments_count or 0
        views = raw_data.views_count or 0
        
        # Calculate engagement ratios
        total_votes = upvotes + downvotes
        upvote_ratio = upvotes / max(total_votes, 1)
        
        # Analyze vote patterns
        if total_votes == 0:
            issues.append("No voting engagement")
            score -= 1.0
        elif upvote_ratio >= 0.8:
            strengths.append("High upvote ratio")
            score += 2.0
        elif upvote_ratio >= 0.6:
            strengths.append("Good upvote ratio")
            score += 1.0
        elif upvote_ratio < 0.3:
            issues.append("Low upvote ratio")
            score -= 2.0
        
        # Analyze comment engagement
        if comments == 0:
            issues.append("No comment engagement")
            score -= 0.5
        elif comments >= 10:
            strengths.append("High comment engagement")
            score += 1.5
        elif comments >= 5:
            strengths.append("Good comment engagement")
            score += 1.0
        
        # Analyze view engagement (if available)
        if views > 0:
            if comments > 0:
                comment_rate = comments / views
                if comment_rate > 0.01:  # 1% comment rate
                    strengths.append("High comment rate")
                    score += 1.0
            
            if total_votes > 0:
                vote_rate = total_votes / views
                if vote_rate > 0.05:  # 5% vote rate
                    strengths.append("High vote rate")
                    score += 0.5
        
        # Check for suspicious patterns
        if upvotes > 0 and downvotes == 0 and upvotes > 100:
            issues.append("Suspicious vote pattern")
            score -= 1.0
        
        if comments > upvotes * 2 and upvotes > 0:
            issues.append("Unusual comment-to-vote ratio")
            score -= 0.5
        
        return max(0.0, min(10.0, score)), issues, strengths


class SourceCredibilityAnalyzer:
    """Analyze source credibility and author reputation."""
    
    def __init__(self):
        # Trusted source patterns
        self.trusted_sources = {
            'reddit': {
                'high_credibility': ['MachineLearning', 'science', 'AskScience', 'programming'],
                'medium_credibility': ['technology', 'startups', 'entrepreneur'],
                'low_credibility': ['memes', 'funny', 'pics']
            },
            'github': {
                'high_credibility': ['microsoft', 'google', 'facebook', 'tensorflow', 'pytorch'],
                'medium_credibility': [],
                'low_credibility': []
            }
        }
    
    def analyze_source_credibility(self, raw_data: RawData) -> Tuple[float, List[str], List[str]]:
        """Analyze source credibility and return score, issues, and strengths."""
        issues = []
        strengths = []
        score = 5.0  # Start with neutral score
        
        source = raw_data.source.lower()
        author = raw_data.author or ""
        author_reputation = raw_data.author_reputation or 0
        
        # Analyze source platform
        if source in ['reddit', 'github', 'stackoverflow']:
            strengths.append("Reputable platform")
            score += 1.0
        elif source in ['twitter', 'linkedin']:
            score += 0.5
        else:
            issues.append("Unknown source platform")
            score -= 0.5
        
        # Analyze subreddit/repository credibility (if available)
        metadata = raw_data.metadata or {}
        
        if source == 'reddit' and 'subreddit' in metadata:
            subreddit = metadata['subreddit'].lower()
            if subreddit in self.trusted_sources['reddit']['high_credibility']:
                strengths.append("High credibility subreddit")
                score += 2.0
            elif subreddit in self.trusted_sources['reddit']['medium_credibility']:
                strengths.append("Medium credibility subreddit")
                score += 1.0
            elif subreddit in self.trusted_sources['reddit']['low_credibility']:
                issues.append("Low credibility subreddit")
                score -= 1.0
        
        if source == 'github' and 'repository' in metadata:
            repo = metadata['repository'].lower()
            for trusted_org in self.trusted_sources['github']['high_credibility']:
                if trusted_org in repo:
                    strengths.append("Trusted organization repository")
                    score += 2.0
                    break
        
        # Analyze author reputation
        if author_reputation > 0:
            if author_reputation >= 1000:
                strengths.append("High author reputation")
                score += 1.5
            elif author_reputation >= 100:
                strengths.append("Good author reputation")
                score += 1.0
            elif author_reputation >= 10:
                score += 0.5
        else:
            issues.append("No author reputation data")
            score -= 0.5
        
        # Check for suspicious author patterns
        if author:
            if re.match(r'^[a-z]+\d+$', author.lower()):
                issues.append("Generic username pattern")
                score -= 0.5
            
            if len(author) < 3:
                issues.append("Very short username")
                score -= 0.5
        else:
            issues.append("Anonymous author")
            score -= 1.0
        
        return max(0.0, min(10.0, score)), issues, strengths


class RelevanceAnalyzer:
    """Analyze relevance to AI opportunities."""
    
    def __init__(self):
        # AI and technology keywords with weights
        self.ai_keywords = {
            'artificial intelligence': 3.0, 'ai': 2.0, 'machine learning': 3.0, 'ml': 2.0,
            'deep learning': 3.0, 'neural network': 2.5, 'algorithm': 2.0, 'automation': 2.5,
            'nlp': 2.0, 'computer vision': 2.5, 'data science': 2.0, 'predictive': 2.0,
            'classification': 1.5, 'clustering': 1.5, 'recommendation': 2.0, 'chatbot': 2.0,
            'voice assistant': 2.0, 'image recognition': 2.0, 'sentiment analysis': 2.0
        }
        
        # Opportunity keywords with weights
        self.opportunity_keywords = {
            'pain point': 3.0, 'frustrating': 2.0, 'time consuming': 2.5, 'manual process': 2.5,
            'repetitive task': 2.0, 'inefficient': 2.0, 'bottleneck': 2.0, 'feature request': 2.5,
            'enhancement': 2.0, 'improvement': 2.0, 'wish there was': 2.5, 'need a tool': 2.5,
            'looking for solution': 2.5, 'automate': 2.0, 'optimize': 2.0, 'streamline': 2.0,
            'market gap': 3.0, 'opportunity': 2.5, 'business idea': 2.5, 'startup idea': 2.5,
            'unmet need': 2.5, 'problem to solve': 2.0
        }
    
    def analyze_relevance(self, raw_data: RawData) -> Tuple[float, List[str], List[str]]:
        """Analyze relevance to AI opportunities and return score, issues, and strengths."""
        issues = []
        strengths = []
        score = 0.0  # Start with zero, build up based on relevance
        
        content = f"{raw_data.title or ''} {raw_data.content}".lower()
        
        # Check for AI keywords
        ai_score = 0.0
        ai_matches = []
        for keyword, weight in self.ai_keywords.items():
            if keyword in content:
                ai_score += weight
                ai_matches.append(keyword)
        
        if ai_matches:
            strengths.append(f"AI keywords found: {', '.join(ai_matches[:3])}")
            score += min(ai_score, 10.0)  # Cap AI score contribution
        
        # Check for opportunity keywords
        opp_score = 0.0
        opp_matches = []
        for keyword, weight in self.opportunity_keywords.items():
            if keyword in content:
                opp_score += weight
                opp_matches.append(keyword)
        
        if opp_matches:
            strengths.append(f"Opportunity keywords found: {', '.join(opp_matches[:3])}")
            score += min(opp_score, 10.0)  # Cap opportunity score contribution
        
        # Bonus for having both AI and opportunity keywords
        if ai_matches and opp_matches:
            strengths.append("Both AI and opportunity indicators present")
            score += 2.0
        
        # Check for technical depth
        technical_indicators = [
            'implementation', 'architecture', 'framework', 'library', 'api',
            'model', 'training', 'dataset', 'performance', 'accuracy'
        ]
        
        tech_matches = [indicator for indicator in technical_indicators if indicator in content]
        if tech_matches:
            strengths.append("Technical depth indicators")
            score += len(tech_matches) * 0.5
        
        # Penalize if no relevant keywords found
        if not ai_matches and not opp_matches:
            issues.append("No AI or opportunity keywords found")
            score = max(score - 5.0, 0.0)
        
        return max(0.0, min(10.0, score)), issues, strengths


class FreshnessAnalyzer:
    """Analyze content freshness and timeliness."""
    
    def analyze_freshness(self, raw_data: RawData) -> Tuple[float, List[str], List[str]]:
        """Analyze content freshness and return score, issues, and strengths."""
        issues = []
        strengths = []
        score = 5.0  # Start with neutral score
        
        if not raw_data.extracted_at:
            issues.append("No extraction timestamp")
            return 3.0, issues, strengths
        
        now = datetime.now()
        age = now - raw_data.extracted_at
        age_hours = age.total_seconds() / 3600
        age_days = age.days
        
        # Score based on age
        if age_hours < 1:
            strengths.append("Very fresh content (< 1 hour)")
            score += 3.0
        elif age_hours < 24:
            strengths.append("Fresh content (< 1 day)")
            score += 2.0
        elif age_days < 7:
            strengths.append("Recent content (< 1 week)")
            score += 1.0
        elif age_days < 30:
            score += 0.5
        elif age_days < 90:
            issues.append("Somewhat old content (> 1 month)")
            score -= 0.5
        elif age_days < 365:
            issues.append("Old content (> 3 months)")
            score -= 1.0
        else:
            issues.append("Very old content (> 1 year)")
            score -= 2.0
        
        return max(0.0, min(10.0, score)), issues, strengths


class CompletenessAnalyzer:
    """Analyze data completeness."""
    
    def analyze_completeness(self, raw_data: RawData) -> Tuple[float, List[str], List[str]]:
        """Analyze data completeness and return score, issues, and strengths."""
        issues = []
        strengths = []
        score = 0.0
        total_fields = 0
        complete_fields = 0
        
        # Check required fields
        required_fields = [
            ('source', raw_data.source),
            ('source_id', raw_data.source_id),
            ('content', raw_data.content),
            ('extracted_at', raw_data.extracted_at)
        ]
        
        for field_name, field_value in required_fields:
            total_fields += 1
            if field_value:
                complete_fields += 1
            else:
                issues.append(f"Missing {field_name}")
        
        # Check optional but valuable fields
        optional_fields = [
            ('title', raw_data.title),
            ('author', raw_data.author),
            ('source_url', raw_data.source_url),
            ('upvotes', raw_data.upvotes),
            ('comments_count', raw_data.comments_count)
        ]
        
        for field_name, field_value in optional_fields:
            total_fields += 1
            if field_value is not None:
                complete_fields += 1
                if field_name in ['title', 'author', 'source_url']:
                    strengths.append(f"Has {field_name}")
        
        # Calculate completeness score
        completeness_ratio = complete_fields / total_fields
        score = completeness_ratio * 10.0
        
        if completeness_ratio >= 0.9:
            strengths.append("Highly complete data")
        elif completeness_ratio >= 0.7:
            strengths.append("Good data completeness")
        elif completeness_ratio < 0.5:
            issues.append("Low data completeness")
        
        return score, issues, strengths


class QualityScorer:
    """Main quality scoring system."""
    
    def __init__(self):
        self.content_analyzer = ContentQualityAnalyzer()
        self.engagement_analyzer = EngagementQualityAnalyzer()
        self.source_analyzer = SourceCredibilityAnalyzer()
        self.relevance_analyzer = RelevanceAnalyzer()
        self.freshness_analyzer = FreshnessAnalyzer()
        self.completeness_analyzer = CompletenessAnalyzer()
        
        # Weights for different quality aspects
        self.weights = {
            'content_quality': 0.25,
            'engagement_quality': 0.15,
            'source_credibility': 0.15,
            'relevance_score': 0.30,
            'freshness_score': 0.10,
            'completeness_score': 0.05
        }
    
    def calculate_quality_score(self, raw_data: RawData) -> QualityMetrics:
        """Calculate comprehensive quality score for raw data."""
        all_issues = []
        all_strengths = []
        
        # Analyze each quality aspect
        content_quality, content_issues, content_strengths = self.content_analyzer.analyze_content_quality(
            raw_data.content, raw_data.title or ""
        )
        all_issues.extend([f"Content: {issue}" for issue in content_issues])
        all_strengths.extend([f"Content: {strength}" for strength in content_strengths])
        
        engagement_quality, engagement_issues, engagement_strengths = self.engagement_analyzer.analyze_engagement_quality(raw_data)
        all_issues.extend([f"Engagement: {issue}" for issue in engagement_issues])
        all_strengths.extend([f"Engagement: {strength}" for strength in engagement_strengths])
        
        source_credibility, source_issues, source_strengths = self.source_analyzer.analyze_source_credibility(raw_data)
        all_issues.extend([f"Source: {issue}" for issue in source_issues])
        all_strengths.extend([f"Source: {strength}" for strength in source_strengths])
        
        relevance_score, relevance_issues, relevance_strengths = self.relevance_analyzer.analyze_relevance(raw_data)
        all_issues.extend([f"Relevance: {issue}" for issue in relevance_issues])
        all_strengths.extend([f"Relevance: {strength}" for strength in relevance_strengths])
        
        freshness_score, freshness_issues, freshness_strengths = self.freshness_analyzer.analyze_freshness(raw_data)
        all_issues.extend([f"Freshness: {issue}" for issue in freshness_issues])
        all_strengths.extend([f"Freshness: {strength}" for strength in freshness_strengths])
        
        completeness_score, completeness_issues, completeness_strengths = self.completeness_analyzer.analyze_completeness(raw_data)
        all_issues.extend([f"Completeness: {issue}" for issue in completeness_issues])
        all_strengths.extend([f"Completeness: {strength}" for strength in completeness_strengths])
        
        # Calculate weighted overall score
        overall_score = (
            content_quality * self.weights['content_quality'] +
            engagement_quality * self.weights['engagement_quality'] +
            source_credibility * self.weights['source_credibility'] +
            relevance_score * self.weights['relevance_score'] +
            freshness_score * self.weights['freshness_score'] +
            completeness_score * self.weights['completeness_score']
        )
        
        # Determine quality level
        if overall_score >= 8.0:
            quality_level = QualityLevel.EXCELLENT
        elif overall_score >= 6.5:
            quality_level = QualityLevel.GOOD
        elif overall_score >= 4.5:
            quality_level = QualityLevel.FAIR
        elif overall_score >= 2.0:
            quality_level = QualityLevel.POOR
        else:
            quality_level = QualityLevel.REJECTED
        
        # Calculate confidence level
        confidence_level = self._calculate_confidence(
            content_quality, engagement_quality, source_credibility,
            relevance_score, freshness_score, completeness_score
        )
        
        return QualityMetrics(
            overall_score=overall_score,
            quality_level=quality_level,
            content_quality=content_quality,
            engagement_quality=engagement_quality,
            source_credibility=source_credibility,
            relevance_score=relevance_score,
            freshness_score=freshness_score,
            completeness_score=completeness_score,
            confidence_level=confidence_level,
            issues=all_issues,
            strengths=all_strengths
        )
    
    def _calculate_confidence(self, *scores) -> float:
        """Calculate confidence level based on score consistency."""
        if not scores:
            return 0.0
        
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = math.sqrt(variance)
        
        # Lower standard deviation = higher confidence
        confidence = max(0.0, 1.0 - (std_dev / 5.0))  # Normalize to 0-1
        
        return confidence


# Task queue integration functions
async def quality_scoring_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Task handler for quality scoring."""
    try:
        # Extract raw data from payload
        raw_data_dict = payload.get('raw_data')
        if not raw_data_dict:
            raise ValueError("No raw data provided")
        
        raw_data = RawData(**raw_data_dict)
        
        # Calculate quality score
        scorer = QualityScorer()
        quality_metrics = scorer.calculate_quality_score(raw_data)
        
        return {
            'success': True,
            'quality_metrics': {
                'overall_score': quality_metrics.overall_score,
                'quality_level': quality_metrics.quality_level,
                'content_quality': quality_metrics.content_quality,
                'engagement_quality': quality_metrics.engagement_quality,
                'source_credibility': quality_metrics.source_credibility,
                'relevance_score': quality_metrics.relevance_score,
                'freshness_score': quality_metrics.freshness_score,
                'completeness_score': quality_metrics.completeness_score,
                'confidence_level': quality_metrics.confidence_level,
                'issues': quality_metrics.issues,
                'strengths': quality_metrics.strengths
            },
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Quality scoring task failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'processed_at': datetime.now().isoformat()
        }


async def batch_quality_scoring_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Task handler for batch quality scoring."""
    try:
        # Extract raw data list from payload
        raw_data_list = payload.get('raw_data_list', [])
        if not raw_data_list:
            raise ValueError("No raw data list provided")
        
        # Convert to RawData objects
        raw_data_objects = [RawData(**item) for item in raw_data_list]
        
        # Score each item
        scorer = QualityScorer()
        results = []
        
        for raw_data in raw_data_objects:
            quality_metrics = scorer.calculate_quality_score(raw_data)
            results.append({
                'data_id': f"{raw_data.source}:{raw_data.source_id}",
                'quality_metrics': {
                    'overall_score': quality_metrics.overall_score,
                    'quality_level': quality_metrics.quality_level,
                    'content_quality': quality_metrics.content_quality,
                    'engagement_quality': quality_metrics.engagement_quality,
                    'source_credibility': quality_metrics.source_credibility,
                    'relevance_score': quality_metrics.relevance_score,
                    'freshness_score': quality_metrics.freshness_score,
                    'completeness_score': quality_metrics.completeness_score,
                    'confidence_level': quality_metrics.confidence_level,
                    'issues': quality_metrics.issues,
                    'strengths': quality_metrics.strengths
                }
            })
        
        # Calculate batch statistics
        scores = [result['quality_metrics']['overall_score'] for result in results]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        quality_distribution = {}
        for result in results:
            level = result['quality_metrics']['quality_level']
            quality_distribution[level] = quality_distribution.get(level, 0) + 1
        
        return {
            'success': True,
            'input_count': len(raw_data_objects),
            'results': results,
            'batch_statistics': {
                'average_score': avg_score,
                'quality_distribution': quality_distribution,
                'high_quality_count': sum(1 for score in scores if score >= 6.5),
                'low_quality_count': sum(1 for score in scores if score < 4.5)
            },
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch quality scoring task failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'processed_at': datetime.now().isoformat()
        }