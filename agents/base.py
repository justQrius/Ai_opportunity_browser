"""
Base Agent class for the AI Opportunity Browser system.
Provides lifecycle management, state persistence, and recovery capabilities.

This module implements the agent architecture as specified in the design document,
supporting the five specialized agent types:
- MonitoringAgent: Continuous data source scanning
- AnalysisAgent: Opportunity scoring and validation
- ResearchAgent: Deep-dive context gathering
- TrendAgent: Pattern recognition and clustering
- CapabilityAgent: AI feasibility assessment
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


class AgentPriority(Enum):
    """Agent task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentTask:
    """Represents a task for an agent to execute"""
    id: str
    type: str
    data: Dict[str, Any]
    priority: AgentPriority = AgentPriority.NORMAL
    created_at: datetime = None
    scheduled_at: datetime = None
    max_retries: int = 3
    retry_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.scheduled_at is None:
            self.scheduled_at = self.created_at


@dataclass
class AgentMetrics:
    """Agent performance and health metrics"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_runtime: float = 0.0
    last_activity: datetime = None
    error_count: int = 0
    restart_count: int = 0
    
    def success_rate(self) -> float:
        """Calculate task success rate"""
        total = self.tasks_completed + self.tasks_failed
        return (self.tasks_completed / total * 100) if total > 0 else 0.0


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.
    Provides lifecycle management, state persistence, and recovery.
    """
    
    def __init__(
        self,
        agent_id: str = None,
        name: str = None,
        config: Dict[str, Any] = None,
        max_concurrent_tasks: int = 5,
        health_check_interval: int = 30
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name or self.__class__.__name__
        self.config = config or {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.health_check_interval = health_check_interval
        
        # State management
        self.state = AgentState.INITIALIZING
        self.metrics = AgentMetrics()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Set[str] = set()
        self.task_results: Dict[str, Any] = {}
        
        # Control flags
        self._shutdown_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._health_check_task: Optional[asyncio.Task] = None
        self._worker_tasks: List[asyncio.Task] = []
        
        # Error handling
        self.last_error: Optional[Exception] = None
        self.error_history: List[Dict[str, Any]] = []
        
        logger.info(f"Agent {self.name} ({self.agent_id}) initialized")
    
    async def start(self) -> None:
        """Start the agent and begin processing tasks"""
        try:
            logger.info(f"Starting agent {self.name}")
            self.state = AgentState.RUNNING
            
            # Initialize agent-specific resources
            await self.initialize()
            
            # Start health check monitoring
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            # Start worker tasks
            for i in range(self.max_concurrent_tasks):
                task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
                self._worker_tasks.append(task)
            
            logger.info(f"Agent {self.name} started successfully")
            
        except Exception as e:
            self.state = AgentState.ERROR
            self.last_error = e
            self._record_error(e, "start")
            logger.error(f"Failed to start agent {self.name}: {e}")
            raise
    
    async def stop(self, timeout: int = 30) -> None:
        """Stop the agent gracefully"""
        logger.info(f"Stopping agent {self.name}")
        self.state = AgentState.STOPPING
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel health check
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # Wait for workers to finish current tasks
        if self._worker_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._worker_tasks, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Agent {self.name} workers did not stop within timeout")
                for task in self._worker_tasks:
                    task.cancel()
        
        # Cleanup agent-specific resources
        await self.cleanup()
        
        self.state = AgentState.STOPPED
        logger.info(f"Agent {self.name} stopped")
    
    async def pause(self) -> None:
        """Pause agent execution"""
        logger.info(f"Pausing agent {self.name}")
        self.state = AgentState.PAUSED
        self._pause_event.set()
    
    async def resume(self) -> None:
        """Resume agent execution"""
        logger.info(f"Resuming agent {self.name}")
        self.state = AgentState.RUNNING
        self._pause_event.clear()
    
    async def add_task(self, task: AgentTask) -> None:
        """Add a task to the agent's queue"""
        await self.task_queue.put(task)
        logger.debug(f"Task {task.id} added to agent {self.name}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "metrics": asdict(self.metrics),
            "queue_size": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "last_error": str(self.last_error) if self.last_error else None,
            "config": self.config
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status"""
        try:
            # Basic health indicators
            health_status = {
                "healthy": True,
                "agent_id": self.agent_id,
                "name": self.name,
                "state": self.state.value,
                "uptime": time.time() - (self.metrics.last_activity.timestamp() if self.metrics.last_activity else time.time()),
                "success_rate": self.metrics.success_rate(),
                "error_count": self.metrics.error_count,
                "queue_size": self.task_queue.qsize()
            }
            
            # Agent-specific health checks
            agent_health = await self.check_health()
            health_status.update(agent_health)
            
            # Determine overall health
            # Determine overall health
            is_unhealthy = (
                self.state == AgentState.ERROR or
                (self.metrics.tasks_completed > 0 and self.metrics.success_rate() < 50) or
                self.metrics.error_count > 10
            )
            if is_unhealthy:
                health_status["healthy"] = False
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed for agent {self.name}: {e}")
            return {
                "healthy": False,
                "agent_id": self.agent_id,
                "name": self.name,
                "error": str(e)
            }
    
    # Abstract methods to be implemented by subclasses
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize agent-specific resources"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup agent-specific resources"""
        pass
    
    @abstractmethod
    async def process_task(self, task: AgentTask) -> Any:
        """Process a single task"""
        pass
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Perform agent-specific health checks"""
        pass
    
    # Private methods
    
    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop for processing tasks"""
        logger.debug(f"Worker {worker_id} started for agent {self.name}")
        
        while not self._shutdown_event.is_set():
            try:
                # Wait if paused
                if self._pause_event.is_set():
                    await asyncio.sleep(1)
                    continue
                
                # Get next task with timeout
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process the task
                await self._execute_task(task, worker_id)
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error in agent {self.name}: {e}")
                self._record_error(e, f"worker_{worker_id}")
        
        logger.debug(f"Worker {worker_id} stopped for agent {self.name}")
    
    async def _execute_task(self, task: AgentTask, worker_id: str) -> None:
        """Execute a single task with error handling and metrics"""
        start_time = time.time()
        self.active_tasks.add(task.id)
        
        try:
            logger.debug(f"Processing task {task.id} with worker {worker_id}")
            
            # Process the task
            result = await self.process_task(task)
            
            # Record success
            self.task_results[task.id] = result
            self.metrics.tasks_completed += 1
            self.metrics.last_activity = datetime.utcnow()
            
            logger.debug(f"Task {task.id} completed successfully")
            
        except Exception as e:
            # Handle task failure
            task.retry_count += 1
            self.metrics.tasks_failed += 1
            self._record_error(e, f"task_{task.id}")
            
            # Retry if possible
            if task.retry_count < task.max_retries:
                logger.warning(f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries}): {e}")
                # Re-queue with delay
                task.scheduled_at = datetime.utcnow() + timedelta(seconds=2 ** task.retry_count)
                await self.task_queue.put(task)
            else:
                logger.error(f"Task {task.id} failed permanently after {task.max_retries} retries: {e}")
                self.task_results[task.id] = {"error": str(e), "failed": True}
        
        finally:
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics.total_runtime += execution_time
            self.active_tasks.discard(task.id)
    
    async def _health_check_loop(self) -> None:
        """Periodic health check loop"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self._shutdown_event.is_set():
                    break
                
                health_status = await self.health_check()
                
                # Log health issues
                if not health_status.get("healthy", True):
                    logger.warning(f"Agent {self.name} health check failed: {health_status}")
                    
                    # Auto-recovery logic could go here
                    if self.state != AgentState.ERROR:
                        self.state = AgentState.ERROR
                        self.metrics.error_count += 1
                
            except Exception as e:
                logger.error(f"Health check loop error for agent {self.name}: {e}")
                self._record_error(e, "health_check")
    
    def _record_error(self, error: Exception, context: str) -> None:
        """Record error in history"""
        error_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(error),
            "type": type(error).__name__,
            "context": context
        }
        
        self.error_history.append(error_record)
        self.last_error = error
        self.metrics.error_count += 1
        
        # Keep only last 100 errors
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]