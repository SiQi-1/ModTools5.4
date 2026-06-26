"""LLM backend supporting Ollama (local) and OpenAI-compatible (cloud) APIs.

Background-thread HTTP calls via QThread. Uses only stdlib.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
import logging

from PyQt6.QtCore import QThread, QObject, pyqtSignal

logger = logging.getLogger(__name__)

# API provider presets
PROVIDERS = {
    "ollama": {
        "label": "Ollama (本地)",
        "default_url": "http://127.0.0.1:11434",
        "chat_path": "/api/chat",
        "default_model": "qwen2.5:7b",
    },
    "deepseek": {
        "label": "DeepSeek (云端)",
        "default_url": "https://api.deepseek.com",
        "chat_path": "/v1/chat/completions",
        "default_model": "deepseek-v4-flash",
    },
    "openai": {
        "label": "OpenAI (云端)",
        "default_url": "https://api.openai.com",
        "chat_path": "/v1/chat/completions",
        "default_model": "gpt-4o-mini",
    },
    "custom": {
        "label": "自定义 (OpenAI兼容)",
        "default_url": "http://127.0.0.1:8000",
        "chat_path": "/v1/chat/completions",
        "default_model": "gpt-3.5-turbo",
    },
}


class LlmWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress_text = pyqtSignal(str)

    def __init__(self, url: str, payload: dict, headers: dict | None = None,
                 stream: bool = False, is_ollama: bool = False,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._url = url
        self._payload = payload
        self._headers = headers or {}
        self._stream = stream
        self._is_ollama = is_ollama

    def run(self) -> None:
        try:
            data = json.dumps(self._payload).encode("utf-8")
            headers = {"Content-Type": "application/json", **self._headers}
            req = urllib.request.Request(
                self._url, data=data, headers=headers, method="POST",
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                if self._stream and self._is_ollama:
                    self._read_ollama_stream(resp)
                else:
                    body = resp.read().decode("utf-8")
                    result = json.loads(body)
                    if not self._is_ollama:
                        result = self._normalize_openai_response(result)
                    self.finished.emit(result)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:500]
            self.error.emit(f"API请求失败 ({e.code}): {body}")
        except urllib.error.URLError as e:
            self.error.emit(f"无法连接: {e.reason}")
        except json.JSONDecodeError as e:
            self.error.emit(f"响应解析失败: {e}")
        except Exception as e:
            self.error.emit(f"请求失败: {e}")

    def _normalize_openai_response(self, resp: dict) -> dict:
        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        tool_calls_raw = msg.get("tool_calls")
        tool_calls = []
        if tool_calls_raw:
            for tc in tool_calls_raw:
                fn = tc.get("function", {})
                tool_calls.append({
                    "id": tc.get("id", fn.get("name", "")),
                    "type": "function",
                    "function": {
                        "name": fn.get("name", ""),
                        "arguments": fn.get("arguments", "{}"),
                    },
                })
        return {
            "message": {
                "role": msg.get("role", "assistant"),
                "content": msg.get("content") or "",
                "tool_calls": tool_calls if tool_calls else None,
            },
        }

    def _read_ollama_stream(self, resp) -> None:
        accumulated = ""
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue
            try:
                chunk = json.loads(line_str)
            except json.JSONDecodeError:
                continue
            if "message" in chunk and "content" in chunk["message"]:
                accumulated += chunk["message"]["content"]
                self.progress_text.emit(chunk["message"]["content"])
            if chunk.get("done"):
                result = chunk.copy()
                result["message"] = {"role": "assistant", "content": accumulated}
                self.finished.emit(result)
                return
        if accumulated:
            self.finished.emit({
                "message": {"role": "assistant", "content": accumulated},
            })


class LlmBackend(QObject):
    def __init__(self, provider: str = "ollama", api_key: str = "",
                 base_url: str = "", model: str = "",
                 parent: QObject | None = None):
        super().__init__(parent)
        self.provider = provider
        self.api_key = api_key
        self._worker: LlmWorker | None = None

        preset = PROVIDERS.get(provider, PROVIDERS["custom"])
        self.base_url = (base_url or preset["default_url"]).rstrip("/")
        self._chat_path = preset["chat_path"]
        self.model = model or preset["default_model"]
        self._is_ollama = (provider == "ollama")

    @property
    def chat_url(self) -> str:
        return f"{self.base_url}{self._chat_path}"

    def send_message(self, messages: list[dict], tools: list[dict] | None = None,
                     callback=None, stream: bool = False) -> None:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if self.provider == "deepseek":
            payload["temperature"] = 1.0

        if tools:
            payload["tools"] = [t for t in tools]
            if not self._is_ollama:
                payload["tool_choice"] = "auto"

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self._worker = LlmWorker(
            self.chat_url, payload, headers=headers,
            stream=stream, is_ollama=self._is_ollama,
        )
        if callback:
            self._worker.finished.connect(callback)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_error(self, msg: str) -> None:
        logger.error("LLM backend error: %s", msg)
