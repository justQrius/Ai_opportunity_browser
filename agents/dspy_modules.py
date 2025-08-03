import dspy
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import data ingestion services
try:
    from data_ingestion.service import DataIngestionService
    from data_ingestion.plugin_manager import PluginManager
    from shared.database import get_db_session
    from shared.models.market_signal import MarketSignal
    DATA_INGESTION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Data ingestion services not available: {e}")
    DATA_INGESTION_AVAILABLE = False
    DataIngestionService = None
    PluginManager = None

class MarketResearchSignature(dspy.Signature):
    """
    Conducts market research for a given topic using real data from ingestion sources.
    Integrates with Reddit discussions, GitHub issues, and other market signals.
    """
    topic = dspy.InputField(desc="The high-level topic for market research")
    real_market_data = dspy.InputField(desc="Actual market signals from data ingestion (Reddit, GitHub, etc.)")
    market_research_report = dspy.OutputField(desc="A detailed report analyzing real market data, trends, and opportunities")

class CompetitiveAnalysisSignature(dspy.Signature):
    """
    Analyzes the competitive landscape based on market research and real market signals.
    """
    market_research_report = dspy.InputField(desc="The market research report with real data analysis")
    competitive_signals = dspy.InputField(desc="Competitive intelligence from market signals")
    competitive_analysis = dspy.OutputField(desc="Analysis of competitors, positioning, and market gaps")

class SynthesisSignature(dspy.Signature):
    """
    Synthesizes market research and competitive analysis into a concrete, actionable AI opportunity.
    """
    market_research_report = dspy.InputField(desc="The market research report based on real data")
    competitive_analysis = dspy.InputField(desc="The competitive analysis with market positioning")
    market_validation_data = dspy.InputField(desc="Supporting validation data from market signals")
    ai_opportunity = dspy.OutputField(desc="A specific, well-defined AI opportunity with solution and target users")

