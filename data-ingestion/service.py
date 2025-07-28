"""Main data ingestion service that orchestrates all components."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict

# Use absolute imports to avoid relative import issues
from plugin_manager import PluginManager
from processing.task_queue import TaskQueue, TaskPriority
from processing.data_cleaning import DataNormalizer, clean_data_task, batch_clean_data_task
from processing.duplicate_detection import DeduplicationService, detect_duplicates_task, batch_deduplicate_task
from processing.quality_scoring import QualityScorer, quality_scoring_task, batch_quality_scoring_task
from plugins.base import RawData, PluginConfig
from plugins.reddit_plugin import RedditPlugin, RedditConfig
from plugins.github_plugin import GitHubPlugin, GitHubConfig
from shared.database import get_db_session
from shared.models.market_signal import MarketSignal, SignalType
from shared.vector_db import VectorDBService


logger = logging.getLogger(__name__)


class DataIngestionService:
    """Main service for orchestrating data ingestion pipeline."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.plugin_manager = PluginManager()
        self.task_queue = TaskQueue()
        self.data_normalizer = DataNormalizer()
        self.dedup_service = DeduplicationService()
        self.quality_scorer = QualityScorer()
        self.vector_db = VectorDBService()
        
        # Processing configuration
        self.batch_size = self.config.get('batch_size', 100)
        self.max_concurrent_tasks = self.config.get('max_concurrent_tasks', 10)
        self.quality_threshold = self.config.get('quality_threshold', 4.5)
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'total_accepted': 0,
            'total_rejected': 0,
            'total_duplicates': 0,
            'processing_errors': 0,
            'last_run': None
        }
    
    async def initialize(self) -> None:
        """Initialize all components of the data ingestion service."""
        logger.info("Initializing Data Ingestion Service")
        
        try:
            # Initialize task queue
            await self.task_queue.initialize()
            
            # Register task handlers
            self.task_queue.register_handler('clean_data', clean_data_task)
            self.task_queue.register_handler('batch_clean_data', batch_clean_data_task)
            self.task_queue.register_handler('detect_duplicates', detect_duplicates_task)
            self.task_queue.register_handler('batch_deduplicate', batch_deduplicate_task)
            self.task_queue.register_handler('quality_scoring', quality_scoring_task)
            self.task_queue.register_handler('batch_quality_scoring', batch_quality_scoring_task)
            self.task_queue.register_handler('process_raw_data', self._process_raw_data_task)
            self.task_queue.register_handler('ingest_from_source', self._ingest_from_source_task)
            
            # Start task queue workers
            await self.task_queue.start_workers(worker_count=4)
            
            # Initialize plugin manager
            await self.plugin_manager.initialize()
            
            # Initialize vector database
            await self.vector_db.initialize()
            
            # Load configured plugins
            await self._load_configured_plugins()
            
            logger.info("Data Ingestion Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Data Ingestion Service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all components gracefully."""
        logger.info("Shutting down Data Ingestion Service")
        
        try:
            await self.plugin_manager.shutdown()
            await self.task_queue.shutdown()
            await self.vector_db.shutdown()
            
            logger.info("Data Ingestion Service shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def ingest_all_sources(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ingest data from all configured sources."""
        logger.info("Starting ingestion from all sources")
        
        start_time = datetime.now()
        results = {}
        
        try:
            # Get all loaded plugins
            plugins = self.plugin_manager.list_loaded_plugins()
            
            # Create ingestion tasks for each plugin
            tasks = []
            for plugin_name in plugins:
                task_id = await self.task_queue.enqueue_task(
                    'ingest_from_source',
                    {
                        'plugin_name': plugin_name,
                        'params': params or {}
                    },
                    priority=TaskPriority.HIGH
                )
                tasks.append((plugin_name, task_id))
            
            # Wait for all ingestion tasks to complete
            for plugin_name, task_id in tasks:
                # Poll for task completion (in a real system, you'd use callbacks)
                while True:
                    task = await self.task_queue.get_task_status(task_id)
                    if task and task.status.value in ['completed', 'failed']:
                        break
                    await asyncio.sleep(1)
                
                if task and task.status.value == 'completed':
                    results[plugin_name] = {'status': 'success', 'task_id': task_id}
                else:
                    results[plugin_name] = {'status': 'failed', 'task_id': task_id, 'error': task.error if task else 'Unknown error'}
            
            # Update statistics
            self.stats['last_run'] = datetime.now()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Completed ingestion from all sources in {execution_time:.2f}s")
            
            return {
                'success': True,
                'execution_time': execution_time,
                'results': results,
                'stats': self.stats
            }
            
        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'results': results
            }
    
    async def ingest_from_plugin(self, plugin_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ingest data from a specific plugin."""
        logger.info(f"Starting ingestion from plugin: {plugin_name}")
        
        try:
            plugin = self.plugin_manager.get_plugin(plugin_name)
            if not plugin:
                raise ValueError(f"Plugin {plugin_name} not found or not loaded")
            
            # Fetch raw data from plugin
            raw_data_list = await self.plugin_manager.fetch_data_from_plugin(plugin_name, params or {})
            
            if not raw_data_list:
                logger.warning(f"No data fetched from plugin {plugin_name}")
                return {'success': True, 'processed_count': 0, 'accepted_count': 0}
            
            # Process the raw data
            result = await self._process_raw_data_batch(raw_data_list)
            
            logger.info(f"Processed {result['processed_count']} items from {plugin_name}, accepted {result['accepted_count']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error ingesting from plugin {plugin_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_raw_data(self, raw_data: RawData) -> Dict[str, Any]:
        """Process a single raw data item through the full pipeline."""
        try:
            # Step 1: Data cleaning and normalization
            normalized_data = self.data_normalizer.normalize_raw_data(raw_data)
            if not normalized_data:
                return {'success': False, 'reason': 'Failed normalization'}
            
            # Step 2: Duplicate detection
            is_duplicate, duplicates = await self.dedup_service.process_raw_data(normalized_data)
            if is_duplicate:
                return {'success': False, 'reason': 'Duplicate detected', 'duplicates': len(duplicates)}
            
            # Step 3: Quality scoring
            quality_metrics = self.quality_scorer.calculate_quality_score(normalized_data)
            if quality_metrics.overall_score < self.quality_threshold:
                return {'success': False, 'reason': 'Low quality score', 'score': quality_metrics.overall_score}
            
            # Step 4: Store in database
            market_signal = await self._create_market_signal(normalized_data, quality_metrics)
            
            # Step 5: Store in vector database for similarity search
            await self._store_in_vector_db(market_signal, normalized_data)
            
            return {
                'success': True,
                'market_signal_id': market_signal.id,
                'quality_score': quality_metrics.overall_score,
                'quality_level': quality_metrics.quality_level
            }
            
        except Exception as e:
            logger.error(f"Error processing raw data: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _process_raw_data_batch(self, raw_data_list: List[RawData]) -> Dict[str, Any]:
        """Process a batch of raw data items."""
        logger.info(f"Processing batch of {len(raw_data_list)} items")
        
        processed_count = 0
        accepted_count = 0
        rejected_count = 0
        duplicate_count = 0
        error_count = 0
        
        # Process in smaller batches to avoid overwhelming the system
        for i in range(0, len(raw_data_list), self.batch_size):
            batch = raw_data_list[i:i + self.batch_size]
            
            # Process each item in the batch
            tasks = []
            for raw_data in batch:
                task = asyncio.create_task(self.process_raw_data(raw_data))
                tasks.append(task)
            
            # Wait for batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            for result in results:
                processed_count += 1
                
                if isinstance(result, Exception):
                    error_count += 1
                    logger.error(f"Processing error: {result}")
                elif result.get('success'):
                    accepted_count += 1
                else:
                    rejected_count += 1
                    reason = result.get('reason', 'Unknown')
                    if 'duplicate' in reason.lower():
                        duplicate_count += 1
        
        # Update statistics
        self.stats['total_processed'] += processed_count
        self.stats['total_accepted'] += accepted_count
        self.stats['total_rejected'] += rejected_count
        self.stats['total_duplicates'] += duplicate_count
        self.stats['processing_errors'] += error_count
        
        return {
            'success': True,
            'processed_count': processed_count,
            'accepted_count': accepted_count,
            'rejected_count': rejected_count,
            'duplicate_count': duplicate_count,
            'error_count': error_count
        }
    
    async def _create_market_signal(self, raw_data: RawData, quality_metrics) -> MarketSignal:
        """Create and store a MarketSignal in the database."""
        async with get_db_session() as session:
            # Map signal type
            signal_type_mapping = {
                'pain_point': SignalType.PAIN_POINT,
                'feature_request': SignalType.FEATURE_REQUEST,
                'complaint': SignalType.COMPLAINT,
                'opportunity': SignalType.OPPORTUNITY,
                'trend': SignalType.TREND,
                'discussion': SignalType.DISCUSSION
            }
            
            signal_type = signal_type_mapping.get(
                raw_data.metadata.get('signal_type', 'discussion'),
                SignalType.DISCUSSION
            )
            
            # Create MarketSignal
            market_signal = MarketSignal(
                source=raw_data.source,
                source_id=raw_data.source_id,
                source_url=raw_data.source_url,
                signal_type=signal_type,
                title=raw_data.title,
                content=raw_data.content,
                raw_content=raw_data.raw_content,
                author=raw_data.author,
                author_reputation=raw_data.author_reputation,
                upvotes=raw_data.upvotes,
                downvotes=raw_data.downvotes,
                comments_count=raw_data.comments_count,
                shares_count=raw_data.shares_count,
                views_count=raw_data.views_count,
                sentiment_score=0.0,  # Will be calculated by AI agents later
                confidence_level=quality_metrics.confidence_level,
                pain_point_intensity=None,  # Will be calculated by AI agents later
                market_validation_signals=raw_data.metadata.get('validation_signals'),
                extracted_at=raw_data.extracted_at,
                processed_at=datetime.now(),
                processing_version="1.0",
                keywords=raw_data.metadata.get('keywords'),
                categories=None,  # Will be categorized by AI agents later
                ai_relevance_score=quality_metrics.relevance_score
            )
            
            session.add(market_signal)
            await session.commit()
            await session.refresh(market_signal)
            
            return market_signal
    
    async def _store_in_vector_db(self, market_signal: MarketSignal, raw_data: RawData) -> None:
        """Store market signal in vector database for similarity search."""
        try:
            # Create content for embedding
            content = f"{market_signal.title or ''}\n{market_signal.content}"
            
            # Create metadata
            metadata = {
                'id': market_signal.id,
                'source': market_signal.source,
                'signal_type': market_signal.signal_type.value,
                'author': market_signal.author,
                'created_at': market_signal.extracted_at.isoformat(),
                'quality_score': raw_data.metadata.get('relevance_score', 0),
                'keywords': raw_data.metadata.get('keywords', [])
            }
            
            # Store in vector database
            await self.vector_db.upsert(
                content,
                metadata=metadata,
                namespace="market_signals",
                id=market_signal.id
            )
            
        except Exception as e:
            logger.error(f"Error storing in vector database: {e}")
            # Don't fail the entire process if vector storage fails
    
    async def _load_configured_plugins(self) -> None:
        """Load plugins based on configuration."""
        plugin_configs = self.config.get('plugins', {})
        
        # Load Reddit plugin if configured
        if 'reddit' in plugin_configs:
            reddit_config = RedditConfig(**plugin_configs['reddit'])
            self.plugin_manager.register_plugin('reddit', RedditPlugin)
            await self.plugin_manager.load_plugin('reddit', reddit_config)
        
        # Load GitHub plugin if configured
        if 'github' in plugin_configs:
            github_config = GitHubConfig(**plugin_configs['github'])
            self.plugin_manager.register_plugin('github', GitHubPlugin)
            await self.plugin_manager.load_plugin('github', github_config)
    
    async def _ingest_from_source_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Task handler for ingesting from a specific source."""
        try:
            plugin_name = payload.get('plugin_name')
            params = payload.get('params', {})
            
            if not plugin_name:
                raise ValueError("No plugin name provided")
            
            result = await self.ingest_from_plugin(plugin_name, params)
            
            return {
                'success': result.get('success', False),
                'plugin_name': plugin_name,
                'result': result,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ingestion task failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
    
    async def _process_raw_data_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Task handler for processing raw data."""
        try:
            raw_data_dict = payload.get('raw_data')
            if not raw_data_dict:
                raise ValueError("No raw data provided")
            
            raw_data = RawData(**raw_data_dict)
            result = await self.process_raw_data(raw_data)
            
            return {
                'success': result.get('success', False),
                'result': result,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Raw data processing task failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        return {
            **self.stats,
            'plugin_stats': self.plugin_manager.get_all_plugin_status(),
            'queue_stats': self.task_queue.get_queue_stats(),
            'dedup_stats': self.dedup_service.get_stats()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health = {
            'overall': True,
            'components': {}
        }
        
        # Check plugin manager
        try:
            plugin_status = await self.plugin_manager.get_all_plugin_status()
            health['components']['plugin_manager'] = {
                'status': 'healthy',
                'plugins': plugin_status
            }
        except Exception as e:
            health['components']['plugin_manager'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['overall'] = False
        
        # Check task queue
        try:
            queue_stats = await self.task_queue.get_queue_stats()
            health['components']['task_queue'] = {
                'status': 'healthy',
                'stats': queue_stats
            }
        except Exception as e:
            health['components']['task_queue'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['overall'] = False
        
        # Check vector database
        try:
            vector_health = await self.vector_db.health_check()
            health['components']['vector_db'] = {
                'status': 'healthy' if vector_health else 'unhealthy'
            }
            if not vector_health:
                health['overall'] = False
        except Exception as e:
            health['components']['vector_db'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['overall'] = False
        
        return health