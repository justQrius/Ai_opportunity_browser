"""
Agent Orchestration Engine for the AI Opportunity Browser system.
Coordinates and manages AI agent workflows as specified in the design document.

This module implements:
- Agent lifecycle management
- Task queue and priority scheduling  
- Inter-agent communication protocols
- Performance monitoring and scaling
- Agent coordination workflows
"""

import asyncio
import logging
from datetime import datetime, timedelta
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type, Union
from dataclasses import dataclass, asdict
import uuid

from .base import BaseAgent, AgentTask, AgentState, AgentPriority, AgentMetrics
from .models import Workflow, WorkflowStep, WorkflowState
from .planner_agent import PlannerAgent

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Overall system health status"""
    healthy: bool
    total_agents: int
    active_agents: int
    failed_agents: int
    total_workflows: int
    active_workflows: int
    system_load: float
    last_check: datetime
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class HealthStatus:
    """Overall system health status"""
    healthy: bool
    total_agents: int
    active_agents: int
    failed_agents: int
    total_workflows: int
    active_workflows: int
    system_load: float
    last_check: datetime
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class AgentOrchestrator:
    """
    Orchestrates and manages AI agent workflows.
    Implements the agent coordination patterns from the design document.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_types: Dict[str, Type[BaseAgent]] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.active_workflows: Set[str] = set()
        
        # Task scheduling
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.workflow_queue: asyncio.Queue = asyncio.Queue()
        
        # Control and monitoring
        self._shutdown_event = asyncio.Event()
        self._orchestrator_task: Optional[asyncio.Task] = None
        self._workflow_processor_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.metrics = {
            "workflows_completed": 0,
            "workflows_failed": 0,
            "total_tasks_processed": 0,
            "average_workflow_time": 0.0,
            "agent_utilization": {}
        }
        
        logger.info("AgentOrchestrator initialized")
    
    async def start(self) -> None:
        """Start the orchestrator and begin processing workflows"""
        logger.info("Starting AgentOrchestrator")
        
        # Start orchestrator tasks
        self._orchestrator_task = asyncio.create_task(self._orchestrator_loop())
        self._workflow_processor_task = asyncio.create_task(self._workflow_processor_loop())
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        
        logger.info("AgentOrchestrator started successfully")
    
    async def stop(self, timeout: int = 60) -> None:
        """Stop the orchestrator gracefully"""
        logger.info("Stopping AgentOrchestrator")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Stop all agents
        stop_tasks = []
        for agent in self.agents.values():
            if agent.state not in [AgentState.STOPPED, AgentState.STOPPING]:
                stop_tasks.append(agent.stop())
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Cancel orchestrator tasks
        tasks = [self._orchestrator_task, self._workflow_processor_task, self._health_monitor_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*[t for t in tasks if t], return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Orchestrator tasks did not stop within timeout")
        
        logger.info("AgentOrchestrator stopped")
    
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseAgent]) -> None:
        """Register an agent type for dynamic deployment"""
        self.agent_types[agent_type] = agent_class
        logger.info(f"Registered agent type: {agent_type}")
    
    async def deploy_agent(
        self, 
        agent_type: str, 
        agent_id: str = None, 
        config: Dict[str, Any] = None
    ) -> str:
        """Deploy a new agent instance"""
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_id = agent_id or f"{agent_type}_{uuid.uuid4().hex[:8]}"
        
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already exists")
        
        # Create and start agent
        agent_class = self.agent_types[agent_type]
        agent = agent_class(agent_id=agent_id, config=config or {})
        
        try:
            await agent.start()
            self.agents[agent_id] = agent
            logger.info(f"Deployed agent {agent_id} of type {agent_type}")
            return agent_id
        except Exception as e:
            logger.error(f"Failed to deploy agent {agent_id}: {e}")
            raise
    
    async def remove_agent(self, agent_id: str) -> None:
        """Remove an agent instance"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.agents[agent_id]
        await agent.stop()
        del self.agents[agent_id]
        logger.info(f"Removed agent {agent_id}")
    
    async def deploy_monitoring_agents(self, sources: List[str]) -> List[str]:
        """Deploy monitoring agents for specified data sources"""
        deployed_agents = []
        
        for source in sources:
            try:
                config = {
                    "data_source": source,
                    "scan_interval": self.config.get("monitoring_scan_interval", 300),
                    "max_signals_per_scan": self.config.get("max_signals_per_scan", 100)
                }
                
                agent_id = await self.deploy_agent("MonitoringAgent", config=config)
                deployed_agents.append(agent_id)
                
            except Exception as e:
                logger.error(f"Failed to deploy monitoring agent for {source}: {e}")
        
        logger.info(f"Deployed {len(deployed_agents)} monitoring agents")
        return deployed_agents
    
    async def trigger_analysis_workflow(self, raw_data: Dict[str, Any]) -> str:
        """Trigger analysis workflow for raw data"""
        workflow_id = str(uuid.uuid4())
        
        # Create analysis workflow steps
        steps = [
            WorkflowStep(
                step_id="data_cleaning",
                agent_type="AnalysisAgent",
                task_type="clean_data",
                input_data={"raw_data": raw_data}
            ),
            WorkflowStep(
                step_id="signal_extraction",
                agent_type="AnalysisAgent", 
                task_type="extract_signals",
                input_data={},
                dependencies=["data_cleaning"]
            ),
            WorkflowStep(
                step_id="opportunity_scoring",
                agent_type="AnalysisAgent",
                task_type="score_opportunity",
                input_data={},
                dependencies=["signal_extraction"]
            )
        ]
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name="analysis_workflow",
            steps=steps
        )
        
        await self.submit_workflow(workflow)
        return workflow_id
    
    async def coordinate_research_tasks(self, opportunity: Dict[str, Any]) -> str:
        """Coordinate research tasks for an opportunity"""
        workflow_id = str(uuid.uuid4())
        
        # Create research workflow steps
        steps = [
            WorkflowStep(
                step_id="market_research",
                agent_type="ResearchAgent",
                task_type="research_market",
                input_data={"opportunity": opportunity}
            ),
            WorkflowStep(
                step_id="competitive_analysis",
                agent_type="ResearchAgent",
                task_type="analyze_competition",
                input_data={"opportunity": opportunity}
            ),
            WorkflowStep(
                step_id="trend_analysis",
                agent_type="TrendAgent",
                task_type="analyze_trends",
                input_data={"opportunity": opportunity},
                dependencies=["market_research"]
            ),
            WorkflowStep(
                step_id="capability_assessment",
                agent_type="CapabilityAgent",
                task_type="assess_feasibility",
                input_data={"opportunity": opportunity},
                dependencies=["competitive_analysis", "trend_analysis"]
            )
        ]
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name="research_workflow",
            steps=steps
        )
        
        await self.submit_workflow(workflow)
        return workflow_id
    
    async def trigger_dynamic_workflow(self, problem_description: str) -> str:
        """
        Triggers a dynamic workflow by first invoking the PlannerAgent.
        """
        logger.info(f"Triggering dynamic workflow for: {problem_description}")

        # 1. Find a Planner Agent
        planner_agents = [
            agent for agent in self.agents.values()
            if isinstance(agent, PlannerAgent) and agent.state == AgentState.RUNNING
        ]
        
        if not planner_agents:
            # Deploy a planner agent if none are available
            try:
                planner_id = await self.deploy_agent("PlannerAgent", config={})
                planner_agent = self.agents[planner_id]
            except Exception as e:
                logger.error(f"Could not deploy a PlannerAgent: {e}")
                raise
        else:
            planner_agent = min(planner_agents, key=lambda a: len(a.active_tasks))

        # 2. Create and execute a planning task
        planning_task = AgentTask(
            id=f"plan_{uuid.uuid4().hex[:8]}",
            type="generate_workflow",
            data={"problem_description": problem_description}
        )
        
        # The PlannerAgent's process_task is synchronous in this design
        workflow = await planner_agent.process_task(planning_task)
        
        if not workflow or not isinstance(workflow, Workflow):
            raise Exception("PlannerAgent did not return a valid workflow.")

        # 3. Submit the generated workflow for execution
        await self.submit_workflow(workflow)
        logger.info(f"Dynamic workflow {workflow.workflow_id} submitted for execution.")
        return workflow.workflow_id

    async def submit_workflow(self, workflow: Workflow) -> None:
        """Submit a workflow for execution"""
        self.workflows[workflow.workflow_id] = workflow
        await self.workflow_queue.put(workflow.workflow_id)
        logger.info(f"Submitted workflow {workflow.workflow_id}")
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        return {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "state": workflow.state.value,
            "created_at": workflow.created_at.isoformat(),
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "steps_completed": len([s for s in workflow.steps if s.step_id in workflow.results]),
            "total_steps": len(workflow.steps),
            "results": workflow.results
        }
    
    async def monitor_agent_health(self) -> HealthStatus:
        """Monitor overall agent health"""
        total_agents = len(self.agents)
        active_agents = len([a for a in self.agents.values() if a.state == AgentState.RUNNING])
        failed_agents = len([a for a in self.agents.values() if a.state == AgentState.ERROR])
        
        total_workflows = len(self.workflows)
        active_workflows = len(self.active_workflows)
        
        # Calculate system load (simplified)
        system_load = sum(len(a.active_tasks) for a in self.agents.values()) / max(total_agents, 1)
        
        # Check for issues
        issues = []
        if failed_agents > 0:
            issues.append(f"{failed_agents} agents in error state")
        if system_load > 0.8:
            issues.append("High system load detected")
        if active_agents < total_agents * 0.5:
            issues.append("Low agent availability")
        
        return HealthStatus(
            healthy=len(issues) == 0,
            total_agents=total_agents,
            active_agents=active_agents,
            failed_agents=failed_agents,
            total_workflows=total_workflows,
            active_workflows=active_workflows,
            system_load=system_load,
            last_check=datetime.utcnow(),
            issues=issues
        )
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        health_status = await self.monitor_agent_health()
        
        # Agent-specific metrics
        agent_metrics = {}
        for agent_id, agent in self.agents.items():
            status = await agent.get_status()
            agent_metrics[agent_id] = status
        
        return {
            "health": asdict(health_status),
            "orchestrator_metrics": self.metrics,
            "agent_metrics": agent_metrics,
            "workflow_queue_size": self.workflow_queue.qsize(),
            "task_queue_size": self.task_queue.qsize()
        }
    
    # Private methods
    
    async def _orchestrator_loop(self) -> None:
        """Main orchestrator loop for task scheduling"""
        logger.debug("Orchestrator loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Process high-priority tasks
                await self._process_priority_tasks()
                
                # Balance agent loads
                await self._balance_agent_loads()
                
                # Cleanup completed workflows
                await self._cleanup_workflows()
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Orchestrator loop error: {e}")
                await asyncio.sleep(5)
        
        logger.debug("Orchestrator loop stopped")
    
    async def _workflow_processor_loop(self) -> None:
        """Process workflow queue"""
        logger.debug("Workflow processor loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get next workflow with timeout
                try:
                    workflow_id = await asyncio.wait_for(
                        self.workflow_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the workflow
                await self._execute_workflow(workflow_id)
                
            except Exception as e:
                logger.error(f"Workflow processor error: {e}")
        
        logger.debug("Workflow processor loop stopped")
    
    async def _health_monitor_loop(self) -> None:
        """Monitor system health periodically"""
        logger.debug("Health monitor loop started")
        
        while not self._shutdown_event.is_set():
            try:
                health_status = await self.monitor_agent_health()
                
                if not health_status.healthy:
                    logger.warning(f"System health issues detected: {health_status.issues}")
                    
                    # Auto-recovery actions
                    await self._handle_health_issues(health_status)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(30)
        
        logger.debug("Health monitor loop stopped")
    
    async def _execute_workflow(self, workflow_id: str) -> None:
        """Execute a workflow"""
        if workflow_id not in self.workflows:
            logger.error(f"Workflow {workflow_id} not found")
            return
        
        workflow = self.workflows[workflow_id]
        workflow.state = WorkflowState.RUNNING
        workflow.started_at = datetime.utcnow()
        self.active_workflows.add(workflow_id)
        
        try:
            logger.info(f"Executing workflow {workflow_id}")
            
            # Execute steps based on dependencies
            # In a full implementation of Dynamic Workflow Generation, this is where
            # the loop would pause and consult the PlannerAgent to potentially
            # modify the remaining steps based on the results of the last step.
            completed_steps = set()
            
            while len(completed_steps) < len(workflow.steps):
                # Find ready steps (dependencies satisfied)
                ready_steps = [
                    step for step in workflow.steps
                    if (step.step_id not in completed_steps and
                        all(dep in completed_steps for dep in step.dependencies))
                ]
                
                if not ready_steps:
                    raise Exception("Workflow deadlock: no ready steps found")
                
                # Execute ready steps in parallel
                step_tasks = []
                for step in ready_steps:
                    task = asyncio.create_task(self._execute_workflow_step(workflow, step))
                    step_tasks.append((step.step_id, task))
                
                # Wait for step completion
                for step_id, task in step_tasks:
                    try:
                        result = await task
                        workflow.results[step_id] = result
                        completed_steps.add(step_id)
                        logger.debug(f"Workflow {workflow_id} step {step_id} completed")
                    except Exception as e:
                        logger.error(f"Workflow {workflow_id} step {step_id} failed: {e}")
                        workflow.state = WorkflowState.FAILED
                        raise
            
            # Workflow completed successfully
            workflow.state = WorkflowState.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self.metrics["workflows_completed"] += 1
            
            logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            workflow.state = WorkflowState.FAILED
            workflow.completed_at = datetime.utcnow()
            self.metrics["workflows_failed"] += 1
            logger.error(f"Workflow {workflow_id} failed: {e}")
        
        finally:
            self.active_workflows.discard(workflow_id)
    
    async def _execute_workflow_step(self, workflow: Workflow, step: WorkflowStep) -> Any:
        """Execute a single workflow step"""
        # Find suitable agent
        suitable_agents = [
            agent for agent_id, agent in self.agents.items()
            if (agent.__class__.__name__ == step.agent_type and 
                agent.state == AgentState.RUNNING)
        ]
        
        if not suitable_agents:
            raise Exception(f"No suitable {step.agent_type} agents available")
        
        # Select agent with lowest load
        selected_agent = min(suitable_agents, key=lambda a: len(a.active_tasks))
        
        # Prepare task input with previous step results
        task_input = step.input_data.copy()
        for dep in step.dependencies:
            if dep in workflow.results:
                task_input[f"{dep}_result"] = workflow.results[dep]
        
        # Create and submit task
        task = AgentTask(
            id=f"{workflow.workflow_id}_{step.step_id}",
            type=step.task_type,
            data=task_input,
            priority=AgentPriority.NORMAL
        )
        
        await selected_agent.add_task(task)
        
        # Wait for task completion with timeout
        start_time = datetime.utcnow()
        while task.id not in selected_agent.task_results:
            if (datetime.utcnow() - start_time).total_seconds() > step.timeout:
                raise Exception(f"Step {step.step_id} timed out")
            await asyncio.sleep(0.1)
        
        result = selected_agent.task_results[task.id]
        
        # Check for task failure
        if isinstance(result, dict) and result.get("failed"):
            raise Exception(f"Step {step.step_id} failed: {result.get('error')}")
        
        return result
    
    async def _process_priority_tasks(self) -> None:
        """Process high-priority tasks"""
        # Implementation for priority task processing
        pass
    
    async def _balance_agent_loads(self) -> None:
        """Balance loads across agents"""
        # Implementation for load balancing
        pass
    
    async def _cleanup_workflows(self) -> None:
        """Cleanup completed workflows"""
        # Remove old completed workflows to prevent memory leaks
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        workflows_to_remove = [
            wf_id for wf_id, workflow in self.workflows.items()
            if (workflow.state in [WorkflowState.COMPLETED, WorkflowState.FAILED] and
                workflow.completed_at and workflow.completed_at < cutoff_time)
        ]
        
        for wf_id in workflows_to_remove:
            del self.workflows[wf_id]
        
        if workflows_to_remove:
            logger.debug(f"Cleaned up {len(workflows_to_remove)} old workflows")
    
    async def _handle_health_issues(self, health_status: HealthStatus) -> None:
        """Handle detected health issues"""
        # Implementation for auto-recovery actions
        for issue in health_status.issues:
            if "agents in error state" in issue:
                await self._restart_failed_agents()
            elif "High system load" in issue:
                await self._scale_agents()
    
    async def _restart_failed_agents(self) -> None:
        """Restart failed agents"""
        failed_agents = [
            agent_id for agent_id, agent in self.agents.items()
            if agent.state == AgentState.ERROR
        ]
        
        for agent_id in failed_agents:
            try:
                agent = self.agents[agent_id]
                await agent.stop()
                await agent.start()
                logger.info(f"Restarted failed agent {agent_id}")
            except Exception as e:
                logger.error(f"Failed to restart agent {agent_id}: {e}")
    
    async def _scale_agents(self) -> None:
        """Scale agents based on load"""
        # Implementation for dynamic agent scaling
        pass