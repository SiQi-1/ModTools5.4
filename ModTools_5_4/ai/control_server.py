"""AI 控制接口：让外部 AI agent 打开并驱动 ModTools GUI。

设计（2026-08 新增）：
- **动作注册表 `ControlContext`**：同一套动作（打开工程 / 状态快照 / 导出清单 /
  一键生成 / 新建 .civ6proj / 一键配置 / 游戏库导入 / 能力搜索 / 截图）同时供
  HTTP 服务器与 CLI 一次性执行（`--ai-exec`）共用，无两份实现；
- **HTTP 服务器 `ControlServer`**：仅绑定 127.0.0.1，请求经队列 + QTimer 桥接到
  Qt 主线程执行（GUI 操作必须在主线程）；可选 token 校验；
- 所有动作结果统一为 JSON：`{"ok": true, "result": ...}` / `{"ok": false, "error": ...}`。

注意：这是给**外部 AI** 的驱动接口，不是 2026-06-30 移除的应用内置 agent 功能。
"""
from __future__ import annotations

import json
import logging
import queue
import sqlite3
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import QTimer

from ..application import GenerationService
from .contracts import ActionContract, make_action_contract

LOGGER = logging.getLogger(__name__)

ActionHandler = Callable[["ControlContext", dict[str, Any]], dict[str, Any]]


class AiActionError(ValueError):
    """动作执行失败（HTTP 返回 ok:false，CLI 计入失败）。"""


