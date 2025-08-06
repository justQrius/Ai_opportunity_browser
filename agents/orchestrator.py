import dspy
import asyncio
import os
from .custom_orchestrator import CustomOrchestrator
from .dspy_modules import OpportunityAnalysisPipeline
import logging
from api.core.config import get_settings
try:
    from data_ingestion.service import DataIngestionService
    DATA_INGESTION_AVAILABLE = True
except ImportError:
    DataIngestionService = None
    DATA_INGESTION_AVAILABLE = False

logger = logging.getLogger(__name__)

settings = get_settings()

class OpportunityOrchestrator:
    def __init__(self):
        # Initialize both approaches for comparison and fallback
        logger.info("Initializing orchestrator with proper DSPy integration and fallback")
        
        # Try to initialize proper DSPy pipeline first
        self.use_proper_dspy = False
        self.proper_pipeline = None
        self.data_service = None
        self._initialization_complete = False
        
        try:
            # Configure DSPy with Gemini (structured output may still have issues)
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                self.llm = dspy.LM(
                    model="gemini/gemini-1.5-flash",
                    api_key=gemini_key,
                    max_tokens=2048,
                    temperature=0.7
                )
                dspy.settings.configure(lm=self.llm)
                
                # Store plugin config for async initialization
                if DATA_INGESTION_AVAILABLE:
                    self.plugin_config = {
                        'plugins': {
                            'reddit': {
                                'rate_limit': 60,
                                'max_requests_per_minute': 60,
                                'timeout': 30
                            },
                            'github': {
                                'rate_limit': 60,
                                'max_requests_per_minute': 60,
                                'timeout': 30
                            },
                            'hackernews': {
                                'rate_limit': 60,
                                'max_requests_per_minute': 60,
                                'timeout': 30
                            },
                            'producthunt': {
                                'rate_limit': 60,
                                'max_requests_per_minute': 60,
                                'timeout': 30
                            },
                            'ycombinator': {
                                'rate_limit': 60,
                                'max_requests_per_minute': 60,
                                'timeout': 30
                            }
                        }
                    }
                    logger.info("📋 Plugin configuration ready for async initialization")
                else:
                    self.plugin_config = None
                    logger.warning("Data ingestion service not available")
                
                logger.info("✅ Basic DSPy configuration complete - async initialization required")
            else:
                raise ValueError("GEMINI_API_KEY not found")
                
        except Exception as e:
            logger.warning(f"Failed to initialize basic DSPy configuration: {e}")
            logger.info("Falling back to custom orchestrator")
            self.use_proper_dspy = False
        
        # Always have custom orchestrator as fallback
        self.custom_orchestrator = CustomOrchestrator()
    
    async def initialize_async(self):
        """Async initialization for data ingestion service and plugins"""
        if self._initialization_complete:
            return
            
        logger.info("🚀 Starting async initialization of data ingestion system")
        
        try:
            if self.plugin_config and DATA_INGESTION_AVAILABLE:
                # Initialize data ingestion service
                self.data_service = DataIngestionService(self.plugin_config)
                await self.data_service.initialize()
                logger.info("✅ Data ingestion service fully initialized with all 5 plugins")
                
                # Initialize the proper DSPy pipeline with data integration
                self.proper_pipeline = OpportunityAnalysisPipeline(self.data_service)
                self.use_proper_dspy = True
                
                logger.info("✅ Complete DSPy pipeline with data integration initialized successfully")
            else:
                logger.warning("No plugin configuration available for data ingestion")
                
            self._initialization_complete = True
            
        except Exception as e:
            logger.error(f"Failed to complete async initialization: {e}")
            self.use_proper_dspy = False

    async def analyze_opportunity(self, topic: str, use_real_data: bool = True):
        """
        Analyze opportunity using proper DSPy with real data integration, or fallback to custom orchestrator
        
        Args:
            topic: The topic to analyze
            use_real_data: Whether to fetch and use real market data (True for proper DSPy, False for fallback)
        """
        logger.info(f"Analyzing opportunity for topic: {topic}")
        
        # Ensure async initialization is complete
        await self.initialize_async()
        
        if self.use_proper_dspy and use_real_data and self.proper_pipeline:
            try:
                logger.info("🚀 Using properly initialized DSPy pipeline with real data integration")
                return await self._analyze_with_proper_dspy(topic)
            except Exception as e:
                logger.error(f"Proper DSPy pipeline failed: {e}")
                logger.info("Falling back to custom orchestrator")
                return await self.custom_orchestrator.analyze_opportunity(topic)
        else:
            logger.info("🔄 Using custom orchestrator (fallback mode)")
            return await self.custom_orchestrator.analyze_opportunity(topic)
    
    async def analyze_opportunity_with_data(self, topic: str) -> tuple[str, dict]:
        """
        Analyze opportunity and return both formatted result and raw market data
        
        Returns:
            tuple: (formatted_result, market_data)
        """
        logger.info(f"Analyzing opportunity with data for topic: {topic}")
        
        # Ensure async initialization is complete
        await self.initialize_async()
        
        if self.use_proper_dspy and self.proper_pipeline:
            try:
                logger.info("🚀 Using properly initialized DSPy pipeline with real data integration")
                
                # Step 1: Fetch real market data using initialized service
                real_market_data = await self.proper_pipeline.fetch_real_market_data(topic)
                logger.info(f"Retrieved {real_market_data.get('signal_count', 0)} market signals from {len(real_market_data.get('data_sources', []))} sources")
                
                # Step 2: Execute DSPy pipeline
                result = self.proper_pipeline.forward(topic, real_market_data)
                
                # Step 3: Format the result
                formatted_result = self._format_dspy_result(result, real_market_data)
                
                logger.info("✅ Proper DSPy pipeline completed successfully")
                return formatted_result, real_market_data
                
            except Exception as e:
                logger.error(f"Proper DSPy pipeline failed: {e}")
                # Return fallback with empty market data
                fallback_result = await self.custom_orchestrator.analyze_opportunity(topic)
                return fallback_result, {}
        else:
            logger.info("🔄 Using custom orchestrator (DSPy pipeline not available)")
            # Return fallback with empty market data
            fallback_result = await self.custom_orchestrator.analyze_opportunity(topic)
            return fallback_result, {}
    
    async def _analyze_with_proper_dspy(self, topic: str) -> str:
        """
        Execute the proper DSPy pipeline with real market data as specified in dspy_integration_plan.md
        """
        logger.info(f"Starting proper DSPy pipeline for topic: {topic}")
        
        try:
            # Step 1: Fetch real market data from ingestion sources
            logger.info("📊 Fetching real market data from ingestion sources (Reddit, GitHub, etc.)")
            real_market_data = await self.proper_pipeline.fetch_real_market_data(topic)
            
            logger.info(f"Retrieved {real_market_data.get('signal_count', 0)} market signals from {len(real_market_data.get('data_sources', []))} sources")
            
            # Step 2: Execute DSPy pipeline with real data
            logger.info("🔬 Executing DSPy pipeline with real market data")
            result = self.proper_pipeline.forward(topic, real_market_data)
            
            # Step 3: Format the result
            formatted_result = self._format_dspy_result(result, real_market_data)
            
            logger.info("✅ Proper DSPy pipeline completed successfully")
            return formatted_result
            
        except Exception as e:
            logger.error(f"Error in proper DSPy pipeline: {e}")
            raise
    
    def _format_dspy_result(self, dspy_result, market_data: dict) -> str:
        """
        Format the DSPy result with market data context
        """
        try:
            # Extract the AI opportunity from DSPy result
            ai_opportunity = dspy_result.ai_opportunity if hasattr(dspy_result, 'ai_opportunity') else str(dspy_result)
            
            # Add data validation footer
            data_sources = market_data.get('data_sources', [])
            signal_count = market_data.get('signal_count', 0)
            
            formatted_output = f"{ai_opportunity}\n\n--- Market Data Validation ---\n"
            formatted_output += f"Data Sources: {', '.join(data_sources) if data_sources else 'None'}\n"
            formatted_output += f"Market Signals Analyzed: {signal_count}\n"
            formatted_output += f"Pain Points Identified: {len(market_data.get('pain_points', []))}\n"
            formatted_output += f"Feature Requests Found: {len(market_data.get('feature_requests', []))}\n"
            formatted_output += f"Total Engagement: {market_data.get('engagement_metrics', {}).get('total_upvotes', 0)} upvotes, {market_data.get('engagement_metrics', {}).get('total_comments', 0)} comments\n"
            formatted_output += f"Generated using: Real market data + DSPy AI Pipeline"
            
            return formatted_output
            
        except Exception as e:
            logger.error(f"Error formatting DSPy result: {e}")
            return str(dspy_result)
