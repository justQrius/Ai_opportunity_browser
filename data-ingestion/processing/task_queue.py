"""Async task queue system for data processing pipeline."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, asdict
from uuid import uuid4

import redis.asyncio as redis
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskResult:
    """Task execution result."""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    completed_at: Optional[datetime] = None


class Task(BaseModel):
    """Task definition."""
    id: str
    name: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskQueue:
    """Async task queue with Redis backend."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", queue_name: str = "data_processing"):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self._redis: Optional[redis.Redis] = None
        self._workers: List[asyncio.Task] = []
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}
        self._running = False
        self._worker_count = 4
        
    async def initialize(self) -> None:
        """Initialize Redis connection and task queue."""
        try:
            self._redis = redis.from_url(self.redis_url)
            await self._redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown task queue and workers."""
        self._running = False
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
        
        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        
        # Close Redis connection
        if self._redis:
            await self._redis.close()
        
        logger.info("Task queue shut down")
    
    def register_handler(self, task_name: str, handler: Callable[[Dict[str, Any]], Awaitable[Any]]) -> None:
        """Register a task handler function."""
        self._handlers[task_name] = handler
        logger.info(f"Registered handler for task: {task_name}")
    
    async def enqueue_task(
        self,
        task_name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        scheduled_at: Optional[datetime] = None
    ) -> str:
        """Enqueue a new task."""
        if not self._redis:
            raise RuntimeError("Task queue not initialized")
        
        task = Task(
            id=str(uuid4()),
            name=task_name,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            created_at=datetime.now(),
            scheduled_at=scheduled_at
        )
        
        # Store task data
        await self._redis.hset(
            f"{self.queue_name}:tasks",
            task.id,
            task.json()
        )
        
        # Add to appropriate queue
        if scheduled_at and scheduled_at > datetime.now():
            # Scheduled task
            score = scheduled_at.timestamp()
            await self._redis.zadd(f"{self.queue_name}:scheduled", {task.id: score})
        else:
            # Immediate task
            queue_key = f"{self.queue_name}:priority:{priority.value}"
            await self._redis.lpush(queue_key, task.id)
        
        logger.info(f"Enqueued task {task.id} ({task_name}) with priority {priority}")
        return task.id
    
    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get task status and details."""
        if not self._redis:
            return None
        
        task_data = await self._redis.hget(f"{self.queue_name}:tasks", task_id)
        if task_data:
            return Task.parse_raw(task_data)
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        if not self._redis:
            return False
        
        task = await self.get_task_status(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False
        
        # Update task status
        task.status = TaskStatus.CANCELLED
        await self._redis.hset(
            f"{self.queue_name}:tasks",
            task_id,
            task.json()
        )
        
        # Remove from queues
        for priority in TaskPriority:
            await self._redis.lrem(f"{self.queue_name}:priority:{priority.value}", 0, task_id)
        
        await self._redis.zrem(f"{self.queue_name}:scheduled", task_id)
        
        logger.info(f"Cancelled task {task_id}")
        return True
    
    async def start_workers(self, worker_count: int = 4) -> None:
        """Start worker processes."""
        self._worker_count = worker_count
        self._running = True
        
        # Start scheduled task processor
        self._workers.append(asyncio.create_task(self._scheduled_task_processor()))
        
        # Start worker tasks
        for i in range(worker_count):
            worker_task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._workers.append(worker_task)
        
        logger.info(f"Started {worker_count} workers")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        if not self._redis:
            return {}
        
        stats = {
            "workers": len(self._workers),
            "handlers": len(self._handlers),
            "queues": {}
        }
        
        # Count tasks in each priority queue
        for priority in TaskPriority:
            queue_key = f"{self.queue_name}:priority:{priority.value}"
            count = await self._redis.llen(queue_key)
            stats["queues"][priority.name.lower()] = count
        
        # Count scheduled tasks
        scheduled_count = await self._redis.zcard(f"{self.queue_name}:scheduled")
        stats["scheduled"] = scheduled_count
        
        # Count total tasks
        total_tasks = await self._redis.hlen(f"{self.queue_name}:tasks")
        stats["total_tasks"] = total_tasks
        
        return stats
    
    async def _worker_loop(self, worker_name: str) -> None:
        """Main worker loop."""
        logger.info(f"Worker {worker_name} started")
        
        while self._running:
            try:
                task_id = await self._get_next_task()
                if task_id:
                    await self._process_task(task_id, worker_name)
                else:
                    # No tasks available, wait a bit
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(5)  # Back off on error
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _get_next_task(self) -> Optional[str]:
        """Get the next task from priority queues."""
        if not self._redis:
            return None
        
        # Check queues in priority order (highest first)
        for priority in sorted(TaskPriority, key=lambda x: x.value, reverse=True):
            queue_key = f"{self.queue_name}:priority:{priority.value}"
            task_id = await self._redis.rpop(queue_key)
            if task_id:
                return task_id.decode() if isinstance(task_id, bytes) else task_id
        
        return None
    
    async def _process_task(self, task_id: str, worker_name: str) -> None:
        """Process a single task."""
        if not self._redis:
            return
        
        # Get task details
        task = await self.get_task_status(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return
        
        # Check if task is cancelled
        if task.status == TaskStatus.CANCELLED:
            return
        
        # Update task status to processing
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now()
        await self._redis.hset(
            f"{self.queue_name}:tasks",
            task_id,
            task.json()
        )
        
        logger.info(f"Worker {worker_name} processing task {task_id} ({task.name})")
        
        try:
            # Get handler
            handler = self._handlers.get(task.name)
            if not handler:
                raise ValueError(f"No handler registered for task: {task.name}")
            
            # Execute task with timeout
            start_time = datetime.now()
            result = await asyncio.wait_for(
                handler(task.payload),
                timeout=task.timeout_seconds
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update task as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            await self._redis.hset(
                f"{self.queue_name}:tasks",
                task_id,
                task.json()
            )
            
            # Store result
            if result is not None:
                await self._redis.hset(
                    f"{self.queue_name}:results",
                    task_id,
                    json.dumps(result, default=str)
                )
            
            logger.info(f"Task {task_id} completed in {execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            await self._handle_task_failure(task, "Task timeout")
        except Exception as e:
            await self._handle_task_failure(task, str(e))
    
    async def _handle_task_failure(self, task: Task, error: str) -> None:
        """Handle task failure and retry logic."""
        if not self._redis:
            return
        
        task.error = error
        task.retry_count += 1
        
        if task.retry_count <= task.max_retries:
            # Retry task
            task.status = TaskStatus.RETRYING
            
            # Calculate retry delay (exponential backoff)
            delay_seconds = min(300, 2 ** task.retry_count)  # Max 5 minutes
            scheduled_at = datetime.now() + timedelta(seconds=delay_seconds)
            task.scheduled_at = scheduled_at
            
            # Update task
            await self._redis.hset(
                f"{self.queue_name}:tasks",
                task.id,
                task.json()
            )
            
            # Schedule retry
            score = scheduled_at.timestamp()
            await self._redis.zadd(f"{self.queue_name}:scheduled", {task.id: score})
            
            logger.warning(f"Task {task.id} failed, retrying in {delay_seconds}s (attempt {task.retry_count}/{task.max_retries})")
        else:
            # Mark as failed
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            
            await self._redis.hset(
                f"{self.queue_name}:tasks",
                task.id,
                task.json()
            )
            
            logger.error(f"Task {task.id} failed permanently after {task.retry_count} attempts: {error}")
    
    async def _scheduled_task_processor(self) -> None:
        """Process scheduled tasks."""
        logger.info("Scheduled task processor started")
        
        while self._running:
            try:
                if not self._redis:
                    await asyncio.sleep(10)
                    continue
                
                now = datetime.now().timestamp()
                
                # Get tasks that are ready to run
                ready_tasks = await self._redis.zrangebyscore(
                    f"{self.queue_name}:scheduled",
                    0, now, withscores=False
                )
                
                for task_id in ready_tasks:
                    if isinstance(task_id, bytes):
                        task_id = task_id.decode()
                    
                    # Get task details
                    task = await self.get_task_status(task_id)
                    if not task:
                        continue
                    
                    # Remove from scheduled queue
                    await self._redis.zrem(f"{self.queue_name}:scheduled", task_id)
                    
                    # Add to appropriate priority queue
                    task.status = TaskStatus.PENDING
                    task.scheduled_at = None
                    await self._redis.hset(
                        f"{self.queue_name}:tasks",
                        task_id,
                        task.json()
                    )
                    
                    queue_key = f"{self.queue_name}:priority:{task.priority.value}"
                    await self._redis.lpush(queue_key, task_id)
                    
                    logger.info(f"Scheduled task {task_id} is now ready for processing")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduled task processor error: {e}")
                await asyncio.sleep(30)
        
        logger.info("Scheduled task processor stopped")


# Global task queue instance
task_queue = TaskQueue()