class ControlContext:
    """AI 动作的执行环境与注册表。"""

    def __init__(self, main_window, workspace_page) -> None:
        self.main_window = main_window
        self.workspace_page = workspace_page
        self.generation_service = GenerationService()
        self._actions: dict[str, tuple[ActionContract, ActionHandler]] = {}
        self._register_builtin_actions()

    # ── 注册表 ────────────────────────────────────────────────────────────

    def register(self, name: str, description: str, handler: ActionHandler) -> None:
        contract = make_action_contract(name, description)
        self._actions[contract.name] = (contract, handler)

    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        spec = self._actions.get(str(action or "").strip())
        if spec is None:
            raise AiActionError(f"未知动作：{action}（可用动作见 help）")
        try:
            result = spec[1](self, dict(params or {}))
        except AiActionError:
            raise
        except Exception as exc:
            raise AiActionError(f"{action} 执行失败：{exc}") from exc
        if not isinstance(result, dict):
            result = {"value": result}
        return result

    def help_text(self) -> list[dict[str, object]]:
        return [
            contract.to_dict()
            for _name, (contract, _handler) in sorted(self._actions.items())
        ]

    def action_contracts(self) -> list[ActionContract]:
        """Return the registered action contracts for adapters and tests."""
        return [contract for _name, (contract, _handler) in sorted(self._actions.items())]

    # ── 内置动作 ──────────────────────────────────────────────────────────

    def _require_workspace(self):
        if self.workspace_page is None:
            raise AiActionError("工作区不可用")

    def _register_builtin_actions(self) -> None:
        ctx = self

        def _h_ping(_ctx, _params):
            ws = ctx.workspace_page
            return {
                "pong": True,
                "project": ws.project_name() if ws is not None else None,
                "has_active_session": bool(ws is not None and ws.has_active_session()),
            }

        def _h_help(_ctx, _params):
            return {"actions": ctx.help_text()}

        def _h_open_project(_ctx, params):
            raw = str(params.get("path") or "").strip()
            if not raw:
                raise AiActionError("缺少参数 path")
            target = Path(raw)
            if not target.exists():
                raise AiActionError(f"文件不存在：{target}")
            ctx.main_window.open_project_file(target)
            ws = ctx.workspace_page
            return {"path": str(target), "project": ws.project_name() if ws is not None else None}

        def _h_save_project(_ctx, params):
            ctx._require_workspace()
            ws = ctx.workspace_page
            raw = str(params.get("path") or "").strip()
            target = Path(raw) if raw else None
            saved = ws.save_project(target)
            return {"path": str(saved)}

        def _h_get_state(_ctx, _params):
            ctx._require_workspace()
            return ctx.workspace_page.ai_get_state()

        def _h_get_manifest(_ctx, _params):
            ctx._require_workspace()
            ws = ctx.workspace_page
            manifest = ctx.generation_service.manifest(ws)
            return manifest.to_dict()

        def _h_generate_all(_ctx, params):
            ctx._require_workspace()
            ws = ctx.workspace_page
            policy = str(params.get("overwrite") or "ask").strip().lower()
            if policy not in {"ask", "all", "none"}:
                raise AiActionError("overwrite 只能是 ask / all / none")
            result = ctx.generation_service.generate_all(ws, overwrite_policy=policy)
            if result is None:
                return {"ok": True, "interactive": True}
            return result

        def _h_generate_file(_ctx, params):
            ctx._require_workspace()
            ws = ctx.workspace_page
            rel = str(params.get("relative_path") or "").strip()
            if not rel:
                raise AiActionError("缺少参数 relative_path")
            overwrite = params.get("overwrite") if "overwrite" in params else None
            if overwrite is not None and not isinstance(overwrite, bool):
                raise AiActionError("overwrite 需为布尔值或省略")
            result = ctx.generation_service.generate_file(ws, rel, overwrite=overwrite)
            if result is None:
                return {"ok": True, "interactive": True}
            return result

        def _h_civ6proj_create(_ctx, params):
            ctx._require_workspace()
            fields = params.get("fields")
            if fields is not None and not isinstance(fields, dict):
                raise AiActionError("fields 需为 JSON 对象")
            return ctx.workspace_page.ai_create_civ6proj(
                directory=str(params.get("directory") or "").strip() or None,
                file_name=str(params.get("file_name") or "").strip() or None,
                fields=fields,
                create_art_xml=bool(params.get("create_art_xml", True)),
            )

        def _h_quick_config(_ctx, _params):
            ctx._require_workspace()
            return ctx.workspace_page.ai_run_quick_config()

        def _h_import_from_db(_ctx, params):
            ctx._require_workspace()
            section = str(params.get("section") or "").strip()
            obj_type = str(params.get("type") or "").strip()
            if not section or not obj_type:
                raise AiActionError("缺少参数 section / type")
            return ctx.workspace_page.ai_import_entry_from_db(
                section, obj_type, replace=bool(params.get("replace", False))
            )

        def _h_project_file_write(_ctx, params):
            ctx._require_workspace()
            rel = str(params.get("relative_path") or "").strip()
            content = params.get("content")
            if not rel or not isinstance(content, str):
                raise AiActionError("缺少参数 relative_path / content（content 为文本字符串）")
            return ctx.workspace_page.ai_project_file_write(
                rel,
                content,
                register_action=bool(params.get("register_action", True)),
                action_type=str(params.get("action_type") or "").strip(),
            )

        def _h_project_file_read(_ctx, params):
            ctx._require_workspace()
            rel = str(params.get("relative_path") or "").strip()
            if not rel:
                raise AiActionError("缺少参数 relative_path")
            return ctx.workspace_page.ai_project_file_read(rel)

        def _h_project_file_list(_ctx, _params):
            ctx._require_workspace()
            return ctx.workspace_page.ai_project_file_list()

        def _h_project_file_delete(_ctx, params):
            ctx._require_workspace()
            rel = str(params.get("relative_path") or "").strip()
            if not rel:
                raise AiActionError("缺少参数 relative_path")
            return ctx.workspace_page.ai_project_file_delete(
                rel, remove_action=bool(params.get("remove_action", True))
            )

        def _h_add_file_action(_ctx, params):
            ctx._require_workspace()
            action_type = str(params.get("type") or params.get("action_type") or "").strip()
            files = params.get("files")
            if not action_type or not isinstance(files, list):
                raise AiActionError("缺少参数 type / files（files 为相对路径数组）")
            try:
                load_order = max(0, int(params.get("load_order") or 0))
            except (TypeError, ValueError):
                load_order = 0
            return ctx.workspace_page.ai_add_file_action(
                action_type=action_type,
                action_id=str(params.get("id") or "").strip(),
                files=[str(item) for item in files],
                load_order=load_order,
            )

        def _h_skill(_ctx, params):
            keyword = str(params.get("keyword") or "").strip()
            raw_file = str(params.get("file") or "").strip()
            if not keyword and not raw_file:
                raise AiActionError("缺少参数 keyword（或 file 直接读全文）")
            try:
                limit = max(1, min(100, int(params.get("limit") or 10)))
            except (TypeError, ValueError):
                limit = 10

            from .. import skills_search

            section = str(params.get("section") or "").strip()
            if section and not raw_file:
                raise AiActionError("section 需要配合 file")
            if raw_file:
                content = skills_search.read_skill_file(raw_file, section=section)
                if content is None:
                    raise AiActionError(f"技能文件不存在或路径非法：{raw_file}")
                return {"file": raw_file, "content": content}
            plan = skills_search.reading_plan(keyword)
            if params.get("plan"):
                return {"reading_plan": plan}
            results = skills_search.search_skills(keyword, limit=limit)
            return {"results": results, "count": len(results), "reading_plan": plan}

        def _h_check_conflicts(_ctx, _params):
            """自定义 SQL × 生成 SQL 冲突检测（需已保存的 .CIV + modgen 源码环境）。"""
            ctx._require_workspace()
            ws = ctx.workspace_page
            civ_path = ws.project_file_path()
            if civ_path is None:
                raise AiActionError("工程尚未保存：先执行 save_project 再检测")
            try:
                from modgen.custom_conflicts import check_conflicts
            except ImportError as exc:
                raise AiActionError(f"check_conflicts 需要 modgen（源码环境）：{exc}") from exc
            result = check_conflicts(civ_path)
            result["ok"] = not result["errors"]
            return result

        def _h_search(_ctx, params):
            keyword = str(params.get("keyword") or "").strip()
            if not keyword:
                raise AiActionError("缺少参数 keyword")
            try:
                limit = max(1, min(500, int(params.get("limit") or 20)))
            except (TypeError, ValueError):
                limit = 20
            category = str(params.get("category") or "").strip() or None

            from ..app.settings_store import load_settings
            from ..db import ability_search
            from ..db.paths import DEFAULT_GAME_DB

            settings = load_settings()
            game_db = Path(str(settings.game_db_path or "")).expanduser()
            if not game_db.exists() and DEFAULT_GAME_DB.exists():
                game_db = DEFAULT_GAME_DB
            if not game_db.exists():
                raise AiActionError("未找到游戏数据库：请先在设置页配置，或至少运行过一次文明6")

            loc_conn = None
            text_db = Path(str(settings.active_text_db_path or "")).expanduser()
            if text_db.exists():
                try:
                    loc_conn = sqlite3.connect(str(text_db))
                except sqlite3.Error:
                    loc_conn = None
            conn = sqlite3.connect(str(game_db))
            try:
                res = ability_search.search_all(
                    conn, loc_conn, keyword, category=category, limit=limit
                )
                return {
                    "results": res.get("results") or [],
                    "hint": res.get("hint") or "",
                    "expansions": res.get("expansions") or [],
                }
            finally:
                conn.close()
                if loc_conn is not None:
                    loc_conn.close()

        def _h_screenshot(_ctx, params):
            window = ctx.main_window
            raw = str(params.get("path") or "").strip()
            if raw:
                target = Path(raw)
            else:
                target = Path(tempfile.gettempdir()) / f"modtools_screenshot_{int(time.time() * 1000)}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            pixmap = window.grab()
            if not pixmap.save(str(target), "PNG"):
                raise AiActionError("截图保存失败")
            return {"path": str(target), "width": pixmap.width(), "height": pixmap.height()}

        self.register("ping", "连通性检查", _h_ping)
        self.register("help", "列出全部可用动作与说明", _h_help)
        self.register("open_project", "打开 .CIV 工程（path）", _h_open_project)
        self.register("save_project", "保存当前工程（可选 path）", _h_save_project)
        self.register("get_state", "工程状态快照：分区/条目/必填缺失/基础信息", _h_get_state)
        self.register("get_manifest", "将导出文件清单（与一键生成同源）", _h_get_manifest)
        self.register("generate_all", "一键生成全部文件（overwrite: ask|all|none）", _h_generate_all)
        self.register("generate_file", "生成单个文件（relative_path, overwrite?）", _h_generate_file)
        self.register("civ6proj_create", "新建 ModBuddy 兼容 .civ6proj（directory/file_name/fields/create_art_xml）", _h_civ6proj_create)
        self.register("quick_config", "一键配置：扫描工程目录追加文件动作", _h_quick_config)
        self.register("import_from_db", "从游戏库导入条目（section/type/replace?）", _h_import_from_db)
        self.register("project_file_write", "写自定义 SQL/XML/Lua 文件进工程目录并注册动作（relative_path/content/register_action?/action_type?）", _h_project_file_write)
        self.register("project_file_read", "读取工程目录文件内容（relative_path）", _h_project_file_read)
        self.register("project_file_list", "列出工程目录文件与文件动作", _h_project_file_list)
        self.register("project_file_delete", "删除工程目录文件并可移除动作引用（relative_path/remove_action?）", _h_project_file_delete)
        self.register("add_file_action", "精确注册文件动作（type/files/id?/load_order?）", _h_add_file_action)
        self.register("search", "能力实现搜索（keyword/category?/limit?）", _h_search)
        self.register("skill", "本地技能库全文检索（keyword/limit?/file?，仓库根 skills/）", _h_skill)
        self.register("check_conflicts", "自定义 SQL × 生成 SQL 冲突检测（需先 save_project；modgen 源码环境）", _h_check_conflicts)
        self.register("screenshot", "主窗口截图存 PNG（path?）", _h_screenshot)


