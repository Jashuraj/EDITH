"""Autonomous Multi-Step ToolUsingAgent for EDITH.

Implements Sections 28, 29, 31, 33 of the Engineering Constitution.
Follows the ReAct / ToolUsingAgent pattern from OpenJarvis.
Autonomously plans steps, selects tools from REGISTRY, observes results,
and iterates until the goal is fully achieved.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from edith.core.event_bus import BUS
from edith.core.security import SECURITY, EmergencyStopActiveError
from edith.core.state_machine import STATE, SystemState
from edith.providers.base import ModelResponse, ToolCall
from edith.providers.router import ROUTER, TaskCategory
from edith.tools.registry import REGISTRY

logger = logging.getLogger("edith.tasks.autonomous_agent")


@dataclass
class AgentStep:
    """An atomic thought, action, and observation in the agent loop."""
    iteration: int
    thought: str
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    observation: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class AgentResult:
    """Final synthesis and step-by-step trace of an autonomous agent execution."""
    goal: str
    final_answer: str
    success: bool
    steps: List[AgentStep] = field(default_factory=list)
    total_duration_ms: float = 0.0


class ToolUsingAgent:
    """Autonomous ReAct agent selecting and executing tools iteratively."""

    def __init__(self, registry=None, router=None, max_iterations: int = 5):
        self.registry = registry or REGISTRY
        self.router = router or ROUTER
        self.max_iterations = max_iterations

    async def run(
        self,
        goal: str,
        on_step_callback: Optional[Callable[[AgentStep], None]] = None,
    ) -> AgentResult:
        """Execute autonomous loop until goal completion or iteration limit."""
        t_start = time.perf_counter()
        clean_goal = (goal or "").strip()
        steps: List[AgentStep] = []

        STATE.set_state_sync(SystemState.PLANNING, reason=f"Planning autonomous task: {clean_goal[:40]}")
        BUS.publish_sync("agent:thought", {"goal": clean_goal, "status": "planning", "thought": "Analyzing goal requirements"})

        system_prompt = (
            "You are EDITH's Autonomous ToolUsingAgent. You solve tasks by taking actions.\n"
            "Respond in one of two formats:\n"
            "Format 1 (To use a tool):\n"
            "THOUGHT: <your reasoning>\n"
            "ACTION: {\"tool\": \"<tool_name>\", \"params\": {<arguments>}}\n\n"
            "Format 2 (When goal is finished):\n"
            "THOUGHT: <your reasoning>\n"
            "FINAL_ANSWER: <complete response to user>\n"
        )

        history_context = f"Goal: {clean_goal}\n"

        for iteration in range(1, self.max_iterations + 1):
            if SECURITY.is_emergency_stopped:
                raise EmergencyStopActiveError("Autonomous agent halted by Emergency Stop.")

            STATE.set_state_sync(SystemState.EXECUTING, reason=f"Autonomous step #{iteration}")
            t_step_start = time.perf_counter()

            # Retrieve available tool definitions
            tools_schemas = self.registry.get_tools_schema()

            prompt = f"{history_context}\nStep {iteration}/{self.max_iterations}. Next action?"
            resp: ModelResponse = await self.router.execute(
                prompt=prompt,
                category=TaskCategory.TOOL_CALLING,
                tools=tools_schemas,
                system_prompt=system_prompt,
            )

            raw_text = resp.content or ""
            dt_step = (time.perf_counter() - t_step_start) * 1000.0

            # 1. Check for Native Tool Calls
            if resp.tool_calls:
                tc = resp.tool_calls[0]
                tool_name = tc.name
                tool_params = tc.arguments
                thought = raw_text.strip() or f"Invoking tool {tool_name}"
            else:
                # 2. Parse text for THOUGHT and ACTION or FINAL_ANSWER
                m_final = re.search(r"FINAL_ANSWER:\s*(.+)", raw_text, re.DOTALL)
                m_thought = re.search(r"THOUGHT:\s*(.+?)(?=(?:ACTION:|FINAL_ANSWER:|$))", raw_text, re.DOTALL)
                thought = m_thought.group(1).strip() if m_thought else raw_text.strip()

                m_action_start = re.search(r"ACTION:\s*(\{.*)", raw_text, re.DOTALL)
                if m_final and not m_action_start:
                    final_ans = m_final.group(1).strip()
                    step = AgentStep(
                        iteration=iteration,
                        thought=thought,
                        observation="Goal achieved.",
                        duration_ms=dt_step,
                    )
                    steps.append(step)
                    if on_step_callback:
                        on_step_callback(step)
                    BUS.publish_sync("agent:completed", {"goal": clean_goal, "answer": final_ans})
                    STATE.set_state_sync(SystemState.READY, reason="Autonomous agent goal complete")
                    return AgentResult(
                        goal=clean_goal,
                        final_answer=final_ans,
                        success=True,
                        steps=steps,
                        total_duration_ms=(time.perf_counter() - t_start) * 1000.0,
                    )

                if m_action_start:
                    try:
                        act_data, _ = json.JSONDecoder().raw_decode(m_action_start.group(1).strip())
                        tool_name = act_data.get("tool", "")
                        tool_params = act_data.get("params", {})
                    except Exception as parse_err:
                        logger.warning("Failed to parse action JSON: %s", parse_err)
                        tool_name = None
                        tool_params = {}
                else:
                    tool_name = None
                    tool_params = {}

            # Execute Tool Action
            if tool_name and self.registry.get(tool_name):
                BUS.publish_sync("agent:action", {"iteration": iteration, "tool": tool_name, "params": tool_params})
                try:
                    observation_val = self.registry.execute_tool(tool_name, tool_params)
                    observation = str(observation_val)
                except Exception as ex:
                    observation = f"Error executing {tool_name}: {ex}"
            else:
                # No valid action found, conclude with response
                final_ans = raw_text
                step = AgentStep(iteration=iteration, thought=thought, observation=final_ans, duration_ms=dt_step)
                steps.append(step)
                STATE.set_state_sync(SystemState.READY, reason="Agent complete without further tool actions")
                return AgentResult(
                    goal=clean_goal,
                    final_answer=final_ans,
                    success=True,
                    steps=steps,
                    total_duration_ms=(time.perf_counter() - t_start) * 1000.0,
                )

            step = AgentStep(
                iteration=iteration,
                thought=thought,
                tool_name=tool_name,
                tool_params=tool_params,
                observation=observation,
                duration_ms=dt_step,
            )
            steps.append(step)
            if on_step_callback:
                on_step_callback(step)

            # Update context for next iteration
            history_context += f"\nThought: {thought}\nAction: {tool_name}({json.dumps(tool_params)})\nObservation: {observation}\n"

        # Limit reached
        STATE.set_state_sync(SystemState.READY, reason="Max iterations reached")
        return AgentResult(
            goal=clean_goal,
            final_answer=f"Completed {self.max_iterations} autonomous steps. Last observation: {steps[-1].observation if steps else 'None'}",
            success=True,
            steps=steps,
            total_duration_ms=(time.perf_counter() - t_start) * 1000.0,
        )


# Global Singleton Instance
AUTONOMOUS_AGENT = ToolUsingAgent()
