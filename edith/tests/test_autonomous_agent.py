"""Unit tests for Autonomous Multi-Step ToolUsingAgent."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from edith.core.security import EmergencyStopActiveError, RiskLevel, SECURITY
from edith.providers.base import ModelResponse, ToolCall
from edith.tasks.autonomous_agent import ToolUsingAgent
from edith.tools.registry import ToolRegistry


class TestAutonomousAgent(unittest.IsolatedAsyncioTestCase):
    """Test suite for ReAct autonomous agent loop."""

    def setUp(self):
        self.registry = ToolRegistry()
        self.registry.register(
            name="mock_calc",
            description="Perform calculation",
            action_pack="CODING_PACK",
            risk=RiskLevel.LOW,
            fn=lambda expr: f"Computed {expr}",
            parameters_schema={"type": "object", "properties": {"expr": {"type": "string"}}},
        )
        self.mock_router = MagicMock()
        self.mock_router.execute = AsyncMock()
        self.agent = ToolUsingAgent(registry=self.registry, router=self.mock_router, max_iterations=3)

    async def test_agent_final_answer_direct(self):
        self.mock_router.execute.return_value = ModelResponse(
            content="THOUGHT: Direct inquiry.\nFINAL_ANSWER: Diagnostic complete.",
            model="mock-model",
            provider="mock",
        )

        result = await self.agent.run("Give diagnostic status")
        self.assertTrue(result.success)
        self.assertEqual(result.final_answer, "Diagnostic complete.")
        self.assertEqual(len(result.steps), 1)

    async def test_agent_action_then_final_answer(self):
        resp_step1 = ModelResponse(
            content='THOUGHT: Need calc.\nACTION: {"tool": "mock_calc", "params": {"expr": "100+50"}}',
            model="mock-model",
            provider="mock",
        )
        resp_step2 = ModelResponse(
            content="THOUGHT: Result in hand.\nFINAL_ANSWER: Calculation gives 150.",
            model="mock-model",
            provider="mock",
        )
        self.mock_router.execute.side_effect = [resp_step1, resp_step2]

        result = await self.agent.run("Compute value")
        self.assertTrue(result.success)
        self.assertEqual(result.final_answer, "Calculation gives 150.")
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(result.steps[0].tool_name, "mock_calc")
        self.assertIn("Computed 100+50", result.steps[0].observation)

    async def test_agent_native_tool_call(self):
        resp_step1 = ModelResponse(
            content="Invoking mock calc",
            tool_calls=[ToolCall(name="mock_calc", arguments={"expr": "42*2"})],
            model="mock-model",
            provider="mock",
        )
        resp_step2 = ModelResponse(
            content="THOUGHT: Done.\nFINAL_ANSWER: 84 computed.",
            model="mock-model",
            provider="mock",
        )
        self.mock_router.execute.side_effect = [resp_step1, resp_step2]

        result = await self.agent.run("Compute 42*2")
        self.assertTrue(result.success)
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(result.steps[0].tool_name, "mock_calc")

    async def test_emergency_stop_halts_agent(self):
        SECURITY.trigger_emergency_stop("Test emergency halt")
        try:
            with self.assertRaises(EmergencyStopActiveError):
                await self.agent.run("Perform actions")
        finally:
            SECURITY.reset_emergency_stop()


if __name__ == "__main__":
    unittest.main()