class ControlServer:
    """localhost HTTP 服务器 + Qt 主线程执行桥。"""

    def __init__(self, context: ControlContext, *, port: int = 8765, token: str | None = None) -> None:
        self.context = context
        self.token = (str(token).strip() or None) if token else None
        self._queue: queue.Queue = queue.Queue()
        # QTimer 必须在主线程创建（本类由 launch() 在主线程构造）
        self._timer = QTimer()
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._drain_queue)
        self._timer.start()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", int(port)), self._make_handler())
        self.port = int(self._httpd.server_address[1])
        self._thread: threading.Thread | None = None

    def _make_handler(self):
        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # noqa: D401 - 静默请求日志
                pass

            def _json(self, code: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except OSError:
                    pass

            def _authorized(self) -> bool:
                if server_ref.token is None:
                    return True
                return self.headers.get("X-ModTools-Token") == server_ref.token

            def do_GET(self) -> None:
                if not self._authorized():
                    self._json(403, {"ok": False, "error": "token 校验失败"})
                    return
                if self.path in ("/health", "/healthz"):
                    self._json(200, {"ok": True, "service": "modtools-ai-control"})
                    return
                self._json(404, {"ok": False, "error": "未知路径（POST /api 或 GET /health）"})

            def do_POST(self) -> None:
                if not self._authorized():
                    self._json(403, {"ok": False, "error": "token 校验失败"})
                    return
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                    raw = self.rfile.read(length) if length else b"{}"
                    data = json.loads(raw.decode("utf-8"))
                except Exception as exc:
                    self._json(400, {"ok": False, "error": f"请求体不是合法 JSON：{exc}"})
                    return
                if not isinstance(data, dict):
                    self._json(400, {"ok": False, "error": "请求体需为 JSON 对象"})
                    return
                action = str(data.get("action") or "").strip()
                params = data.get("params") if isinstance(data.get("params"), dict) else {}
                if not action:
                    self._json(400, {"ok": False, "error": "缺少 action 字段"})
                    return
                try:
                    timeout = float(data.get("timeout") or 120)
                except (TypeError, ValueError):
                    timeout = 120.0
                self._json(200, server_ref.submit(action, params, timeout=timeout))

        return Handler

    def submit(self, action: str, params: dict[str, Any], *, timeout: float = 120.0) -> dict[str, Any]:
        """HTTP 线程调用：入队并等待主线程执行结果。"""
        envelope: dict[str, Any] = {
            "action": action,
            "params": params,
            "event": threading.Event(),
            "response": None,
        }
        self._queue.put(envelope)
        if not envelope["event"].wait(timeout):
            return {"ok": False, "error": f"动作执行超时（{timeout}s，主线程可能被模态对话框阻塞）"}
        return envelope["response"]

    def _drain_queue(self) -> None:
        """主线程 QTimer 槽：清空队列并执行动作。"""
        while True:
            try:
                envelope = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                result = self.context.execute(envelope["action"], envelope["params"])
                envelope["response"] = {"ok": True, "result": result}
            except AiActionError as exc:
                envelope["response"] = {"ok": False, "error": str(exc)}
            except Exception as exc:  # noqa: BLE001 - 保证 HTTP 请求总能收到回包
                LOGGER.exception("[AI控制] 动作 %s 执行异常", envelope["action"])
                envelope["response"] = {"ok": False, "error": f"内部错误：{exc}"}
            envelope["event"].set()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True, name="modtools-ai-http")
        self._thread.start()

    def shutdown(self) -> None:
        # 注意：BaseServer.shutdown() 只能在 serve_forever 运行期间从其它线程调用，
        # 否则会死锁——因此仅在服务线程存活时调用
        if self._thread is not None and self._thread.is_alive():
            try:
                self._httpd.shutdown()
            except Exception:
                pass
        try:
            self._httpd.server_close()
        except Exception:
            pass
        self._timer.stop()


