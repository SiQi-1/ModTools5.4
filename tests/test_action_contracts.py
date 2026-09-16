"""Tests for descriptive AI action contracts."""
from __future__ import annotations

import unittest

from ModTools_5_4.ai.contracts import make_action_contract


class ActionContractTestCase(unittest.TestCase):
    def test_known_action_exposes_parameter_metadata(self) -> None:
        contract = make_action_contract("generate_all", "生成全部文件")
        payload = contract.to_dict()
        self.assertEqual(payload["name"], "generate_all")
        self.assertEqual(payload["version"], "1")
        self.assertEqual(payload["params"]["overwrite"]["enum"], ["ask", "all", "none"])

    def test_unknown_action_remains_descriptive(self) -> None:
        payload = make_action_contract("future_action", "未来动作").to_dict()
        self.assertEqual(payload["name"], "future_action")
        self.assertNotIn("params", payload)


if __name__ == "__main__":
    unittest.main()
