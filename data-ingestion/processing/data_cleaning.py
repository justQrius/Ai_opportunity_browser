"""Data cleaning and normalization utilities for market signals."""

import re
import html
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import logging

try:
    from ..plugins.base import RawData
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from plugins.base import RawData


logger = logging.getLogger(__name__)


class TextCleaner:
    """Text cleaning and normalization utilities."""
    
    def __init__(self):
        # Common spam patterns
        self.spam_patterns = [
            r'\b(?:buy|sell|cheap|discount|offer|deal|price|money|cash|free|win|winner|prize)\b.*\b(?:now|today|click|visit|link|website)\b',
            r'\b(?:viagra|cialis|pharmacy|pills|medication|drugs)\b',
            r'\b(?:casino|gambling|poker|lottery|jackpot)\b',
            r'\b(?:loan|credit|debt|mortgage|insurance)\b.*\b(?:approved|guaranteed|instant)\b',
            r'(?:https?://)?(?:bit\.ly|tinyurl|t\.co|goo\.gl|short\.link)',
            r'\b(?:subscribe|follow|like|share)\b.*\b(?:channel|page|profile)\b',
        ]
        
        # Noise patterns to remove
        self.noise_patterns = [
            r'\[deleted\]',
            r'\[removed\]',
            r'\[edit:.*?\]',
            r'edit\s*:.*?(?=\n|$)',
            r'update\s*:.*?(?=\n|$)',
            r'tldr\s*:.*?(?=\n|$)',
            r'tl;dr\s*:.*?(?=\n|$)',
        ]
        
        # Common stop words for content analysis
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'would', 'could', 'should', 'can',
            'this', 'these', 'those', 'they', 'them', 'their', 'there', 'where',
            'when', 'why', 'how', 'what', 'who', 'which', 'i', 'you', 'we',
            'me', 'my', 'your', 'our', 'his', 'her', 'him', 'us', 'do', 'did',
            'does', 'have', 'had', 'been', 'being', 'get', 'got', 'go', 'went',
            'come', 'came', 'see', 'saw', 'know', 'knew', 'think', 'thought',
            'say', 'said', 'tell', 'told', 'ask', 'asked', 'give', 'gave',
            'take', 'took', 'make', 'made', 'use', 'used', 'work', 'worked',
            'want', 'wanted', 'need', 'needed', 'like', 'liked', 'look', 'looked'
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Normalize Unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        # Remove noise patterns
        for pattern in self.noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up markdown and formatting
        text = self._clean_markdown(text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def is_spam(self, text: str) -> bool:
        """Check if text appears to be spam."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check spam patterns
        for pattern in self.spam_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Check for excessive capitalization
        if len(text) > 50:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.7:
                return True
        
        # Check for excessive punctuation
        punct_ratio = sum(1 for c in text if c in '!?.,;:') / max(len(text), 1)
        if punct_ratio > 0.3:
            return True
        
        # Check for excessive URLs
        url_count = len(re.findall(r'https?://\S+', text))
        if url_count > 3:
            return True
        
        return False
    
    def is_low_quality(self, text: str) -> bool:
        """Check if text is low quality or not informative."""
        if not text:
            return True
        
        # Too short
        if len(text.strip()) < 20:
            return True
        
        # Too repetitive
        words = text.lower().split()
        if len(set(words)) < len(words) * 0.3:  # Less than 30% unique words
            return True
        
        # Mostly stop words
        content_words = [w for w in words if w not in self.stop_words and len(w) > 2]
        if len(content_words) < len(words) * 0.2:  # Less than 20% content words
            return True
        
        # Check for common low-quality patterns
        low_quality_patterns = [
            r'^(yes|no|ok|okay|thanks|thank you)\.?$',
            r'^(me too|same here|agreed?|exactly)\.?$',
            r'^(lol|haha|lmao|rofl)\.?$',
            r'^\+1\.?$',
            r'^this\.?$',
        ]
        
        text_lower = text.lower().strip()
        for pattern in low_quality_patterns:
            if re.match(pattern, text_lower):
                return True
        
        return False
    
    def extract_keywords(self, text: str, min_length: int = 3, max_keywords: int = 20) -> List[str]:
        """Extract meaningful keywords from text."""
        if not text:
            return []
        
        # Clean and tokenize
        text = self.clean_text(text).lower()
        words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + r',}\b', text)
        
        # Remove stop words
        keywords = [w for w in words if w not in self.stop_words]
        
        # Count frequency
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:max_keywords]]
    
    def _clean_markdown(self, text: str) -> str:
        """Clean markdown formatting from text."""
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '[CODE]', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'https?://\S+', '[LINK]', text)
        
        # Remove formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
        text = re.sub(r'~~(.*?)~~', r'\1', text)      # Strikethrough
        text = re.sub(r'#{1,6}\s*', '', text)         # Headers
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # Lists
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # Numbered lists
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)  # Quotes
        
        return text


class ContentFilter:
    """Filter content based on relevance and quality criteria."""
    
    def __init__(self):
        self.text_cleaner = TextCleaner()
        
        # AI and technology related keywords
        self.ai_keywords = {
            'artificial intelligence', 'ai', 'machine learning', 'ml', 'deep learning',
            'neural network', 'algorithm', 'automation', 'nlp', 'computer vision',
            'data science', 'predictive', 'classification', 'clustering', 'recommendation',
            'chatbot', 'voice assistant', 'image recognition', 'sentiment analysis',
            'natural language processing', 'tensorflow', 'pytorch', 'scikit-learn',
            'opencv', 'transformers', 'bert', 'gpt', 'llm', 'large language model'
        }
        
        # Pain point and opportunity indicators
        self.opportunity_keywords = {
            'pain point', 'frustrating', 'time consuming', 'manual process',
            'repetitive task', 'inefficient', 'slow process', 'difficult',
            'annoying', 'tedious', 'waste of time', 'bottleneck',
            'feature request', 'enhancement', 'improvement', 'wish there was',
            'need a tool', 'looking for solution', 'automate', 'optimize',
            'streamline', 'simplify', 'faster way', 'better solution',
            'market gap', 'opportunity', 'business idea', 'startup idea',
            'untapped market', 'unmet need', 'problem to solve'
        }
    
    def is_relevant(self, raw_data: RawData) -> bool:
        """Check if content is relevant for AI opportunity detection."""
        content = f"{raw_data.title or ''} {raw_data.content}".lower()
        
        # Check for AI relevance
        ai_relevant = any(keyword in content for keyword in self.ai_keywords)
        
        # Check for opportunity indicators
        opportunity_relevant = any(keyword in content for keyword in self.opportunity_keywords)
        
        # Must have either AI relevance or opportunity indicators
        if not (ai_relevant or opportunity_relevant):
            return False
        
        # Check content quality
        if self.text_cleaner.is_spam(raw_data.content):
            return False
        
        if self.text_cleaner.is_low_quality(raw_data.content):
            return False
        
        # Check engagement threshold
        engagement_score = (
            (raw_data.upvotes or 0) + 
            (raw_data.comments_count or 0) * 2 - 
            (raw_data.downvotes or 0)
        )
        
        if engagement_score < -5:  # Heavily downvoted content
            return False
        
        return True
    
    def calculate_relevance_score(self, raw_data: RawData) -> float:
        """Calculate relevance score for content."""
        content = f"{raw_data.title or ''} {raw_data.content}".lower()
        score = 0.0
        
        # AI keyword scoring
        ai_matches = sum(1 for keyword in self.ai_keywords if keyword in content)
        score += ai_matches * 2.0
        
        # Opportunity keyword scoring
        opp_matches = sum(1 for keyword in self.opportunity_keywords if keyword in content)
        score += opp_matches * 1.5
        
        # Engagement scoring
        engagement = (
            (raw_data.upvotes or 0) * 0.1 + 
            (raw_data.comments_count or 0) * 0.2 - 
            (raw_data.downvotes or 0) * 0.1
        )
        score += max(0, engagement)
        
        # Author reputation scoring
        if raw_data.author_reputation:
            score += min(raw_data.author_reputation * 0.01, 5.0)
        
        # Content length scoring (moderate length preferred)
        content_length = len(raw_data.content)
        if 100 <= content_length <= 1000:
            score += 1.0
        elif content_length > 1000:
            score += 0.5
        
        # Recency scoring
        if raw_data.extracted_at:
            days_old = (datetime.now() - raw_data.extracted_at).days
            if days_old <= 7:
                score += 2.0
            elif days_old <= 30:
                score += 1.0
            elif days_old <= 90:
                score += 0.5
        
        return max(0.0, score)


class DataNormalizer:
    """Normalize raw data into consistent format."""
    
    def __init__(self):
        self.text_cleaner = TextCleaner()
        self.content_filter = ContentFilter()
    
    def normalize_raw_data(self, raw_data: RawData) -> Optional[RawData]:
        """Normalize raw data with cleaning and validation."""
        try:
            # Check relevance first
            if not self.content_filter.is_relevant(raw_data):
                return None
            
            # Clean content
            cleaned_content = self.text_cleaner.clean_text(raw_data.content)
            if not cleaned_content:
                return None
            
            # Clean title
            cleaned_title = self.text_cleaner.clean_text(raw_data.title or "")
            
            # Extract keywords
            keywords = self.text_cleaner.extract_keywords(cleaned_content)
            
            # Calculate relevance score
            relevance_score = self.content_filter.calculate_relevance_score(raw_data)
            
            # Create normalized data
            normalized_data = RawData(
                source=raw_data.source,
                source_id=raw_data.source_id,
                source_url=raw_data.source_url,
                title=cleaned_title,
                content=cleaned_content,
                raw_content=raw_data.raw_content,
                author=raw_data.author,
                author_reputation=raw_data.author_reputation,
                upvotes=raw_data.upvotes or 0,
                downvotes=raw_data.downvotes or 0,
                comments_count=raw_data.comments_count or 0,
                shares_count=raw_data.shares_count or 0,
                views_count=raw_data.views_count or 0,
                extracted_at=raw_data.extracted_at,
                metadata={
                    **raw_data.metadata,
                    'keywords': keywords,
                    'relevance_score': relevance_score,
                    'cleaned': True,
                    'normalized_at': datetime.now().isoformat()
                }
            )
            
            return normalized_data
            
        except Exception as e:
            logger.error(f"Error normalizing data: {e}")
            return None
    
    def batch_normalize(self, raw_data_list: List[RawData]) -> List[RawData]:
        """Normalize a batch of raw data."""
        normalized_data = []
        
        for raw_data in raw_data_list:
            normalized = self.normalize_raw_data(raw_data)
            if normalized:
                normalized_data.append(normalized)
        
        logger.info(f"Normalized {len(normalized_data)}/{len(raw_data_list)} raw data items")
        return normalized_data


# Utility functions for task queue integration
async def clean_data_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Task handler for data cleaning."""
    try:
        # Extract raw data from payload
        raw_data_dict = payload.get('raw_data')
        if not raw_data_dict:
            raise ValueError("No raw data provided")
        
        raw_data = RawData(**raw_data_dict)
        
        # Normalize data
        normalizer = DataNormalizer()
        normalized_data = normalizer.normalize_raw_data(raw_data)
        
        if normalized_data:
            return {
                'success': True,
                'normalized_data': normalized_data.dict(),
                'processed_at': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'reason': 'Data filtered out during normalization',
                'processed_at': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Data cleaning task failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'processed_at': datetime.now().isoformat()
        }


async def batch_clean_data_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Task handler for batch data cleaning."""
    try:
        # Extract raw data list from payload
        raw_data_list = payload.get('raw_data_list', [])
        if not raw_data_list:
            raise ValueError("No raw data list provided")
        
        # Convert to RawData objects
        raw_data_objects = [RawData(**item) for item in raw_data_list]
        
        # Normalize data
        normalizer = DataNormalizer()
        normalized_data = normalizer.batch_normalize(raw_data_objects)
        
        return {
            'success': True,
            'input_count': len(raw_data_objects),
            'output_count': len(normalized_data),
            'normalized_data': [item.dict() for item in normalized_data],
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch data cleaning task failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'processed_at': datetime.now().isoformat()
        }