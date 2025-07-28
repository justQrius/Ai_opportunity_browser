"""Data ingestion service package for AI Opportunity Browser.

This package provides a comprehensive data ingestion system with:
- Plugin-based architecture for multiple data sources
- Async task queue for processing pipeline
- Data cleaning and normalization
- Duplicate detection and deduplication
- Quality scoring and assessment

Main components:
- PluginManager: Manages data source plugins
- TaskQueue: Handles async processing tasks
- DataNormalizer: Cleans and normalizes raw data
- DuplicateDetector: Identifies and handles duplicates
- QualityScorer: Assesses data quality

Usage:
    from data_ingestion import DataIngestionService
    
    service = DataIngestionService()
    await service.initialize()
    
    # Ingest data from all sources
    await service.ingest_all_sources()
"""

from .plugin_manager import PluginManager, plugin_manager
from .processing.task_queue import TaskQueue, task_queue
from .processing.data_cleaning import DataNormalizer, clean_data_task, batch_clean_data_task
from .processing.duplicate_detection import DeduplicationService, detect_duplicates_task, batch_deduplicate_task
from .processing.quality_scoring import QualityScorer, quality_scoring_task, batch_quality_scoring_task
from .service import DataIngestionService

__all__ = [
    'PluginManager',
    'plugin_manager',
    'TaskQueue', 
    'task_queue',
    'DataNormalizer',
    'DeduplicationService',
    'QualityScorer',
    'DataIngestionService'
]