"""civ6-ai-play 夹具库契约测试：Lua 构建器文本、解析与 CLI（不需要游戏）。"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/packages/civ6-ai-play/scripts"
sys.path.insert(0, str(SCRIPTS))

_spec = importlib.util.spec_from_file_location("civ6_fixtures", SCRIPTS / "civ6_fixtures.py")
fixtures = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixtures)


class _FakeClient:
    def __init__(self, lines):
        self.lines = lines
        self.calls = []

    def eval_collect(self, state, lua, wait=3.0):
        self.calls.append((state, lua, wait))
        return {"lines": list(self.lines), "error": None, "raw": []}

    def refresh_states(self):
        return {6: "Arknights_Cute_Leaders_19.47_Scripts", 136: "InGame"}


class LuaBuilderTests(unittest.TestCase):
    def test_quote_escapes_quotes_and_keeps_unicode(self):
        self.assertEqual(fixtures._q('A"B'), '"A\\"B"')
        self.assertIn("若叶睦", fixtures._q("若叶睦"))

    def test_find_plot_owned_city_and_wonder_slot(self):
        lua = fixtures.lua_find_plot(owned=True, city_id=65536, wonder_slot=True)
        self.assertIn("pt:GetOwner() == pid", lua)
        self.assertIn("pc:GetID() == 65536", lua)
        self.assertIn("GetDistrictType() == -1", lua)
        self.assertIn("emit(\"plot.index\"", lua)

    def test_find_plot_unowned_distance(self):
        lua = fixtures.lua_find_plot(owned=False, unowned_min_distance=4)
        self.assertIn("pt:GetOwner() < 0", lua)
        self.assertIn("GetPlotDistance", lua)
        self.assertIn(">= 4", lua)

    def test_spawn_unit_uses_init_unit(self):
        lua = fixtures.lua_spawn_unit("UNIT_WARRIOR", 25, 10)
        self.assertIn("UnitManager.InitUnit(pid, \"UNIT_WARRIOR\", 25, 10)", lua)

    def test_found_city_uses_request_operation(self):
        lua = fixtures.lua_found_city(196608)
        self.assertIn("UnitManager.GetUnit(pid, 196608)", lua)
        self.assertIn("UnitOperationTypes.FOUND_CITY", lua)

    def test_governor_points(self):
        lua = fixtures.lua_governor_points(12)
        self.assertIn("ChangeGovernorPoints(12)", lua)
        self.assertIn("GetGovernorPoints()", lua)

    def test_create_building_uses_create_building(self):
        lua = fixtures.lua_create_building(65536, "BUILDING_GRANARY")
        self.assertIn("CreateBuilding(info.Index)", lua)
        self.assertIn("HasBuilding(info.Index)", lua)

    def test_create_wonder_uses_incomplete_building(self):
        # F-29：Wonder 只能用 CreateIncompleteBuilding，不能用 CreateBuilding。
        lua = fixtures.lua_create_wonder(65536, "BUILDING_STONEHENGE", 123)
        self.assertIn("CreateIncompleteBuilding(info.Index, 123, 100)", lua)
        self.assertNotIn("CreateBuilding(info.Index", lua)

    def test_simulate_combat_reads_result_parameters(self):
        lua = fixtures.lua_simulate_combat(131073, 196610)
        self.assertIn("SimulateAttackVersus(131073, 196610)", lua)
        self.assertIn("CombatResultParameters.ATTACKER", lua)
        self.assertIn("CombatResultParameters.STRENGTH_MODIFIER", lua)

    def test_tourism_uses_stats(self):
        lua = fixtures.lua_tourism(0)
        self.assertIn("GetStats()", lua)
        self.assertIn("GetTourism()", lua)

    def test_emit_preamble_prints_prefixed_lines(self):
        self.assertIn("@@CIV6AI:", fixtures.EMIT_PREAMBLE)

    # -- UI 侧生产夹具（建筑/区域/奇观） -------------------------------------

    def test_production_list_uses_canproduce_and_canstartoperation(self):
        lua = fixtures.lua_production_list(65536, "all")
        self.assertIn("CanProduce(hash, true)", lua)
        self.assertIn("CanStartOperation", lua)
        self.assertIn("PARAM_UNIT_TYPE", lua)
        self.assertIn("PARAM_BUILDING_TYPE", lua)
        self.assertIn("PARAM_DISTRICT_TYPE", lua)
        self.assertIn("PARAM_PROJECT_TYPE", lua)

    def test_production_list_kind_filters(self):
        unit_only = fixtures.lua_production_list(1, "unit")
        self.assertIn("GameInfo.Units()", unit_only)
        self.assertNotIn("GameInfo.Districts()", unit_only)
        wonder_only = fixtures.lua_production_list(1, "wonder")
        self.assertIn("IsWonder", wonder_only)
        self.assertIn("PARAM_BUILDING_TYPE", wonder_only)

    def test_build_targets_uses_operation_targets_and_plot_checks(self):
        lua = fixtures.lua_build_targets(65536, "building", "BUILDING_STONEHENGE", 5)
        self.assertIn("GetOperationTargets", lua)
        self.assertIn("CityOperationTypes.PARAM_BUILDING_TYPE", lua)
        self.assertIn("CanStartOperation", lua)
        self.assertIn("PARAM_X", lua)
        self.assertIn("SUCCESS_CONDITIONS", lua)
        self.assertIn("math.min(#plots, 5)", lua)

    def test_build_targets_district_param(self):
        lua = fixtures.lua_build_targets(65536, "district", "DISTRICT_CAMPUS")
        self.assertIn("CityOperationTypes.PARAM_DISTRICT_TYPE", lua)

    def test_build_targets_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            fixtures.lua_build_targets(1, "unit", "UNIT_WARRIOR")

    def test_production_current_builder(self):
        lua = fixtures.lua_production_current(65536)
        self.assertIn("GetCurrentProductionTypeHash()", lua)
        self.assertIn("GetTurnsLeft()", lua)

    def test_set_production_async_verify(self):
        class _Scripted:
            def __init__(self):
                self.responses = [
                    ["CIV6AI:production.can=true", "CIV6AI:production.expected=123"],
                    ["CIV6AI:production.current=123", "CIV6AI:production.turns=8"],
                ]
                self.calls = 0

            def refresh_states(self):
                return {6: "Mod_Scripts", 136: "InGame"}

            def eval_collect(self, state, lua, wait=3.0):
                lines = self.responses[self.calls]
                self.calls += 1
                return {"lines": lines, "error": None, "raw": []}

        client = _Scripted()
        out = fixtures.set_production(client, 65536, "unit", "UNIT_WARRIOR", verify_delay=0)
        self.assertEqual(out["data"]["production.verified"], True)
        self.assertEqual(out["data"]["production.current"], "123")

    def test_set_production_requests_build_operation(self):
        lua = fixtures.lua_set_production(65536, "wonder", "BUILDING_STONEHENGE", 123)
        self.assertIn("CityManager.RequestOperation(city, CityOperationTypes.BUILD, params)", lua)
        self.assertIn("PARAM_X", lua)
        self.assertIn("GetCurrentProductionTypeHash()", lua)
        # 非坐标项不带 PARAM_X
        unit_lua = fixtures.lua_set_production(65536, "unit", "UNIT_WARRIOR")
        self.assertNotIn("PARAM_X", unit_lua)


class EvalAndCliTests(unittest.TestCase):
    def test_eval_emit_parses_prefixed_lines(self):
        client = _FakeClient(["CIV6AI:plot.index=5", "CIV6AI:plot.x=25", "CIV6AI:plot.y=10"])
        out = fixtures.eval_emit(client, 6, "emit('x', 1)")
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["plot.index"], "5")
        self.assertEqual(out["data"]["plot.x"], "25")
        self.assertEqual(client.calls[0][0], 6)

    def test_run_scripts_uses_scripts_state(self):
        client = _FakeClient(["CIV6AI:turn=3"])
        out = fixtures.run_scripts(client, "emit('turn', 3)")
        self.assertEqual(out["data"]["turn"], "3")
        self.assertEqual(client.calls[0][0], 6)

    def test_cli_has_commands_and_defaults(self):
        parser = fixtures.build_parser()
        actions = {a.dest for a in parser._actions if a.dest == "command"}  # subparsers
        self.assertIn("command", actions)
        # 逐个命令解析
        for argv in (
            ["states"], ["turn"], ["find-plot", "--city-id", "1"],
            ["spawn-unit", "--unit", "UNIT_WARRIOR", "--x", "1", "--y", "2"],
            ["found-city", "--x", "3", "--y", "4"],
            ["governor-points", "--points", "5"],
            ["create-building", "--city-id", "1", "--building", "BUILDING_GRANARY"],
            ["create-wonder", "--city-id", "1", "--wonder", "BUILDING_X", "--plot-index", "9"],
            ["simulate-combat", "--attacker", "1", "--defender", "2"],
            ["tourism"], ["end-turn"], ["run-turns", "--count", "3"], ["press-escape"],
            ["list-production", "--city-id", "1"],
            ["list-production", "--city-id", "1", "--kind", "wonder"],
            ["build-targets", "--city-id", "1", "--kind", "building", "--item", "BUILDING_X"],
            ["wonder-targets", "--city-id", "1", "--wonder", "BUILDING_X"],
            ["district-targets", "--city-id", "1", "--district", "DISTRICT_X"],
            ["set-production", "--city-id", "1", "--kind", "wonder", "--item", "BUILDING_X", "--plot-index", "9"],
        ):
            args = parser.parse_args(argv)
            self.assertEqual(args.host, fixtures.DEFAULT_HOST)
            self.assertEqual(args.port, fixtures.DEFAULT_PORT)

    def test_find_state_prefers_exact_in_game(self):
        class _States:
            def refresh_states(self):
                return {5: "InGamePopup", 138: "InGame"}

        self.assertEqual(fixtures._find_state(_States(), "InGame"), 138)

    def test_press_escape_returns_error_off_windows(self):
        with mock.patch.object(fixtures.sys, "platform", "linux"):
            out = fixtures.press_escape(1)
        self.assertFalse(out["ok"])
        self.assertIn("windows", out["error"].lower())


if __name__ == "__main__":
    unittest.main()
