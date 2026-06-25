"""Chat message dataclass for agent conversation history."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ChatMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None
    name: str | None = None

    def to_openai_dict(self) -> dict:
        d: dict = {"role": self.role, "content": self.content}
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            d["tool_calls"] = self.tool_calls
        if self.name is not None:
            d["name"] = self.name
        return d

    @classmethod
    def system(cls, content: str) -> ChatMessage:
        return cls(role="system", content=content)

    @classmethod
    def user(cls, content: str) -> ChatMessage:
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str, tool_calls: list[dict] | None = None) -> ChatMessage:
        return cls(role="assistant", content=content, tool_calls=tool_calls)

    @classmethod
    def tool(cls, content: str, tool_call_id: str, name: str) -> ChatMessage:
        return cls(role="tool", content=content, tool_call_id=tool_call_id, name=name)
