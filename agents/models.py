"""
Data models for agent workflows in the AI Opportunity Browser system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

@dataclass
class WorkflowStep:
    """Represents a step in an agent workflow"""
    step_id: str
    agent_type: str
    task_type: str
    input_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 300  # 5 minutes default
    retry_count: int = 0
    max_retries: int = 3

class WorkflowState(Enum):
    """Workflow execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Workflow:
    """Represents a complete agent workflow"""
    workflow_id: str
    name: str
    steps: List[WorkflowStep]
    state: WorkflowState = WorkflowState.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime = None
    completed_at: datetime = None
    results: Dict[str, Any] = field(default_factory=dict)