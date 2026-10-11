"""Test suite for EDITH configuration and hardware profiling."""

import unittest
from edith.core.config import CONFIG, HardwareProfile, SystemConfig


class TestSystemConfig(unittest.TestCase):
    def test_hardware_detection(self):
        hw = HardwareProfile.detect()
        self.assertGreater(hw.cpu_cores, 0)
        self.assertGreater(hw.total_ram_gb, 0.0)
        self.assertIsNotNone(hw.os_name)

    def test_low_resource_ceiling_applied(self):
        cfg = SystemConfig()
        if cfg.hardware.total_ram_gb <= 8.5:
            self.assertEqual(cfg.ceilings.max_models_loaded, 1)
            self.assertLessEqual(cfg.ceilings.max_ram_usage_gb, 6.0)

    def test_singleton_config(self):
        self.assertEqual(CONFIG.system_name, "EDITH")
        self.assertEqual(CONFIG.creator, "Jashwanth Raj")


if __name__ == "__main__":
    unittest.main()
