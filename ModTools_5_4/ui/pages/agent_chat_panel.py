"""AI Agent chat panel — embeddable QWidget for natural-language mod editing."""

from __future__ import annotations

import json
import logging
from typing import Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QTextEdit,
    QPushButton, QLabel, QLineEdit, QSplitter, QFrame, QDialog,
    QFormLayout, QComboBox, QDialogButtonBox, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QSizePolicy,
)

from ...agent.agent_session import AgentSession
from ...agent.llm_backend import LlmBackend, PROVIDERS
from ...agent.tool_executor import ToolExecutor
from ...agent.system_prompt import build_system_prompt

logger = logging.getLogger(__name__)

PANEL_MIN_WIDTH = 320
PANEL_DEFAULT_WIDTH = 420


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
    def __init__(self, sections_provider: Callable[[], dict[str, object]],
                 on_apply_proposal: Callable[[dict], None],
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._sections_provider = sections_provider
        self._on_apply_proposal = on_apply_proposal
        self._proposal_card: _ProposalCard | None = None
        self._proposals = []

        # Backend initialization
        self._llm_backend = LlmBackend(model="qwen2.5:7b")
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
        header_bar.setContentsMargins(10, 6, 10, 6)
        title = QLabel("AI 助手")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        header_bar.addWidget(title)
        header_bar.addStretch()

        self._status_label = QLabel("⚪ 未连接")
        self._status_label.setStyleSheet("color: #888;")
        header_bar.addWidget(self._status_label)
        header_bar.addSpacing(8)

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(28, 28)
        settings_btn.clicked.connect(self._show_settings)
        header_bar.addWidget(settings_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(40, 28)
        clear_btn.clicked.connect(self._clear_chat)
        header_bar.addWidget(clear_btn)

        main_layout.addLayout(header_bar)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(sep)

        # Splitter: chat history + preview area
        self._splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(self._splitter, 1)

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

        # Input area
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(10, 6, 10, 6)

        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("输入需求，如'创建一个+5战斗力的单位能力'...")
        self._input_field.returnPressed.connect(self._handle_send)
        input_layout.addWidget(self._input_field)

        self._send_btn = QPushButton("发送")
        self._send_btn.clicked.connect(self._handle_send)
        self._send_btn.setFixedWidth(60)
        input_layout.addWidget(self._send_btn)

        main_layout.addLayout(input_layout)

        self.setMinimumWidth(PANEL_MIN_WIDTH)

    def _handle_send(self):
        text = self._input_field.text().strip()
        if not text:
            return
        self._input_field.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._status_label.setText("⏳ 思考中...")
        self._status_label.setStyleSheet("color: #f39c12;")

        self._remove_proposal_card()
        self._append_message("user", text)
        self._agent.send_user_message(text)

    def _on_response_started(self):
        self._append_message("assistant", "")  # Placeholder for streaming

    def _on_response_chunk(self, text: str):
        # For streaming support (future)
        pass

    def _on_response_finished(self, text: str):
        self._input_field.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._status_label.setText("✅ 就绪")
        self._status_label.setStyleSheet("color: #27ae60;")
        # Replace the placeholder with actual text
        cursor = self._chat_display.textCursor()
        cursor.moveOperation(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        if not text:
            text = "（工具调用完成，等待预览...）"
        cursor.insertText(text + "\n\n")

    def _on_preview_ready(self, proposal: dict, description: str):
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
        self._append_message("assistant", f"🔧 {msg}")

    def _on_error(self, msg: str):
        self._input_field.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._status_label.setText("❌ 错误")
        self._status_label.setStyleSheet("color: #c0392b;")
        self._append_message("assistant", f"❌ 错误：{msg}")

    def _handle_apply(self, proposal: dict):
        try:
            self._on_apply_proposal(proposal)
            self._append_message("assistant", "✅ 变更已应用。")
            self._remove_proposal_card()
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
            display.append(f"👤 **你**：{content}")
        elif role == "assistant":
            if not content:
                return
            display.append(f"🤖 **助手**：{content}")
        display.ensureCursorVisible()

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

    def update_sections_provider(self, provider):
        self._sections_provider = provider
        self._tool_executor._sections_provider = provider
