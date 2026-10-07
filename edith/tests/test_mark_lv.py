"""Unit tests for Mark-LV architectural features in EDITH.

Tests Undo stack, Confirmation gate, and Echo guard.
"""

import time
import unittest
import numpy as np

from edith.core.confirm import ConfirmationGate
from edith.core.echo import EchoGuard, band_energies
from edith.core.undo import UndoManager
from edith.tools.reflex import REFLEX


class TestMarkLVFeatures(unittest.TestCase):
    def test_undo_manager_stack_and_reversal(self):
        mgr = UndoManager(max_depth=5)
        self.assertFalse(mgr.can_undo())
        self.assertEqual(mgr.undo_last(), "Nothing to undo, sir.")

        state = {"volume": 50}
        def reverse_vol():
            state["volume"] = 40
            return "Volume restored to 40"

        mgr.push("Change Volume", reverse_vol)
        self.assertTrue(mgr.can_undo())
        self.assertEqual(mgr.peek(), "Change Volume")
        self.assertEqual(mgr.history(), ["Change Volume"])

        res = mgr.undo_last()
        self.assertIn("Undone: Change Volume", res)
        self.assertEqual(state["volume"], 40)
        self.assertFalse(mgr.can_undo())

    def test_undo_manager_overflow(self):
        mgr = UndoManager(max_depth=2)
        mgr.push("Action 1", lambda: "1")
        mgr.push("Action 2", lambda: "2")
        mgr.push("Action 3", lambda: "3")

        self.assertEqual(len(mgr.history()), 2)
        self.assertEqual(mgr.peek(), "Action 3")

    def test_confirmation_gate_lifecycle(self):
        gate = ConfirmationGate(timeout_seconds=5.0)
        executed = []

        def risky_action():
            executed.append("done")
            return "Reboot completed"

        req = gate.request("reboot", "System Reboot", "Rebooting the host", risky_action)
        self.assertEqual(req["status"], "pending_confirmation")
        req_id = req["id"]

        pending = gate.get_pending()
        self.assertIsNotNone(pending)
        self.assertEqual(pending["id"], req_id)

        # Deny first
        denial = gate.resolve(req_id, approved=False)
        self.assertTrue(denial["success"])
        self.assertIn("Action cancelled", denial["message"])
        self.assertEqual(executed, [])

        # Request again and approve
        req2 = gate.request("reboot", "System Reboot", "Rebooting the host", risky_action)
        approval = gate.resolve(req2["id"], approved=True)
        self.assertTrue(approval["success"])
        self.assertIn("Executed: System Reboot", approval["message"])
        self.assertEqual(executed, ["done"])
        self.assertIsNone(gate.get_pending())

    def test_echo_guard_spectral_similarity(self):
        guard = EchoGuard()
        # Output synthetic speech audio block
        t = np.linspace(0, 0.1, 1600, endpoint=False)
        output_pcm = 0.5 * np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        guard.note_output(output_pcm, sr=16000, level=0.5)

        # Identical echo signal arriving at microphone
        is_echo = guard.is_echo(output_pcm, sr=16000)
        self.assertTrue(is_echo)

        # Unrelated high frequency signal (not echo)
        user_voice = 0.5 * np.sin(2 * np.pi * 4000 * t).astype(np.float32)
        is_user_echo = guard.is_echo(user_voice, sr=16000)
        self.assertFalse(is_user_echo)

    def test_reflex_undo_and_confirm(self):
        # Match undo
        m_undo = REFLEX.evaluate("undo that")
        self.assertIsNotNone(m_undo)
        self.assertEqual(m_undo.command_name, "undo_action")

        # Match confirm
        m_confirm = REFLEX.evaluate("confirm action")
        self.assertIsNotNone(m_confirm)
        self.assertEqual(m_confirm.command_name, "confirm_action")

        # Match system metrics
        m_stats = REFLEX.evaluate("system metrics")
        self.assertIsNotNone(m_stats)
        self.assertEqual(m_stats.command_name, "system_metrics")


if __name__ == "__main__":
    unittest.main()
