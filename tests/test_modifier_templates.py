"""Regression tests for modifier parameter template wiring."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.ui.ui_widget_kit import TEMPLATE_SPECS, build_template_widget  # noqa: E402
from ModTools_5_4.ui.ui_widget_kit import set_workspace_sections_provider  # noqa: E402
from ModTools_5_4.ui.pages.modifier_workspace import TEMPLATE_PARAM_MAPPINGS  # noqa: E402

from sample_project import build_sample_project  # noqa: E402

NEW_TEMPLATE_KEYS = [
    "promotion_class_search", "leader_search", "civilization_search", "project_search",
    "trait_search", "policy_search", "belief_search", "unit_promotion_search",
    "governor_promotion_search", "great_person_individual_search", "route_search",
    "diplomatic_action_search", "random_event_search", "victory_search", "war_search",
    "resolution_search", "operation_search", "emergency_search",
    "military_formation_search", "resource_usage_search",
    "diplomatic_yield_source_search", "bonus_type_search",
    "belief_yield_type_search", "relic_source_search", "effect_type_search",
    "collection_type_search", "happiness_search",
]


class ModifierTemplateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.registered_keys = {spec.key for spec in TEMPLATE_SPECS}

    def test_every_mapping_value_registered(self) -> None:
        missing = sorted(
            key for key in set(TEMPLATE_PARAM_MAPPINGS.values()) if key not in self.registered_keys
        )
        self.assertEqual(missing, [], "映射指向了未注册的模板")

    def test_new_templates_instantiate(self) -> None:
        for key in NEW_TEMPLATE_KEYS:
            with self.subTest(key=key):
                widget = build_template_widget(key)
                self.assertIsNotNone(widget)

    def test_promotion_class_includes_workspace_tree(self) -> None:
        sections = build_sample_project().sections
        set_workspace_sections_provider(lambda: sections)
        try:
            widget = build_template_widget("unit_promotion_class")
            options = widget._options
            values = [value for _display, value in options]
            self.assertIn("PROMOTION_CLASS_SIQI_DEMO", values, "应包含工程晋升树类型")
        finally:
            set_workspace_sections_provider(None)

    def test_promotion_node_types_computed(self) -> None:
        sections = build_sample_project().sections
        set_workspace_sections_provider(lambda: sections)
        try:
            widget = build_template_widget("unit_promotion_search")
            values = [value for _display, value in widget._options]
            self.assertIn("PROMOTION_DEMO_DEMO_A", values)
            self.assertIn("PROMOTION_DEMO_DEMO_B", values)
        finally:
            set_workspace_sections_provider(None)

    def test_happiness_template_is_selection_only(self) -> None:
        widget = build_template_widget("happiness_search")
        self.assertFalse(widget._combo.isEditable())


if __name__ == "__main__":
    unittest.main()
