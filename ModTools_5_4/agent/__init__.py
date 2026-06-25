"""AI Agent system for ModTools 5.4.

Provides natural-language-driven workspace editing via local LLM (Ollama-compatible).
"""


def __getattr__(name):
    if name == "ChatMessage":
        from .chat_message import ChatMessage as _c
        return _c
    if name == "LlmBackend":
        from .llm_backend import LlmBackend as _l
        return _l
    if name == "TOOL_DEFS":
        from .tools import TOOL_DEFS as _t
        return _t
    if name == "ToolExecutor":
        from .tool_executor import ToolExecutor as _e
        return _e
    if name == "AgentSession":
        from .agent_session import AgentSession as _s
        return _s
    if name == "build_system_prompt":
        from .system_prompt import build_system_prompt as _b
        return _b
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ChatMessage",
    "LlmBackend",
    "TOOL_DEFS",
    "ToolExecutor",
    "AgentSession",
    "build_system_prompt",
]