class OpportunityAnalysisPipeline(dspy.Module):
    """
    A declarative pipeline for identifying AI opportunities using real market data.
    Integrates with the data ingestion system to use actual Reddit, GitHub, and other sources.
    """
    def __init__(self, data_ingestion_service: Optional[DataIngestionService] = None):
        super().__init__()
        self.market_research = dspy.Predict(MarketResearchSignature)
        self.competitive_analysis = dspy.Predict(CompetitiveAnalysisSignature)
        self.synthesis = dspy.Predict(SynthesisSignature)
        
        # Initialize data ingestion service if available
        self.data_available = DATA_INGESTION_AVAILABLE
        if self.data_available:
            self.data_service = data_ingestion_service or DataIngestionService()
            self.plugin_manager = PluginManager()
            logger.info("OpportunityAnalysisPipeline initialized with data-aware DSPy modules")
        else:
            self.data_service = None
            self.plugin_manager = None
            logger.warning("OpportunityAnalysisPipeline initialized WITHOUT data integration (imports failed)")

    async def fetch_real_market_data(self, topic: str) -> Dict[str, Any]:
        """
        Fetch real market data from ingestion sources (Reddit, GitHub, etc.)
        """
        logger.info(f"Fetching real market data for topic: {topic}")
        
        if not self.data_available:
            logger.warning("Data ingestion not available, returning mock data")
            return {
                'topic': topic,
                'signal_count': 0,
                'data_sources': ['mock'],
                'pain_points': [],
                'feature_requests': [],
                'market_discussions': [],
                'competitive_mentions': [],
                'engagement_metrics': {'total_upvotes': 0, 'total_comments': 0, 'avg_sentiment': 0.0},
                'note': 'Data ingestion services not available - using mock data'
            }
        
        try:
            # Search for market signals related to the topic
            async with get_db_session() as session:
                # Query recent market signals related to the topic
                from sqlalchemy import and_, or_, text
                query = text("""
                    SELECT * FROM market_signals 
                    WHERE 
                        (LOWER(title) LIKE :topic_pattern 
                         OR LOWER(content) LIKE :topic_pattern
                         OR :topic_keyword = ANY(keywords))
                    AND extracted_at >= :recent_date
                    ORDER BY ai_relevance_score DESC, upvotes DESC
                    LIMIT 50
                """)
                
                recent_date = datetime.now() - timedelta(days=30)
                topic_pattern = f"%{topic.lower()}%"
                topic_keyword = topic.lower().replace(" ", "-")
                
                result = await session.execute(query, {
                    'topic_pattern': topic_pattern,
                    'topic_keyword': topic_keyword,
                    'recent_date': recent_date
                })
                
                market_signals = result.fetchall()
                
                # Format the data for DSPy analysis
                formatted_data = {
                    'topic': topic,
                    'signal_count': len(market_signals),
                    'data_sources': [],
                    'pain_points': [],
                    'feature_requests': [],
                    'market_discussions': [],
                    'competitive_mentions': [],
                    'engagement_metrics': {
                        'total_upvotes': 0,
                        'total_comments': 0,
                        'avg_sentiment': 0.0
                    }
                }
                
                for signal in market_signals:
                    signal_data = {
                        'source': signal.source,
                        'title': signal.title,
                        'content': signal.content[:500],  # Truncate for processing
                        'upvotes': signal.upvotes or 0,
                        'comments': signal.comments_count or 0,
                        'signal_type': signal.signal_type.value if signal.signal_type else 'discussion',
                        'author_reputation': signal.author_reputation or 0,
                        'url': signal.source_url
                    }
                    
                    # Categorize signals
                    if signal.signal_type and 'pain' in signal.signal_type.value.lower():
                        formatted_data['pain_points'].append(signal_data)
                    elif signal.signal_type and 'feature' in signal.signal_type.value.lower():
                        formatted_data['feature_requests'].append(signal_data)
                    else:
                        formatted_data['market_discussions'].append(signal_data)
                    
                    # Track data sources
                    if signal.source not in formatted_data['data_sources']:
                        formatted_data['data_sources'].append(signal.source)
                    
                    # Aggregate engagement metrics
                    formatted_data['engagement_metrics']['total_upvotes'] += signal.upvotes or 0
                    formatted_data['engagement_metrics']['total_comments'] += signal.comments_count or 0
                
                # Calculate averages
                if len(market_signals) > 0:
                    formatted_data['engagement_metrics']['avg_upvotes'] = formatted_data['engagement_metrics']['total_upvotes'] / len(market_signals)
                    formatted_data['engagement_metrics']['avg_comments'] = formatted_data['engagement_metrics']['total_comments'] / len(market_signals)
                
                logger.info(f"Retrieved {len(market_signals)} market signals from {len(formatted_data['data_sources'])} sources")
                return formatted_data
                
        except Exception as e:
            logger.error(f"Error fetching real market data: {e}")
            # Return empty data structure if database fails
            return {
                'topic': topic,
                'signal_count': 0,
                'data_sources': [],
                'pain_points': [],
                'feature_requests': [],
                'market_discussions': [],
                'competitive_mentions': [],
                'engagement_metrics': {'total_upvotes': 0, 'total_comments': 0, 'avg_sentiment': 0.0},
                'error': str(e)
            }

    def forward(self, topic: str, real_market_data: Optional[Dict[str, Any]] = None):
        """
        Execute the DSPy pipeline with real market data integration
        """
        logger.info(f"Starting data-aware DSPy pipeline for topic: {topic}")
        
        # Use provided data or indicate it needs to be fetched
        market_data = real_market_data or {"note": "Real market data should be fetched before calling forward()"}
        
        # 1. Conduct market research using real data
        research = self.market_research(
            topic=topic,
            real_market_data=str(market_data)
        )

        # Extract competitive signals from market data
        competitive_signals = {
            'competitors_mentioned': market_data.get('competitive_mentions', []),
            'market_gaps': market_data.get('pain_points', []),
            'solution_attempts': market_data.get('feature_requests', []),
            'engagement_data': market_data.get('engagement_metrics', {})
        }

        # 2. Perform competitive analysis
        analysis = self.competitive_analysis(
            market_research_report=research.market_research_report,
            competitive_signals=str(competitive_signals)
        )

        # 3. Synthesize the final opportunity with validation data
        validation_data = {
            'signal_count': market_data.get('signal_count', 0),
            'data_sources': market_data.get('data_sources', []),
            'engagement_metrics': market_data.get('engagement_metrics', {}),
            'pain_point_intensity': len(market_data.get('pain_points', [])),
            'feature_demand': len(market_data.get('feature_requests', []))
        }

        opportunity = self.synthesis(
            market_research_report=research.market_research_report,
            competitive_analysis=analysis.competitive_analysis,
            market_validation_data=str(validation_data)
        )

        logger.info("Data-aware DSPy pipeline completed successfully")
        return opportunity
