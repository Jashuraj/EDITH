"""Unit tests for Multi-Agent Swarm Orchestrator."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from edith.providers.base import ModelResponse
from edith.tasks.agent_swarm import AgentSwarm, SwarmRole


class TestAgentSwarm(unittest.IsolatedAsyncioTestCase):
    """Test suite for concurrent subagents and consensus synthesis."""

    def setUp(self):
        self.mock_router = MagicMock()
        self.mock_router.execute = AsyncMock()
        self.swarm = AgentSwarm(router=self.mock_router)

    async def test_swarm_execution_and_synthesis(self):
        # Return mock response for subagent queries and consensus synthesis
        self.mock_router.execute.side_effect = [
            ModelResponse(content="Architect: System boundaries sound.", model="mock", provider="mock"),
            ModelResponse(content="Coder: Zero-defect functions ready.", model="mock", provider="mock"),
            ModelResponse(content="Researcher: Upstream docs verified.", model="mock", provider="mock"),
            ModelResponse(content="Auditor: Security policy compliant.", model="mock", provider="mock"),
            ModelResponse(content="Consensus: System cleared for launch.", model="mock", provider="mock"),
        ]

        roles = [SwarmRole.ARCHITECT, SwarmRole.CODER, SwarmRole.RESEARCHER, SwarmRole.AUDITOR]
        result = await self.swarm.execute_swarm(goal="Launch Project", roles=roles)

        self.assertTrue(result.success)
        self.assertEqual(len(result.reports), 4)
        self.assertEqual(result.consensus, "Consensus: System cleared for launch.")
        self.assertEqual(self.mock_router.execute.call_count, 5)

    async def test_subagent_failure_handling(self):
        self.mock_router.execute.side_effect = Exception("Provider Timeout")

        roles = [SwarmRole.ARCHITECT]
        result = await self.swarm.execute_swarm(goal="Evaluate Failures", roles=roles)

        self.assertTrue(result.success)
        self.assertEqual(len(result.reports), 1)
        self.assertFalse(result.reports[0].success)
        self.assertIn("Error", result.reports[0].content)


if __name__ == "__main__":
    unittest.main()
