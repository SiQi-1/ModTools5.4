"""AI Agent chat panel — embeddable QWidget for natural-language mod editing."""

from __future__ import annotations

import json
import logging
import re
import os
import subprocess
from typing import Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QTextEdit,
    QPushButton, QLabel, QLineEdit, QPlainTextEdit, QSplitter, QFrame, QDialog,
    QFormLayout, QComboBox, QDialogButtonBox, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QSizePolicy,
)

from ...app.settings_store import load_agent_settings, save_agent_settings
from ...app.user_paths import settings_file_path
from ...agent.agent_session import AgentSession
from ...agent.llm_backend import LlmBackend, PROVIDERS
from ...agent.tool_executor import ToolExecutor
from ...agent.system_prompt import build_system_prompt

logger = logging.getLogger(__name__)

PANEL_MIN_WIDTH = 320
PANEL_DEFAULT_WIDTH = 420

_SMALL_BTN_STYLE = (
    "QPushButton { padding: 2px 4px; font-size: 12px; border-radius: 4px; }"
    "QPushButton:hover { background-color: #e8e8e8; }"
)


def _mark_small_btn(btn: QPushButton) -> None:
    btn.setStyleSheet(_SMALL_BTN_STYLE)
    btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


class _ProposalCard(QFrame):
    apply_clicked = pyqtSignal(dict)
    reject_clicked = pyqtSignal()

    def __init__(self, proposal: dict, description: str, parent=None):
        super().__init__(parent)
        self._proposal = proposal
        self._description = description
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        # Header
        header = QLabel(f"📋 变更提案：{self._description}")
        header_font = QFont()
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        action = self._proposal.get("action", "")
        preview = self._proposal.get("preview", {})

        if action == "add_modifier":
            self._build_modifier_preview(layout, preview)
        elif action in ("add_entity", "edit_entity"):
            self._build_entity_preview(layout, preview, action)
        elif action == "delete_entity":
            lbl = QLabel(f"删除：{preview.get('deleted_entry', '')}")
            lbl.setStyleSheet("color: #c0392b; font-weight: bold;")
            layout.addWidget(lbl)
        else:
            layout.addWidget(QLabel(json.dumps(preview, ensure_ascii=False, indent=2)))

        # Warnings
        warnings = self._proposal.get("warnings", [])
        for w in warnings:
            warn_label = QLabel(f"⚠ {w}")
            warn_label.setStyleSheet("color: #e67e22;")
            layout.addWidget(warn_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        reject_btn = QPushButton("拒绝")
        reject_btn.clicked.connect(self.reject_clicked.emit)
        apply_btn = QPushButton("应用")
        apply_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; }")
        apply_btn.clicked.connect(lambda: self.apply_clicked.emit(self._proposal))
        btn_layout.addWidget(reject_btn)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def _build_modifier_preview(self, layout, preview):
        owner = preview.get("owner", {})
        modifier = preview.get("modifier", {})
        reqsets = preview.get("requirement_sets", [])
        requirements = preview.get("requirements", [])

        tree = QTreeWidget()
        tree.setHeaderLabels(["层级", "详情"])
        owner_item = QTreeWidgetItem(tree, [
            f"拥有者: {owner.get('display_name', owner.get('type_name', ''))}",
            f"表: {owner.get('table_name', '')}",
        ])
        mod_item = QTreeWidgetItem(owner_item, [
            f"修改器: {modifier.get('modifier_id', '')}",
            f"EffectType: {modifier.get('effect_type', '')}",
        ])
        params = modifier.get("parameters", [])
        if params:
            for p in params:
                QTreeWidgetItem(mod_item, [p.get("name", ""), str(p.get("value", ""))])
        for rs in reqsets:
            rs_item = QTreeWidgetItem(mod_item, [
                f"条件集: {rs.get('requirement_set_id', '')}",
                f"逻辑: {rs.get('logic', 'ALL')}",
            ])
            for rid in rs.get("bound_requirements", []):
                req = next((r for r in requirements if r.get("requirement_id") == rid), None)
                if req:
                    QTreeWidgetItem(rs_item, [
                        f"条件: {rid}",
                        req.get("requirement_type", ""),
                    ])
        tree.expandAll()
        layout.addWidget(tree)

    def _build_entity_preview(self, layout, preview, action):
        before = preview.get("before", {})
        after = preview.get("after", {})

        table_data_before = before.get("table_data", {}) if isinstance(before, dict) else {}
        table_data_after = after.get("table_data", {}) if isinstance(after, dict) else {}

        all_keys = set(table_data_before.keys()) | set(table_data_after.keys())
        # Also include top-level keys
        all_top = set(before.keys()) if isinstance(before, dict) else set()
        all_top |= set(after.keys()) if isinstance(after, dict) else set()
        all_top -= {"table_data", "images", "subtables"}

        tree = QTreeWidget()
        tree.setHeaderLabels(["字段", "当前值", "新值"])
        if action == "add_entity":
            tree.setHeaderLabels(["字段", "值"])

        for key in sorted(all_top):
            old_val = str(before.get(key, "")) if isinstance(before, dict) else ""
            new_val = str(after.get(key, "")) if isinstance(after, dict) else ""
            if action == "add_entity":
                QTreeWidgetItem(tree, [key, new_val])
            elif old_val != new_val:
                item = QTreeWidgetItem(tree, [key, old_val, new_val])
                item.setForeground(1, Qt.GlobalColor.red)
                item.setForeground(2, Qt.GlobalColor.darkGreen)

        for key in sorted(all_keys):
            old_val = str(table_data_before.get(key, ""))
            new_val = str(table_data_after.get(key, ""))
            if action == "add_entity":
                QTreeWidgetItem(tree, [f"table_data.{key}", new_val])
            elif old_val != new_val:
                item = QTreeWidgetItem(tree, [f"table_data.{key}", old_val, new_val])
                item.setForeground(1, Qt.GlobalColor.red)
                item.setForeground(2, Qt.GlobalColor.darkGreen)

        tree.expandAll()
        layout.addWidget(tree)


