"""AI 控制接口测试：动作注册表 + Qt 桥 + HTTP 服务器 + --ai-exec 解析（offscreen）。"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ModTools_5_4.ai.control_server import (  # noqa: E402
    AiActionError,
    ControlContext,
    ControlServer,
    emit_exec_results,
    parse_ai_exec_requests,
    run_ai_requests,
)
from ModTools_5_4.app.application import _parse_cli_ai_args  # noqa: E402
from ModTools_5_4.app.config import load_config  # noqa: E402
from ModTools_5_4.app.logging_setup import configure_logging  # noqa: E402
from ModTools_5_4.project.civ_project import save_civ_project  # noqa: E402
from ModTools_5_4.ui.main_window import MainWindow  # noqa: E402
from tests.sample_project import build_sample_project  # noqa: E402


class AiControlTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.window = MainWindow(config)
        cls.window.show()
        cls.page = cls.window.workspace_page()
        cls.context = ControlContext(cls.window, cls.page)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # 每个用例打开同一份示例工程，隔离工作区状态
        project = build_sample_project()
        civ_path = Path(self._tmp.name) / "sample.CIV"
        save_civ_project(civ_path, project)
        self.window.open_project_file(civ_path)
        self.civ_path = civ_path

    # ── 注册表与基础动作 ──────────────────────────────────────────────────

    def test_ping_and_help(self) -> None:
        result = self.context.execute("ping", {})
        self.assertTrue(result["pong"])
        help_result = self.context.execute("help", {})
        names = {item["name"] for item in help_result["actions"]}
        for expected in ("open_project", "get_state", "generate_all", "civ6proj_create", "screenshot"):
            self.assertIn(expected, names)
        generate_all = next(item for item in help_result["actions"] if item["name"] == "generate_all")
        self.assertEqual(generate_all["version"], "1")
        self.assertEqual(generate_all["params"]["overwrite"]["enum"], ["ask", "all", "none"])

    def test_extension_actions_and_manifest_contract(self) -> None:
        result = self.context.execute("extension", {"operation": "init", "gameplay": True, "ui": True})
        self.assertTrue(result["ok"], result)
        manifest = self.context.execute("get_manifest", {})
        self.assertFalse(manifest["extension_errors"])
        self.assertEqual(len(manifest["extension_paths"]), 4)
        result = self.context.execute("extension", {"operation": "check"})
        self.assertTrue(result["ok"], result)
        saved = json.loads(self.civ_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["extensions"]["version"], 1)
        contract = next(a for a in self.context.execute("help", {})["actions"] if a["name"] == "extension")
        self.assertIn("init", contract["params"]["operation"]["enum"])
        core = next(entry["path"] for entry in saved["extensions"]["files"] if entry["id"] == "core")
        written = self.context.execute("project_file_write", {
            "relative_path": core,
            "content": "INSERT INTO Units (UnitType,Name) VALUES ('UNIT_SIQI_DEMO','duplicate');",
        })
        self.assertTrue(written["ok"], written)
        blocked = self.context.execute("generate_all", {"overwrite": "all"})
        self.assertEqual(blocked.get("error"), "extensions_invalid", blocked)
        self.assertTrue(any(issue.get("table") == "Units" for issue in blocked["issues"]))

    def test_unknown_action_raises(self) -> None:
        with self.assertRaises(AiActionError):
            self.context.execute("no_such_action", {})

    def test_open_project_and_get_state(self) -> None:
        state = self.context.execute("get_state", {})
        self.assertEqual(state["project_name"], "示例工程")
        self.assertTrue(state["has_active_session"])
        self.assertEqual(state["file_path"], str(self.civ_path))
        sections = state["sections"]
        self.assertEqual(sections["文明"]["kind"], "list")
        self.assertGreater(sections["文明"]["count"], 0)
        entry = sections["文明"]["entries"][0]
        self.assertEqual(entry["type"], "CIVILIZATION_SIQI_DEMO")
        self.assertIn("基础信息", sections)
        self.assertEqual(state["required_missing"], [])

    def test_save_project(self) -> None:
        target = Path(self._tmp.name) / "saved.CIV"
        result = self.context.execute("save_project", {"path": str(target)})
        self.assertTrue(target.exists())
        self.assertEqual(result["path"], str(target))

    def test_get_manifest_without_civ6proj(self) -> None:
        manifest = self.context.execute("get_manifest", {})
        self.assertFalse(manifest["can_generate"])
        self.assertIsNone(manifest["civ6proj_path"])

    # ── civ6proj 创建 + 一键生成（非交互） ────────────────────────────────

    def test_civ6proj_create_and_generate_all(self) -> None:
        target_dir = Path(self._tmp.name) / "mod"
        created = self.context.execute(
            "civ6proj_create",
            {"directory": str(target_dir), "file_name": "Ai_Test_Mod"},
        )
        self.assertTrue(created["ok"])
        proj_path = Path(created["civ6proj"])
        self.assertTrue(proj_path.exists())
        art_path = created["art_xml"]
        self.assertTrue(art_path and Path(art_path).exists())

        state = self.context.execute("get_state", {})
        self.assertTrue(state["project_info"]["civ6proj_exists"])
        self.assertEqual(state["project_info"]["file_name"], "Ai_Test_Mod")

        manifest = self.context.execute("get_manifest", {})
        self.assertTrue(manifest["can_generate"])
        self.assertIn("Data/Ai_Test_Mod_Units.sql", manifest["files"])

        generated = self.context.execute("generate_all", {"overwrite": "all"})
        self.assertTrue(generated["ok"], f"generate_all 失败：{generated}")
        self.assertGreater(generated["written"], 0)
        self.assertTrue((target_dir / "Ai_Test_Mod.civ6proj").exists())
        self.assertTrue((target_dir / "Data" / "Ai_Test_Mod_Units.sql").exists())

        # 再次生成：文件已存在且策略 none → 全部跳过
        second = self.context.execute("generate_all", {"overwrite": "none"})
        self.assertTrue(second["ok"])
        self.assertEqual(second["written"], 0)
        self.assertGreater(second["skipped"], 0)

    def test_generate_all_bad_policy(self) -> None:
        with self.assertRaises(AiActionError):
            self.context.execute("generate_all", {"overwrite": "sometimes"})

    def test_generate_file_non_interactive(self) -> None:
        target_dir = Path(self._tmp.name) / "mod2"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "Ai_Test_Mod2"})
        rel = "Data/Ai_Test_Mod2_Units.sql"
        result = self.context.execute("generate_file", {"relative_path": rel, "overwrite": True})
        self.assertTrue(result["ok"], f"generate_file 失败：{result}")
        self.assertTrue((target_dir / rel.replace("/", os.sep)).exists())

    def test_generate_all_without_civ6proj_returns_error(self) -> None:
        result = self.context.execute("generate_all", {"overwrite": "all"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "no_civ6proj")

    # ── 一键配置 / 截图 / 导入 ────────────────────────────────────────────

    def test_quick_config_scans_project_files(self) -> None:
        target_dir = Path(self._tmp.name) / "mod3"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "Ai_Test_Mod3"})
        # 往工程目录放一个外部 SQL，一键配置应自动追加 UpdateDatabase 动作
        data_dir = target_dir / "Data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "external_extra.sql").write_text("-- external", encoding="utf-8")
        result = self.context.execute("quick_config", {})
        self.assertTrue(result["ok"], f"quick_config 失败：{result}")
        self.assertGreaterEqual(result["added_files"], 1)

    def test_quick_config_without_civ6proj(self) -> None:
        self.page.create_new_project("无工程文件")
        result = self.context.execute("quick_config", {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "no_civ6proj")

    def test_screenshot_saves_png(self) -> None:
        target = Path(self._tmp.name) / "shot.png"
        result = self.context.execute("screenshot", {"path": str(target)})
        self.assertTrue(target.exists())
        self.assertGreater(target.stat().st_size, 0)
        self.assertEqual(result["path"], str(target))

    def test_import_from_db_unknown_section(self) -> None:
        result = self.context.execute("import_from_db", {"section": "不存在的分类", "type": "X"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "unsupported_section")

    def test_skill_action_searches_local_skills(self) -> None:
        """AI 通道也能查本地技能库（与 modgen skill 同引擎）。"""
        from ModTools_5_4.skills_search import default_skills_root

        if not default_skills_root().exists():
            self.skipTest("仓库根 skills/ 不存在")
        result = self.context.execute("skill", {"keyword": "Modifier", "limit": 5})
        self.assertTrue(result["results"], "技能库应能搜到 Modifier 相关文件")
        self.assertGreaterEqual(result["count"], 1)
        first = str(result["results"][0]["rel"])
        full = self.context.execute("skill", {"file": first})
        self.assertIn("content", full)
        self.assertTrue(full["content"])

    def test_skill_action_plan_and_section_read(self) -> None:
        plan = self.context.execute("skill", {"keyword": "UI 按钮", "plan": True})
        self.assertIn("05-modtools-civ/ui-assets.md", plan["reading_plan"]["required"])
        result = self.context.execute("skill", {"keyword": "独立UI纹理", "limit": 1})
        item = result["results"][0]
        self.assertIn("start_line", item)
        self.assertIn("reading_plan", result)
        section = self.context.execute("skill", {"file": item["rel"], "section": item["section"]})
        self.assertIn("ui_textures", section["content"])
        from ModTools_5_4.ai.control_server import AiActionError
        with self.assertRaises(AiActionError):
            self.context.execute("skill", {"keyword": "UI", "section": "无文件"})

    def test_check_conflicts_action(self) -> None:
        """AI 通道可检测自定义 SQL × 生成 SQL 冲突（先保存工程）。"""
        target_dir = Path(self._tmp.name) / "mod_cc"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "CC_Mod"})
        self.context.execute(
            "project_file_write",
            {"relative_path": "Data/Clash.sql",
             "content": "INSERT INTO Units (UnitType, Name) VALUES ('UNIT_SIQI_DEMO','X');"},
        )
        self.context.execute("save_project", {"path": str(self.civ_path)})
        result = self.context.execute("check_conflicts", {})
        self.assertFalse(result["ok"])
        self.assertTrue(result["errors"], result)
        self.assertEqual(result["errors"][0]["table"], "Units")

    # ── 自定义文件通道（SQL/XML/Lua）──────────────────────────────────────

    def test_project_file_write_auto_registers_action(self) -> None:
        target_dir = Path(self._tmp.name) / "mod_cf"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "CF_Mod"})
        result = self.context.execute(
            "project_file_write",
            {"relative_path": "Scripts/Init.lua", "content": "function Initialize()\nend\n"},
        )
        self.assertTrue(result["ok"], result)
        self.assertTrue((target_dir / "Scripts" / "Init.lua").exists())
        state = self.context.execute("get_state", {})
        in_game = state["file_info"]["in_game_actions"]
        self.assertTrue(
            any(a["type"] == "AddGameplayScripts" and "Scripts/Init.lua" in a["files"] for a in in_game),
            f"一键配置语义应自动注册 AddGameplayScripts：{in_game}",
        )
        self.assertIn("Scripts/Init.lua", state["custom_files"])
        self.assertEqual(state["project_info"]["project_root"], str(target_dir))

    def test_project_file_write_explicit_action_and_read(self) -> None:
        target_dir = Path(self._tmp.name) / "mod_cf2"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "CF_Mod2"})
        content = "INSERT INTO Types VALUES ('TYPE_CF', 'KIND_CF');"
        result = self.context.execute(
            "project_file_write",
            {"relative_path": "Data/Custom.sql", "content": content, "action_type": "UpdateDatabase"},
        )
        self.assertTrue(result["ok"], result)
        read = self.context.execute("project_file_read", {"relative_path": "Data/Custom.sql"})
        self.assertTrue(read["ok"])
        self.assertEqual(read["content"], content)

    def test_project_file_list_and_delete(self) -> None:
        target_dir = Path(self._tmp.name) / "mod_cf3"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "CF_Mod3"})
        self.context.execute("project_file_write", {"relative_path": "Scripts/A.lua", "content": "x"})
        listing = self.context.execute("project_file_list", {})
        self.assertTrue(listing["ok"])
        paths = {item["path"] for item in listing["files"]}
        self.assertIn("Scripts/A.lua", paths)
        deleted = self.context.execute("project_file_delete", {"relative_path": "Scripts/A.lua"})
        self.assertTrue(deleted["ok"], deleted)
        self.assertTrue(deleted["deleted_file"])
        self.assertGreaterEqual(deleted["removed_actions"], 1)
        after = self.context.execute("project_file_list", {})
        self.assertNotIn("Scripts/A.lua", {item["path"] for item in after["files"]})

    def test_project_file_write_rejects_traversal(self) -> None:
        target_dir = Path(self._tmp.name) / "mod_cf4"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "CF_Mod4"})
        result = self.context.execute("project_file_write", {"relative_path": "../evil.lua", "content": "x"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "invalid_path")
        self.assertFalse((Path(self._tmp.name) / "evil.lua").exists())

    def test_add_file_action(self) -> None:
        target_dir = Path(self._tmp.name) / "mod_cf5"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "CF_Mod5"})
        result = self.context.execute(
            "add_file_action",
            {"type": "UpdateIcons", "files": ["Icons/My_Icons.xml"]},
        )
        self.assertTrue(result["ok"], result)
        state = self.context.execute("get_state", {})
        self.assertTrue(any(a["type"] == "UpdateIcons" for a in state["file_info"]["front_end_actions"]))
        self.assertTrue(any(a["type"] == "UpdateIcons" for a in state["file_info"]["in_game_actions"]))

    def test_custom_file_flows_through_generate_all(self) -> None:
        """端到端：自定义 Lua 写入 → 动作注册 → 一键生成原样透传 + civ6proj 引用。"""
        target_dir = Path(self._tmp.name) / "mod_cf6"
        self.context.execute("civ6proj_create", {"directory": str(target_dir), "file_name": "CF_Mod6"})
        lua_content = "function Initialize()\nend\n"
        self.context.execute("project_file_write", {"relative_path": "Scripts/Game.lua", "content": lua_content})
        manifest = self.context.execute("get_manifest", {})
        self.assertIn("Scripts/Game.lua", manifest["files"], manifest["files"])
        generated = self.context.execute("generate_all", {"overwrite": "all"})
        self.assertTrue(generated["ok"], generated)
        self.assertEqual((target_dir / "Scripts" / "Game.lua").read_text(encoding="utf-8"), lua_content)
        proj_text = (target_dir / "CF_Mod6.civ6proj").read_text(encoding="utf-8")
        self.assertIn("Scripts\\Game.lua", proj_text)
        self.assertIn("AddGameplayScripts", proj_text)


class ControlServerBridgeTestCase(unittest.TestCase):
    """Qt 桥 + HTTP 服务器（手动驱动事件循环）。"""

    @classmethod
    def setUpClass(cls) -> None:
        config = load_config()
        configure_logging(config.log_dir, config.debug)
        cls.app = QApplication.instance() or QApplication([])
        cls.window = MainWindow(config)
        cls.window.show()
        cls.context = ControlContext(cls.window, cls.window.workspace_page())

    def _pump(self, seconds: float = 2.0) -> None:
        deadline = time.time() + seconds
        while time.time() < deadline:
            self.app.processEvents()
            time.sleep(0.005)

    def test_submit_runs_on_main_thread_via_timer(self) -> None:
        server = ControlServer(self.context, port=0)
        self.addCleanup(server.shutdown)
        envelope = {"action": "ping", "params": {}, "event": threading.Event(), "response": None}
        server._queue.put(envelope)
        self._pump()
        self.assertTrue(envelope["event"].is_set(), "Qt 桥未在事件循环中执行动作")
        self.assertTrue(envelope["response"]["ok"])
        self.assertTrue(envelope["response"]["result"]["pong"])

    def test_http_endpoint_roundtrip(self) -> None:
        server = ControlServer(self.context, port=0)
        server.start()
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.port}/api"

        def _post_and_pump(payload: dict) -> dict:
            # 请求必须在工作线程发出，主线程负责泵事件循环驱动 Qt 桥
            received: list[dict] = []

            def _client() -> None:
                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    received.append(json.loads(resp.read().decode("utf-8")))

            thread = threading.Thread(target=_client, daemon=True)
            thread.start()
            thread.join(timeout=1)
            deadline = time.time() + 10
            while not received and time.time() < deadline:
                self.app.processEvents()
                time.sleep(0.005)
            thread.join(timeout=10)
            self.assertTrue(received, "HTTP 请求未返回")
            return received[0]

        ping = _post_and_pump({"action": "ping"})
        self.assertTrue(ping["ok"])
        self.assertTrue(ping["result"]["pong"])

        bad = _post_and_pump({"action": "no_such_action"})
        self.assertFalse(bad["ok"])
        self.assertIn("未知动作", bad["error"])

    def test_http_token_required(self) -> None:
        server = ControlServer(self.context, port=0, token="secret-token")
        server.start()
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.port}/health"

        def _get(headers: dict) -> tuple[int, dict]:
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.status, json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

        code, body = _get({})
        self.assertEqual(code, 403)
        self.assertFalse(body["ok"])
        code, body = _get({"X-ModTools-Token": "secret-token"})
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])


class AiExecCliTestCase(unittest.TestCase):
    def test_parse_cli_ai_args(self) -> None:
        cleaned, port, token, execs, headless = _parse_cli_ai_args(
            ["工程.CIV", "--ai-port", "8765", "--ai-token=abc", "--ai-exec", '{"action":"ping"}', "--headless"]
        )
        self.assertEqual(cleaned, ["工程.CIV"])
        self.assertEqual(port, 8765)
        self.assertEqual(token, "abc")
        self.assertEqual(execs, ['{"action":"ping"}'])
        self.assertTrue(headless)

    def test_parse_cli_ai_args_defaults(self) -> None:
        cleaned, port, token, execs, headless = _parse_cli_ai_args(["工程.CIV", "--other", "x"])
        self.assertEqual(cleaned, ["工程.CIV", "--other", "x"])
        self.assertIsNone(port)
        self.assertIsNone(token)
        self.assertEqual(execs, [])
        self.assertFalse(headless)

    def test_parse_ai_exec_requests(self) -> None:
        requests = parse_ai_exec_requests(['{"action": "ping"}', '[{"action": "help"}, {"action": "ping"}]'])
        self.assertEqual([item["action"] for item in requests], ["ping", "help", "ping"])
        with self.assertRaises(ValueError):
            parse_ai_exec_requests(["not json"])

    def test_run_ai_requests_and_emit(self) -> None:
        config = load_config()
        app = QApplication.instance() or QApplication([])
        window = MainWindow(config)
        context = ControlContext(window, window.workspace_page())
        results = run_ai_requests(
            context,
            [
                {"action": "ping"},
                {"action": "no_such_action"},
                {"action": "ping", "params": {}},
            ],
        )
        self.assertTrue(results[0]["response"]["ok"])
        self.assertFalse(results[1]["response"]["ok"])
        self.assertTrue(results[2]["response"]["ok"])
        with tempfile.TemporaryDirectory() as tmp:
            result_path = Path(tmp) / "ai_exec_result.json"
            emit_exec_results(results, result_path)
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertFalse(payload["all_ok"])
            self.assertEqual(len(payload["requests"]), 3)
        window.close()


if __name__ == "__main__":
    unittest.main()
