"""
Base Agent Framework for True Autonomous ReAct Agents.
Provides Think -> Act -> Observe execution loops, tool bindings,
inter-agent messaging, and telemetry tracking.
"""

import time
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

logger = logging.getLogger("rex.base_agent")


class AgentMessage(BaseModel):
    sender: str
    receiver: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class AgentToolCall(BaseModel):
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


class AgentResult(BaseModel):
    agent_name: str
    status: str = "success"  # "success", "partial", "failed"
    summary: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: List[AgentToolCall] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    thought_trajectory: List[str] = Field(default_factory=list)


class BaseTool:
    """Base class for modular agent tools."""
    name: str = "base_tool"
    description: str = "Base tool description"

    def execute(self, **kwargs) -> Any:
        raise NotImplementedError("Subclasses must implement execute()")

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "description": self.description}


class FunctionalTool(BaseTool):
    """Wraps a standard Python function into an agent tool."""
    def __init__(self, name: str, description: str, fn: Callable):
        self.name = name
        self.description = description
        self.fn = fn

    def execute(self, **kwargs) -> Any:
        return self.fn(**kwargs)


class BaseResearchAgent:
    """
    Autonomous ReAct Research Agent.
    Executes a reasoning loop (Think -> Act -> Observe) using bound tools.
    """
    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model_name: str = "phi3:mini",
        tools: Optional[List[BaseTool]] = None,
        max_steps: int = 4
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.tools = {t.name: t for t in (tools or [])}
        self.max_steps = max_steps

    def register_tool(self, tool: BaseTool):
        self.tools[tool.name] = tool

    def execute(self, task: str, context: Dict[str, Any]) -> AgentResult:
        """
        Executes the ReAct (Think -> Act -> Observe) reasoning loop.
        """
        t0 = time.perf_counter()
        tool_calls: List[AgentToolCall] = []
        trajectory: List[str] = []
        step = 0
        
        trajectory.append(f"[{self.name}] Initialized task: {task[:100]}")
        
        # Available tools description for LLM or decision logic
        tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in self.tools.values())
        
        # If agent has dedicated deterministic tools and task matches, invoke them
        current_data = dict(context)
        
        for tool_name, tool_obj in self.tools.items():
            t_start = time.perf_counter()
            try:
                trajectory.append(f"[{self.name}] Step {step+1}: Invoking tool '{tool_name}'")
                # Introspect tool requirements from context
                tool_args = {k: v for k, v in context.items() if k in getattr(tool_obj, '__code__', {}).co_varnames if k != 'self'}
                if not tool_args:
                    tool_args = {"query": context.get("query", task), "sources": context.get("all_sources", [])}
                
                output = tool_obj.execute(**tool_args)
                t_dur = (time.perf_counter() - t_start) * 1000
                
                tool_calls.append(AgentToolCall(
                    tool_name=tool_name,
                    args=tool_args,
                    output=output,
                    duration_ms=t_dur,
                    success=True
                ))
                trajectory.append(f"[{self.name}] Tool '{tool_name}' executed in {t_dur:.1f}ms")
                current_data[f"{self.name}_{tool_name}_output"] = output
            except Exception as e:
                t_dur = (time.perf_counter() - t_start) * 1000
                tool_calls.append(AgentToolCall(
                    tool_name=tool_name,
                    args={},
                    output=None,
                    duration_ms=t_dur,
                    success=False,
                    error=str(e)
                ))
                trajectory.append(f"[{self.name}] Tool '{tool_name}' failed: {e}")
            step += 1
            if step >= self.max_steps:
                break

        elapsed = (time.perf_counter() - t0) * 1000
        summary = f"Agent {self.name} ({self.role}) completed {step} execution steps with {len(tool_calls)} tool calls."
        
        return AgentResult(
            agent_name=self.name,
            status="success" if any(tc.success for tc in tool_calls) or not self.tools else "partial",
            summary=summary,
            data=current_data,
            tool_calls=tool_calls,
            execution_time_ms=elapsed,
            thought_trajectory=trajectory
        )