class AgentChatPanel(QWidget):
    collapseToggled = pyqtSignal(bool)  # True=collapsed, False=expanded

    def __init__(self, sections_provider: Callable[[], dict[str, object]],
                 on_apply_proposal: Callable[[dict], None],
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._sections_provider = sections_provider
        self._on_apply_proposal = on_apply_proposal
        self._proposal_card: _ProposalCard | None = None
        self._proposals = []

        # Backend initialization — load persisted settings
        agent_cfg = load_agent_settings()
        self._llm_backend = LlmBackend(
            provider=agent_cfg.provider,
            api_key=agent_cfg.api_key,
            base_url=agent_cfg.base_url,
            model=agent_cfg.model,
        )
        self._tool_executor = ToolExecutor(sections_provider)
        self._system_prompt = build_system_prompt()

        self._agent = AgentSession(
            self._llm_backend,
            self._tool_executor,
            self._system_prompt,
            parent=self,
        )
        self._agent.response_started.connect(self._on_response_started)
        self._agent.response_chunk.connect(self._on_response_chunk)
        self._agent.response_finished.connect(self._on_response_finished)
        self._agent.preview_ready.connect(self._on_preview_ready)
        self._agent.thinking.connect(self._on_thinking)
        self._agent.error_occurred.connect(self._on_error)

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(4, 4, 4, 4)
        self._header_title = QLabel("AI 助手")
        title_font = QFont()
        title_font.setBold(True)
        self._header_title.setFont(title_font)
        header_bar.addWidget(self._header_title)
        header_bar.addStretch()

        provider_label = PROVIDERS.get(self._llm_backend.provider, {}).get("label", self._llm_backend.provider)
        self._status_label = QLabel(f"⚪ {provider_label}")
        self._status_label.setStyleSheet("color: #888;")
        header_bar.addWidget(self._status_label)
        header_bar.addSpacing(4)

        self._header_settings = QPushButton("⚙")
        self._header_settings.setFixedSize(24, 24)
        self._header_settings.clicked.connect(self._show_settings)
        _mark_small_btn(self._header_settings)
        header_bar.addWidget(self._header_settings)

        self._header_clear = QPushButton("清空")
        self._header_clear.setFixedSize(40, 24)
        self._header_clear.clicked.connect(self._clear_chat)
        _mark_small_btn(self._header_clear)
        header_bar.addWidget(self._header_clear)

        self._collapse_btn = QPushButton("▶")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.clicked.connect(self._toggle_collapse)
        self._collapse_btn.setToolTip("折叠AI助手")
        _mark_small_btn(self._collapse_btn)
        header_bar.addWidget(self._collapse_btn)

        self._header_bar_layout = header_bar
        main_layout.addLayout(header_bar)

        # Wrapper for collapsible content
        self._content_wrapper = QWidget()
        content_layout = QVBoxLayout(self._content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(sep)

        # Splitter: chat history + preview area
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        content_layout.addWidget(self._splitter, 1)

        # Chat area
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        chat_layout.addWidget(self._chat_display)

        self._splitter.addWidget(chat_widget)

        # Proposal placeholder (initially hidden by splitter)
        self._proposal_container = QWidget()
        self._proposal_container.setVisible(False)
        self._proposal_layout = QVBoxLayout(self._proposal_container)
        self._proposal_layout.setContentsMargins(0, 0, 0, 0)
        self._splitter.addWidget(self._proposal_container)
        self._proposal_container.setMaximumHeight(0)

        # Input area — multi-line with auto-grow
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(10, 6, 10, 6)
        input_layout.setSpacing(4)

        self._input_field = QPlainTextEdit()
        self._input_field.setPlaceholderText("输入需求，如'创建一个+5战斗力的单位能力'...\nEnter 发送，Ctrl+Enter 换行")
        self._input_field.setMaximumHeight(120)
        self._input_field.setMinimumHeight(36)
        self._input_field.setTabChangesFocus(True)
        # Ctrl+Enter to send
        self._input_field.installEventFilter(self)
        input_layout.addWidget(self._input_field)

        btn_row = QHBoxLayout()
        hint = QLabel("Enter 发送 · Ctrl+Enter 换行")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        btn_row.addWidget(hint)
        btn_row.addStretch()

        self._web_search_btn = QPushButton("Web")
        self._web_search_btn.setCheckable(True)
        self._web_search_btn.setChecked(False)
        self._web_search_btn.setFixedSize(40, 24)
        self._web_search_btn.setToolTip("联网搜索：关闭")
        self._web_search_btn.toggled.connect(self._toggle_web_search)
        _mark_small_btn(self._web_search_btn)
        self._web_search_btn.setStyleSheet(
            _SMALL_BTN_STYLE + "QPushButton { color: #aaa; } "
            "QPushButton:checked { color: #2980b9; font-weight: bold; }"
        )
        btn_row.addWidget(self._web_search_btn)
        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self._handle_cancel)
        self._cancel_btn.setFixedSize(50, 28)
        self._cancel_btn.setVisible(False)
        _mark_small_btn(self._cancel_btn)
        self._cancel_btn.setStyleSheet(
            _SMALL_BTN_STYLE + "QPushButton { color: #c0392b; font-weight: bold; }"
        )
        btn_row.addWidget(self._cancel_btn)

        self._send_btn = QPushButton("发送")
        self._send_btn.clicked.connect(self._handle_send)
        self._send_btn.setFixedSize(60, 28)
        _mark_small_btn(self._send_btn)
        btn_row.addWidget(self._send_btn)
        input_layout.addLayout(btn_row)

        content_layout.addLayout(input_layout)
        main_layout.addWidget(self._content_wrapper, 1)

        self.setMinimumWidth(PANEL_MIN_WIDTH)
        self._collapsed = False
        self._web_search_enabled = False

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._elapsed_seconds = 0

    def _toggle_web_search(self, checked: bool) -> None:
        self._web_search_enabled = checked
        self._web_search_btn.setToolTip(f"联网搜索：{'开启' if checked else '关闭'}")
        self._agent.set_web_search_enabled(checked)

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        self._content_wrapper.setVisible(not self._collapsed)
        if self._collapsed:
            self.setMaximumWidth(28)
            self.setMinimumWidth(0)
            self._header_title.setVisible(False)
            self._status_label.setVisible(False)
            self._header_settings.setVisible(False)
            self._header_clear.setVisible(False)
            self._collapse_btn.setText("◀")
            self._collapse_btn.setToolTip("展开AI助手")
        else:
            self.setMaximumWidth(16777215)
            self.setMinimumWidth(PANEL_MIN_WIDTH)
            self._header_title.setVisible(True)
            self._status_label.setVisible(True)
            self._header_settings.setVisible(True)
            self._header_clear.setVisible(True)
            self._collapse_btn.setText("▶")
            self._collapse_btn.setToolTip("折叠AI助手")
        self.collapseToggled.emit(self._collapsed)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self._input_field and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    # Ctrl+Enter: insert newline
                    self._input_field.insertPlainText("\n")
                else:
                    # Enter: send
                    self._handle_send()
                return True
        return super().eventFilter(obj, event)

    def _tick_elapsed(self):
        self._elapsed_seconds += 1
        self._status_label.setText(f"⏳ 等待响应... {self._elapsed_seconds}s")

    def _is_cancelled(self) -> bool:
        return getattr(self, "_cancelled", False)

    def _handle_cancel(self):
        self._cancelled = True
        self._agent.reset()
        worker = self._llm_backend._worker
        if worker is not None and worker.isRunning():
            try:
                worker.terminate()
                worker.wait(1000)
            except Exception:
                pass
        self._input_field.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._elapsed_timer.stop()
        self._status_label.setText("⏹ 已取消")
        self._status_label.setStyleSheet("color: #888;")
        self._append_message("thinking", "请求已取消。")

    def _handle_send(self):
        text = self._input_field.toPlainText().strip()
        if not text:
            return
        self._cancelled = False
        self._input_field.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)
        self._elapsed_seconds = 0
        self._elapsed_timer.start()
        self._status_label.setText("⏳ 连接中... 0s")
        self._status_label.setStyleSheet("color: #f39c12;")

        self._input_field.clear()
        self._remove_proposal_card()
        self._append_message("user", text)
        self._agent.send_user_message(text)

    def _on_response_started(self):
        self._append_message("assistant", "")  # Placeholder for streaming

    def _on_response_chunk(self, text: str):
        # For streaming support (future)
        pass

    def _on_response_finished(self, text: str):
        if self._is_cancelled():
            return
        self._elapsed_timer.stop()
        self._input_field.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._status_label.setText(f"✅ 就绪 ({self._elapsed_seconds}s)")
        self._status_label.setStyleSheet("color: #27ae60;")
        # Replace the placeholder with actual text
        cursor = self._chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        if not text:
            text = "（工具调用完成，等待预览...）"
        cursor.insertText(text + "\n\n")

    def _on_preview_ready(self, proposal: dict, description: str):
        if self._is_cancelled():
            return
        self._remove_proposal_card()
        card = _ProposalCard(proposal, description)
        card.apply_clicked.connect(self._handle_apply)
        card.reject_clicked.connect(self._remove_proposal_card)
        self._proposal_card = card
        self._proposal_layout.addWidget(card)
        self._proposal_container.setVisible(True)
        self._proposal_container.setMaximumHeight(400)
        self._append_message("assistant",
                             f"[提案] {description}\n请查看下方预览卡片并确认操作。")

    def _on_thinking(self, msg: str):
        self._append_message("thinking", msg)

    def _on_error(self, msg: str):
        if self._is_cancelled():
            return
        self._elapsed_timer.stop()
        self._input_field.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._status_label.setText(f"❌ 错误 ({self._elapsed_seconds}s)")
        self._status_label.setStyleSheet("color: #c0392b;")
        self._append_message("assistant", f"❌ 错误：{msg}")

    def _handle_apply(self, proposal: dict):
        try:
            self._on_apply_proposal(proposal)
            self._append_message("assistant", "✅ 变更已应用。")
            self._remove_proposal_card()
            # Continue the agent loop for multi-step requests
            self._agent.accept_proposal()
        except Exception as e:
            self._append_message("assistant", f"❌ 应用变更失败：{e}")

    def _remove_proposal_card(self):
        if self._proposal_card:
            self._proposal_card.setParent(None)
            self._proposal_card.deleteLater()
            self._proposal_card = None
        self._proposal_container.setVisible(False)
        self._proposal_container.setMaximumHeight(0)

    def _append_message(self, role: str, content: str):
        display = self._chat_display
        cursor = display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if role == "user":
            display.append(f"<b style='color:#2c3e50;'>👤 你</b><br>{self._escape_html(content)}")
        elif role == "assistant":
            if not content:
                return
            html_body = self._md_to_html(content)
            display.append(f"<b style='color:#2980b9;'>🤖 助手</b><br>{html_body}")
        elif role == "thinking":
            display.append(
                f"<span style='color:#888; font-style:italic;'>🔧 {self._escape_html(content)}</span>")
        display.ensureCursorVisible()

    @staticmethod
    def _escape_html(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _md_to_html(text: str) -> str:
        """Convert basic Markdown to HTML for QTextEdit rendering."""
        # Escape HTML first, then selectively un-escape our own tags
        html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Code blocks (```...```)
        html = re.sub(r'```(\w*)\n?(.*?)```', r'<pre style="background:#f0f0f0; padding:8px; border-radius:4px;"><code>\2</code></pre>', html, flags=re.DOTALL)
        # Inline code (`...`)
        html = re.sub(r'`([^`]+)`', r'<code style="background:#f0f0f0; padding:1px 4px; border-radius:2px;">\1</code>', html)

        # Bold (**...**)
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)

        # Headings (###, ##, #)
        html = re.sub(r'^### (.+)$', r'<h4 style="margin:8px 0 4px;">\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h3 style="margin:10px 0 4px;">\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h2 style="margin:12px 0 4px;">\1</h2>', html, flags=re.MULTILINE)

        # Horizontal rules (---)
        html = re.sub(r'^---$', r'<hr style="border:none; border-top:1px solid #ddd;">', html, flags=re.MULTILINE)

        # Tables (simple pipe-based)
        lines = html.split("\n")
        in_table = False
        table_buffer = []
        out_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped[1:-1].split("|")]
                # Skip separator row (|----|----|)
                if all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c):
                    continue
                if not in_table:
                    in_table = True
                table_buffer.append(cells)
            else:
                if in_table:
                    # Flush table
                    out_lines.append('<table style="border-collapse:collapse; margin:6px 0;">')
                    for i, row in enumerate(table_buffer):
                        tag = "th" if i == 0 else "td"
                        style = "border:1px solid #ddd; padding:4px 10px;"
                        if i == 0:
                            style += " background:#f5f5f5; font-weight:bold;"
                        row_html = "<tr>" + "".join(
                            f'<{tag} style="{style}">{c}</{tag}>' for c in row
                        ) + "</tr>"
                        out_lines.append(row_html)
                    out_lines.append("</table>")
                    table_buffer = []
                    in_table = False
                out_lines.append(line)
        if in_table and table_buffer:
            out_lines.append('<table style="border-collapse:collapse; margin:6px 0;">')
            for i, row in enumerate(table_buffer):
                tag = "th" if i == 0 else "td"
                style = "border:1px solid #ddd; padding:4px 10px;"
                if i == 0:
                    style += " background:#f5f5f5; font-weight:bold;"
                row_html = "<tr>" + "".join(
                    f'<{tag} style="{style}">{c}</{tag}>' for c in row
                ) + "</tr>"
                out_lines.append(row_html)
            out_lines.append("</table>")
        html = "\n".join(out_lines)

        # Newlines to <br>
        html = html.replace("\n", "<br>")

        return html

    def _clear_chat(self):
        self._chat_display.clear()
        self._agent.reset()
        self._remove_proposal_card()

    def _show_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("AI 助手设置")
        dlg.setMinimumWidth(400)
        layout = QFormLayout(dlg)

        # Provider selection
        provider_names = list(PROVIDERS.keys())
        provider_labels = [PROVIDERS[k]["label"] for k in provider_names]
        provider_combo = QComboBox()
        provider_combo.addItems(provider_labels)
        try:
            idx = provider_names.index(self._llm_backend.provider)
        except ValueError:
            idx = 0
        provider_combo.setCurrentIndex(idx)
        layout.addRow("服务商:", provider_combo)

        # URL
        url_edit = QLineEdit(self._llm_backend.base_url)
        layout.addRow("API URL:", url_edit)

        # API Key
        key_edit = QLineEdit(self._llm_backend.api_key)
        key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_edit.setPlaceholderText("Ollama本地模式无需填写")
        layout.addRow("API Key:", key_edit)

        # Model
        model_combo = QComboBox()
        model_combo.setEditable(True)
        model_combo.addItems([
            "deepseek-v4-flash", "deepseek-v4-pro",
            "deepseek-chat", "deepseek-reasoner",
            "gpt-4o-mini", "gpt-4o",
            "qwen2.5:7b", "qwen2.5:14b",
        ])
        model_combo.setCurrentText(self._llm_backend.model)
        layout.addRow("模型:", model_combo)

        # Auto-switch URL when provider changes
        def _on_provider_changed(index):
            key = provider_names[index]
            preset = PROVIDERS[key]
            url_edit.setText(preset["default_url"])
            model_combo.setCurrentText(preset["default_model"])
            if key == "ollama":
                key_edit.setPlaceholderText("Ollama本地模式无需填写")
                key_edit.setText("")
            else:
                key_edit.setPlaceholderText("输入API Key")
        provider_combo.currentIndexChanged.connect(_on_provider_changed)

        # Config folder button
        config_path = settings_file_path()
        open_btn = QPushButton(f"打开配置文件夹: {config_path}")
        open_btn.clicked.connect(lambda: self._open_config_folder(config_path))
        layout.addRow("配置:", open_btn)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                    QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addRow(btn_box)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            provider_key = provider_names[provider_combo.currentIndex()]
            self._llm_backend = LlmBackend(
                provider=provider_key,
                api_key=key_edit.text().strip(),
                base_url=url_edit.text().strip(),
                model=model_combo.currentText().strip(),
            )
            self._agent = AgentSession(
                self._llm_backend,
                self._tool_executor,
                self._system_prompt,
                parent=self,
            )
            self._agent.response_started.connect(self._on_response_started)
            self._agent.response_chunk.connect(self._on_response_chunk)
            self._agent.response_finished.connect(self._on_response_finished)
            self._agent.preview_ready.connect(self._on_preview_ready)
            self._agent.thinking.connect(self._on_thinking)
            self._agent.error_occurred.connect(self._on_error)
            self._status_label.setText("✅ 就绪 (已更新)")
            self._status_label.setStyleSheet("color: #27ae60;")

            # Persist settings
            from ...app.settings_store import AgentSettings
            save_agent_settings(AgentSettings(
                provider=provider_key,
                api_key=key_edit.text().strip(),
                base_url=url_edit.text().strip(),
                model=model_combo.currentText().strip(),
            ))

    @staticmethod
    def _open_config_folder(path):
        folder = path.parent
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))
        except AttributeError:
            subprocess.Popen(["xdg-open", str(folder)])

    def update_sections_provider(self, provider):
        self._sections_provider = provider
        self._tool_executor._sections_provider = provider
