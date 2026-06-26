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
            self._tools.append({
                "type": "function",
                "function": {
                    "name": td.name,
                    "description": td.description,
                    "parameters": td.parameters,
                },
            })

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
            # Model wants to call tools
            msg = ChatMessage.assistant(content="", tool_calls=tool_calls)
            self._messages.append(msg)
            self.thinking.emit(f"调用 {len(tool_calls)} 个工具...")

            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                logger.info("Tool call: %s(%s)", name, args)
                result = self._executor.execute(name, args)
                result_str = json.dumps(result, ensure_ascii=False, default=str)
                self._messages.append(ChatMessage.tool(
                    content=result_str,
                    tool_call_id=tc.get("id", name),
                    name=name,
                ))
                # Check if this is a propose tool
                from .tools import TOOL_DEFS
                for td in TOOL_DEFS:
                    if td.name == name and td.requires_preview:
                        self._pending_proposal = result
                        break

            self._tool_iteration += 1
            if self._tool_iteration >= MAX_TOOL_ITERATIONS:
                self.error_occurred.emit("工具调用次数过多，可能陷入循环。请尝试更具体的描述。")
                return

            self._call_llm()
        else:
            # Final text response
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