def parse_ai_exec_requests(raw_values: list[str]) -> list[dict[str, Any]]:
    """--ai-exec 参数解析：每个值为 JSON 对象或 JSON 数组。"""
    requests: list[dict[str, Any]] = []
    for raw in raw_values:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--ai-exec 参数不是合法 JSON：{exc}") from exc
        if isinstance(data, list):
            items = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            items = [data]
        else:
            raise ValueError("--ai-exec 参数需为 JSON 对象或对象数组")
        requests.extend(items)
    return requests


def run_ai_requests(context: ControlContext, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """主线程内顺序执行一组动作请求（--ai-exec 一次性模式）。"""
    results: list[dict[str, Any]] = []
    for req in requests:
        action = str(req.get("action") or "").strip()
        params = req.get("params") if isinstance(req.get("params"), dict) else {}
        if not action:
            results.append({"action": action, "response": {"ok": False, "error": "缺少 action 字段"}})
            continue
        try:
            results.append({"action": action, "response": {"ok": True, "result": context.execute(action, params)}})
        except AiActionError as exc:
            results.append({"action": action, "response": {"ok": False, "error": str(exc)}})
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("[AI控制] --ai-exec 动作 %s 执行异常", action)
            results.append({"action": action, "response": {"ok": False, "error": f"内部错误：{exc}"}})
    return results


def emit_exec_results(results: list[dict[str, Any]], result_path: Path) -> None:
    """输出 --ai-exec 结果：stdout（可用时）+ 结果文件（始终可查）。"""
    all_ok = all(bool(item["response"].get("ok")) for item in results)
    payload = json.dumps({"requests": results, "all_ok": all_ok}, ensure_ascii=False, indent=1)
    try:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(payload + "\n", encoding="utf-8")
    except OSError:
        pass
    if sys.stdout is not None:
        try:
            sys.stdout.write(payload + "\n")
            sys.stdout.flush()
        except OSError:
            pass



