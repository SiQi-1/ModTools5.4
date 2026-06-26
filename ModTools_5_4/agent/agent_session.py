"""Agent conversation session — manages message history, tool-calling loop."""

from __future__ import annotations

import json
import logging
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from .chat_message import ChatMessage
from .llm_backend import LlmBackend
from .tool_executor import ToolExecutor

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10
MAX_HISTORY_MESSAGES = 30


class AgentSession(QObject):
    response_started = pyqtSignal()
    response_chunk = pyqtSignal(str)
    response_finished = pyqtSignal(str)         # Full accumulated response text
    preview_ready = pyqtSignal(dict, str)        # proposal dict, description
    thinking = pyqtSignal(str)                   # Status message during tool execution
    error_occurred = pyqtSignal(str)

    def __init__(self, llm_backend: LlmBackend, tool_executor: ToolExecutor,
                 system_prompt_text: str, parent: QObject | None = None):
        super().__init__(parent)
        self._llm = llm_backend
        self._executor = tool_executor
        self._system_prompt = system_prompt_text
        self._messages: list[ChatMessage] = []
        self._tools: list[dict] = []
        self._pending_proposal: dict | None = None
        self._accumulated_response = ""
        self._tool_iteration = 0
        self._build_tools_list()

    def _build_tools_list(self) -> None:
        from .tools import TOOL_DEFS
        for td in TOOL_DEFS:
            self._tools.append(td.to_openai_dict_legacy())

    def accept_proposal(self) -> None:
        """Feed proposal acceptance back to the model so it can continue."""
        self._messages.append(ChatMessage.user("变更已应用，可以继续下一步。"))
        self._pending_proposal = None
        self._tool_iteration = 0
        self.response_started.emit()
        self._call_llm()

    def reset(self) -> None:
        self._messages.clear()
        self._pending_proposal = None
        self._tool_iteration = 0

    def send_user_message(self, text: str) -> None:
        self._tool_iteration = 0
        self._pending_proposal = None
        self._accumulated_response = ""

        if not self._messages:
            self._messages.append(ChatMessage.system(self._system_prompt))
        self._messages.append(ChatMessage.user(text))

        self.response_started.emit()
        self._call_llm()

    def _call_llm(self) -> None:
        openai_msgs = [m.to_openai_dict() for m in self._messages]
        self._llm.send_message(
            openai_msgs,
            tools=self._tools,
            callback=self._on_llm_response,
            stream=False,
        )

    def _on_llm_response(self, response: dict) -> None:
        message = response.get("message", {})
        content = message.get("content", "") or ""
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            msg = ChatMessage.assistant(content="", tool_calls=tool_calls)
            self._messages.append(msg)

            tool_details = []
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                args_brief = ", ".join(
                    f"{k}={repr(v)[:40]}" for k, v in args.items()
                ) or "无参数"
                logger.info("Tool call %d: %s(%s)", self._tool_iteration + 1, name, args)
                result = self._executor.execute(name, args)
                result_str = json.dumps(result, ensure_ascii=False, default=str)

                # Summarize result
                if "error" in result:
                    summary = f"❌ {result['error']}"
                elif "results" in result:
                    summary = f"找到 {len(result['results'])} 个结果"
                elif "entries" in result:
                    summary = f"返回 {result.get('count', len(result['entries']))} 个条目"
                elif "count" in result:
                    summary = f"{result['count']} 个条目"
                elif "data" in result:
                    summary = "获取到数据"
                else:
                    summary = "完成"

                self.thinking.emit(f"[{self._tool_iteration + 1}/{MAX_TOOL_ITERATIONS}] {name}({args_brief}) → {summary}")
                tool_details.append(f"🔧 `{name}`: {summary}")

                self._messages.append(ChatMessage.tool(
                    content=result_str,
                    tool_call_id=tc.get("id", name),
                    name=name,
                ))
                from .tools import TOOL_DEFS
                if "error" not in result:
                    for td in TOOL_DEFS:
                        if td.name == name and td.requires_preview:
                            self._pending_proposal = result
                            break

            self._tool_iteration += 1
            if self._tool_iteration >= MAX_TOOL_ITERATIONS:
                self.error_occurred.emit(
                    f"已达到最大工具调用次数({MAX_TOOL_ITERATIONS})。\n"
                    f"最后调用：{tool_details[-1] if tool_details else '无'}\n"
                    f"请尝试更具体的描述。"
                )
                return

            # If propose tools called, emit preview and stop
            if self._pending_proposal is not None:
                self.response_finished.emit("")
                description = self._pending_proposal.get("description", "变更提案")
                self.preview_ready.emit(self._pending_proposal, description)
                return

            self._call_llm()
        else:
            # Final text response (no more tool calls)
            msg = ChatMessage.assistant(content=content)
            self._messages.append(msg)
            self.response_finished.emit(content)

            if self._pending_proposal:
                description = self._pending_proposal.get("description", "变更提案")
                self.preview_ready.emit(self._pending_proposal, description)

        self._prune_history()

    def _prune_history(self) -> None:
        system_msgs = [m for m in self._messages if m.role == "system"]
        other_msgs = [m for m in self._messages if m.role != "system"]
        if len(other_msgs) > MAX_HISTORY_MESSAGES:
            self._messages = system_msgs + other_msgs[-MAX_HISTORY_MESSAGES:]
