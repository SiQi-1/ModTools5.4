"""Ollama-compatible LLM backend with background-thread HTTP calls.

Uses only stdlib (urllib + json) to avoid adding dependencies beyond PyQt6.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
import logging

from PyQt6.QtCore import QThread, QObject, pyqtSignal

logger = logging.getLogger(__name__)


class LlmWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress_text = pyqtSignal(str)

    def __init__(self, url: str, payload: dict, stream: bool = False,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._url = url
        self._payload = payload
        self._stream = stream

    def run(self) -> None:
        try:
            data = json.dumps(self._payload).encode("utf-8")
            req = urllib.request.Request(
                self._url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                if self._stream:
                    self._read_stream(resp)
                else:
                    body = resp.read().decode("utf-8")
                    result = json.loads(body)
                    self.finished.emit(result)
        except urllib.error.URLError as e:
            self.error.emit(f"无法连接到本地模型服务: {e.reason}")
        except json.JSONDecodeError as e:
            self.error.emit(f"模型响应解析失败: {e}")
        except Exception as e:
            self.error.emit(f"请求失败: {e}")

    def _read_stream(self, resp) -> None:
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
                delta = chunk["message"]["content"]
                accumulated += delta
                self.progress_text.emit(delta)
            if chunk.get("done", False):
                result = chunk.copy()
                result["message"] = {"role": "assistant", "content": accumulated}
                self.finished.emit(result)
                return
        # Stream ended without "done" marker
        if accumulated:
            self.finished.emit({
                "message": {"role": "assistant", "content": accumulated},
            })


class LlmBackend(QObject):
    def __init__(self, base_url: str = "http://127.0.0.1:11434",
                 model: str = "qwen2.5:7b", parent: QObject | None = None):
        super().__init__(parent)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._worker: LlmWorker | None = None

    @property
    def chat_url(self) -> str:
        return f"{self.base_url}/api/chat"

    def send_message(self, messages: list[dict], tools: list[dict] | None = None,
                     callback=None, stream: bool = False) -> None:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        self._worker = LlmWorker(self.chat_url, payload, stream=stream)
        if callback:
            self._worker.finished.connect(callback)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_error(self, msg: str) -> None:
        logger.error("LLM backend error: %s", msg)
