from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# ============================================================
# Windows GUI 自动化测试平台 - GUI 用例编辑器（第一版）
#
# 目标：
# 1. 给测试人员直接编辑/保存 JSON 用例
# 2. 管理模板图片
# 3. 一键执行用例（调用你已有的 app.main / run_case）
# 4. 查看运行日志、截图和结果
#
# 配套目录（建议）：
# windows_gui_test_platform/
#   app/
#   cases/
#   templates/
#   runs/
#   platform_gui.py   <-- 当前文件
#
# 运行：
#   pip install pyside6
#   python platform_gui.py
#
# 注意：
# 1. 这是一版“真正可用的 GUI 用例编辑器底座”，不是最终商业版。
# 2. 执行按钮会尝试导入 app.main 中的 run_case(case_path) 来跑你的用例。
# 3. 如果你后续要加录制器、AI 规划器、模板测试器，可以继续在此基础上扩展。
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
CASES_DIR = BASE_DIR / "cases"
TEMPLATES_DIR = BASE_DIR / "templates"
RUNS_DIR = BASE_DIR / "runs"

CASES_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)


ACTION_FIELDS: Dict[str, List[str]] = {
    "click_image": ["template", "timeout", "clicks"],
    "double_click_image": ["template", "timeout"],
    "right_click_image": ["template", "timeout"],
    "move_to_image": ["template", "timeout"],
    "move_relative_from_image": ["template", "timeout", "dx", "dy"],
    "click_relative_from_image": ["template", "timeout", "dx", "dy"],
    "drag_relative_from_image": ["template", "timeout", "dx", "dy", "duration"],
    "drag_image_to_image": ["source_template", "target_template", "timeout", "duration"],
    "mouse_down": [],
    "mouse_up": [],
    "scroll": ["amount"],
    "press_key": ["key"],
    "hotkey": ["keys"],
    "type_text": ["text"],
    "sleep": ["seconds"],
    "wait_image": ["template", "timeout"],
    "assert_image": ["template", "timeout"],
    "assert_not_image": ["template", "timeout"],
    "scroll_until_find": ["move_anchor_template", "target_template", "max_scrolls", "scroll_amount"],
    "screenshot": ["name"],
}

DEFAULT_STEP: Dict[str, Any] = {
    "action": "click_image",
    "template": "",
    "timeout": 10,
    "clicks": 1,
    "dx": 0,
    "dy": 0,
    "duration": 0.5,
    "amount": 500,
    "key": "",
    "keys": ["ctrl", "s"],
    "text": "",
    "seconds": 1,
    "source_template": "",
    "target_template": "",
    "move_anchor_template": "",
    "max_scrolls": 12,
    "scroll_amount": 500,
    "name": "shot",
    "note": "",
}


def safe_json_dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


class RunWorker(QThread):
    log = Signal(str)
    finished_ok = Signal(str)
    finished_fail = Signal(str)

    def __init__(self, case_path: str):
        super().__init__()
        self.case_path = case_path

    def run(self):
        try:
            self.log.emit(f"开始执行用例: {self.case_path}")
            # 延迟导入，避免 GUI 启动时因自动化依赖问题直接崩
            from app.main import run_case

            run_case(self.case_path)
            self.finished_ok.emit(f"执行完成: {self.case_path}")
        except Exception as e:
            self.finished_fail.emit(f"执行失败: {e}")


class CaseEditorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_case_path: Path | None = None
        self.current_data: Dict[str, Any] = {"name": "new_case", "steps": []}
        self._build_ui()
        self.refresh_case_list()
        self.refresh_templates_combo()
        self.load_case_to_editor(self.current_data)

    def _build_ui(self):
        root = QHBoxLayout(self)

        # 左侧：用例列表
        left = QVBoxLayout()
        left.addWidget(QLabel("用例列表"))
        self.case_list = QListWidget()
        self.case_list.itemClicked.connect(self.on_case_selected)
        left.addWidget(self.case_list)

        left_btns = QHBoxLayout()
        self.btn_new_case = QPushButton("新建用例")
        self.btn_open_case = QPushButton("打开文件")
        self.btn_refresh_case = QPushButton("刷新")
        left_btns.addWidget(self.btn_new_case)
        left_btns.addWidget(self.btn_open_case)
        left_btns.addWidget(self.btn_refresh_case)
        left.addLayout(left_btns)

        self.btn_new_case.clicked.connect(self.new_case)
        self.btn_open_case.clicked.connect(self.open_case_file)
        self.btn_refresh_case.clicked.connect(self.refresh_case_list)

        left_widget = QWidget()
        left_widget.setLayout(left)

        # 中间：步骤表格
        center = QVBoxLayout()
        header = QHBoxLayout()
        self.case_name_edit = QLineEdit()
        self.case_name_edit.setPlaceholderText("用例名称")
        header.addWidget(QLabel("用例名称"))
        header.addWidget(self.case_name_edit)

        self.btn_save_case = QPushButton("保存用例")
        self.btn_run_case = QPushButton("执行用例")
        self.btn_add_step = QPushButton("添加步骤")
        self.btn_del_step = QPushButton("删除步骤")

        header.addWidget(self.btn_save_case)
        header.addWidget(self.btn_run_case)
        header.addWidget(self.btn_add_step)
        header.addWidget(self.btn_del_step)
        center.addLayout(header)

        self.steps_table = QTableWidget(0, 4)
        self.steps_table.setHorizontalHeaderLabels(["序号", "动作", "摘要", "备注"])
        self.steps_table.itemSelectionChanged.connect(self.on_step_selected)
        center.addWidget(self.steps_table)

        center_widget = QWidget()
        center_widget.setLayout(center)

        # 右侧：步骤属性编辑器
        right = QVBoxLayout()

        right.addWidget(QLabel("步骤属性"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(ACTION_FIELDS.keys())
        self.action_combo.currentTextChanged.connect(self.on_action_changed)
        right.addWidget(self.action_combo)

        form_box = QGroupBox("参数")
        self.form_layout = QFormLayout(form_box)

        self.template_combo = QComboBox()
        self.source_template_combo = QComboBox()
        self.target_template_combo = QComboBox()
        self.anchor_template_combo = QComboBox()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 999)
        self.timeout_spin.setValue(10)
        self.clicks_spin = QSpinBox()
        self.clicks_spin.setRange(1, 10)
        self.clicks_spin.setValue(1)
        self.dx_spin = QSpinBox()
        self.dx_spin.setRange(-5000, 5000)
        self.dy_spin = QSpinBox()
        self.dy_spin.setRange(-5000, 5000)
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 10.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(0.5)
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(-5000, 5000)
        self.amount_spin.setValue(500)
        self.key_edit = QLineEdit()
        self.keys_edit = QLineEdit("ctrl,s")
        self.text_edit = QLineEdit()
        self.seconds_spin = QDoubleSpinBox()
        self.seconds_spin.setRange(0.1, 999.0)
        self.seconds_spin.setValue(1.0)
        self.max_scrolls_spin = QSpinBox()
        self.max_scrolls_spin.setRange(1, 999)
        self.max_scrolls_spin.setValue(12)
        self.scroll_amount_spin = QSpinBox()
        self.scroll_amount_spin.setRange(-5000, 5000)
        self.scroll_amount_spin.setValue(500)
        self.note_edit = QLineEdit()
        self.screenshot_name_edit = QLineEdit("shot")

        self.widgets_map = {
            "template": self.template_combo,
            "source_template": self.source_template_combo,
            "target_template": self.target_template_combo,
            "move_anchor_template": self.anchor_template_combo,
            "timeout": self.timeout_spin,
            "clicks": self.clicks_spin,
            "dx": self.dx_spin,
            "dy": self.dy_spin,
            "duration": self.duration_spin,
            "amount": self.amount_spin,
            "key": self.key_edit,
            "keys": self.keys_edit,
            "text": self.text_edit,
            "seconds": self.seconds_spin,
            "max_scrolls": self.max_scrolls_spin,
            "scroll_amount": self.scroll_amount_spin,
            "note": self.note_edit,
            "name": self.screenshot_name_edit,
        }

        self.labels_map = {
            "template": "模板",
            "source_template": "源模板",
            "target_template": "目标模板",
            "move_anchor_template": "滚动锚点模板",
            "timeout": "超时(秒)",
            "clicks": "点击次数",
            "dx": "水平偏移",
            "dy": "垂直偏移",
            "duration": "持续时间",
            "amount": "滚轮值",
            "key": "按键",
            "keys": "快捷键(逗号分隔)",
            "text": "文本",
            "seconds": "等待秒数",
            "max_scrolls": "最大滚动次数",
            "scroll_amount": "每次滚动值",
            "note": "备注",
            "name": "截图名",
        }

        self.current_step_index: int | None = None
        self.form_rows: Dict[str, QWidget] = {}
        for field_name, widget in self.widgets_map.items():
            label = QLabel(self.labels_map[field_name])
            self.form_layout.addRow(label, widget)
            self.form_rows[field_name] = widget

        right.addWidget(form_box)

        btn_apply = QPushButton("应用到当前步骤")
        btn_apply.clicked.connect(self.apply_form_to_step)
        right.addWidget(btn_apply)

        self.step_preview = QPlainTextEdit()
        self.step_preview.setReadOnly(True)
        right.addWidget(QLabel("当前步骤 JSON"))
        right.addWidget(self.step_preview)

        right_widget = QWidget()
        right_widget.setLayout(right)

        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(center_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 1)
        root.addWidget(splitter)

        self.btn_save_case.clicked.connect(self.save_case)
        self.btn_run_case.clicked.connect(self.run_case)
        self.btn_add_step.clicked.connect(self.add_step)
        self.btn_del_step.clicked.connect(self.delete_step)

        self.on_action_changed(self.action_combo.currentText())

    def refresh_templates_combo(self):
        templates = sorted([p.name for p in TEMPLATES_DIR.glob("*.png")])
        for combo in [
            self.template_combo,
            self.source_template_combo,
            self.target_template_combo,
            self.anchor_template_combo,
        ]:
            current = combo.currentText()
            combo.clear()
            combo.addItems(templates)
            if current and current in templates:
                combo.setCurrentText(current)

    def refresh_case_list(self):
        self.case_list.clear()
        for case_file in sorted(CASES_DIR.glob("*.json")):
            item = QListWidgetItem(case_file.name)
            item.setData(Qt.UserRole, str(case_file))
            self.case_list.addItem(item)

    def new_case(self):
        self.current_case_path = None
        self.current_data = {"name": "new_case", "steps": []}
        self.load_case_to_editor(self.current_data)

    def open_case_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择用例文件", str(CASES_DIR), "JSON Files (*.json)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.current_case_path = Path(path)
        self.current_data = data
        self.load_case_to_editor(data)

    def on_case_selected(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.current_case_path = Path(path)
        self.current_data = data
        self.load_case_to_editor(data)

    def load_case_to_editor(self, data: Dict[str, Any]):
        self.case_name_edit.setText(data.get("name", ""))
        self.steps_table.setRowCount(0)
        for idx, step in enumerate(data.get("steps", []), start=1):
            self._append_step_row(idx, step)
        self.step_preview.setPlainText("")
        self.current_step_index = None

    def _append_step_row(self, idx: int, step: Dict[str, Any]):
        row = self.steps_table.rowCount()
        self.steps_table.insertRow(row)
        self.steps_table.setItem(row, 0, QTableWidgetItem(str(idx)))
        self.steps_table.setItem(row, 1, QTableWidgetItem(step.get("action", "")))
        summary = self._build_summary(step)
        self.steps_table.setItem(row, 2, QTableWidgetItem(summary))
        self.steps_table.setItem(row, 3, QTableWidgetItem(step.get("note", "")))

    def _build_summary(self, step: Dict[str, Any]) -> str:
        action = step.get("action", "")
        keys = ACTION_FIELDS.get(action, [])
        parts = []
        for k in keys[:3]:
            if k in step and step[k] not in (None, "", [], {}):
                parts.append(f"{k}={step[k]}")
        return ", ".join(parts)

    def add_step(self):
        step = dict(DEFAULT_STEP)
        step["action"] = self.action_combo.currentText()
        self.current_data.setdefault("steps", []).append(step)
        self._append_step_row(len(self.current_data["steps"]), step)

    def delete_step(self):
        row = self.steps_table.currentRow()
        if row < 0:
            return
        self.steps_table.removeRow(row)
        self.current_data["steps"].pop(row)
        self._reload_steps_table()
        self.current_step_index = None
        self.step_preview.setPlainText("")

    def _reload_steps_table(self):
        self.steps_table.setRowCount(0)
        for idx, step in enumerate(self.current_data.get("steps", []), start=1):
            self._append_step_row(idx, step)

    def on_step_selected(self):
        row = self.steps_table.currentRow()
        if row < 0 or row >= len(self.current_data.get("steps", [])):
            return
        self.current_step_index = row
        step = self.current_data["steps"][row]
        self.fill_form(step)
        self.step_preview.setPlainText(safe_json_dump(step))

    def fill_form(self, step: Dict[str, Any]):
        action = step.get("action", "click_image")
        self.action_combo.setCurrentText(action)
        self.refresh_templates_combo()

        self.template_combo.setCurrentText(step.get("template", ""))
        self.source_template_combo.setCurrentText(step.get("source_template", ""))
        self.target_template_combo.setCurrentText(step.get("target_template", ""))
        self.anchor_template_combo.setCurrentText(step.get("move_anchor_template", ""))
        self.timeout_spin.setValue(int(step.get("timeout", 10)))
        self.clicks_spin.setValue(int(step.get("clicks", 1)))
        self.dx_spin.setValue(int(step.get("dx", 0)))
        self.dy_spin.setValue(int(step.get("dy", 0)))
        self.duration_spin.setValue(float(step.get("duration", 0.5)))
        self.amount_spin.setValue(int(step.get("amount", 500)))
        self.key_edit.setText(step.get("key", ""))
        self.keys_edit.setText(",".join(step.get("keys", ["ctrl", "s"])) if isinstance(step.get("keys"), list) else str(step.get("keys", "")))
        self.text_edit.setText(step.get("text", ""))
        self.seconds_spin.setValue(float(step.get("seconds", 1)))
        self.max_scrolls_spin.setValue(int(step.get("max_scrolls", 12)))
        self.scroll_amount_spin.setValue(int(step.get("scroll_amount", 500)))
        self.note_edit.setText(step.get("note", ""))
        self.screenshot_name_edit.setText(step.get("name", "shot"))
        self.on_action_changed(action)

    def on_action_changed(self, action: str):
        visible_fields = set(ACTION_FIELDS.get(action, [])) | {"note"}
        if action == "screenshot":
            visible_fields.add("name")
        for field_name, widget in self.form_rows.items():
            label_item = self.form_layout.labelForField(widget)
            is_visible = field_name in visible_fields
            widget.setVisible(is_visible)
            if label_item:
                label_item.setVisible(is_visible)

    def _collect_form_step(self) -> Dict[str, Any]:
        action = self.action_combo.currentText()
        step: Dict[str, Any] = {"action": action}
        for field_name in ACTION_FIELDS.get(action, []):
            widget = self.widgets_map[field_name]
            if isinstance(widget, QComboBox):
                step[field_name] = widget.currentText()
            elif isinstance(widget, QSpinBox):
                step[field_name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                step[field_name] = widget.value()
            elif isinstance(widget, QLineEdit):
                value = widget.text().strip()
                if field_name == "keys":
                    step[field_name] = [k.strip() for k in value.split(",") if k.strip()]
                else:
                    step[field_name] = value
        note = self.note_edit.text().strip()
        if note:
            step["note"] = note
        if action == "screenshot":
            step["name"] = self.screenshot_name_edit.text().strip() or "shot"
        return step

    def apply_form_to_step(self):
        if self.current_step_index is None:
            QMessageBox.warning(self, "提示", "请先选择一个步骤")
            return
        step = self._collect_form_step()
        self.current_data["steps"][self.current_step_index] = step
        self._reload_steps_table()
        self.steps_table.selectRow(self.current_step_index)
        self.step_preview.setPlainText(safe_json_dump(step))

    def save_case(self):
        self.current_data["name"] = self.case_name_edit.text().strip() or "new_case"
        if self.current_case_path is None:
            path = CASES_DIR / f"{self.current_data['name']}.json"
            self.current_case_path = path
        else:
            path = self.current_case_path

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.current_data, f, ensure_ascii=False, indent=2)
        self.refresh_case_list()
        QMessageBox.information(self, "成功", f"已保存用例:\n{path}")

    def run_case(self):
        self.save_case()
        if self.current_case_path is None:
            QMessageBox.warning(self, "提示", "请先保存用例")
            return

        main_window = self.window()
        if not hasattr(main_window, "run_case_path"):
            QMessageBox.critical(self, "错误", "主窗口未找到 run_case_path 方法")
            return

        main_window.run_case_path(str(self.current_case_path))

class TemplateManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.refresh_template_list()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("模板列表"))
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self.on_template_selected)
        left.addWidget(self.template_list)

        btn_row = QHBoxLayout()
        self.btn_import = QPushButton("导入模板")
        self.btn_refresh = QPushButton("刷新")
        self.btn_delete = QPushButton("删除模板")
        btn_row.addWidget(self.btn_import)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_delete)
        left.addLayout(btn_row)

        self.btn_import.clicked.connect(self.import_template)
        self.btn_refresh.clicked.connect(self.refresh_template_list)
        self.btn_delete.clicked.connect(self.delete_template)

        right = QVBoxLayout()
        right.addWidget(QLabel("模板预览"))
        self.preview_label = QLabel("暂无预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(420, 280)
        self.preview_label.setStyleSheet("border:1px solid #999;")
        right.addWidget(self.preview_label)

        self.info_text = QPlainTextEdit()
        self.info_text.setReadOnly(True)
        right.addWidget(self.info_text)

        left_w = QWidget()
        left_w.setLayout(left)
        right_w = QWidget()
        right_w.setLayout(right)

        splitter = QSplitter()
        splitter.addWidget(left_w)
        splitter.addWidget(right_w)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def refresh_template_list(self):
        self.template_list.clear()
        for p in sorted(TEMPLATES_DIR.glob("*.png")):
            item = QListWidgetItem(p.name)
            item.setData(Qt.UserRole, str(p))
            self.template_list.addItem(item)

    def on_template_selected(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if not path:
            return
        pix = QPixmap(path)
        if pix.isNull():
            self.preview_label.setText("预览失败")
        else:
            self.preview_label.setPixmap(pix.scaled(420, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        file_path = Path(path)
        self.info_text.setPlainText(
            f"文件: {file_path.name}\n"
            f"路径: {file_path}\n"
            f"大小: {file_path.stat().st_size} bytes\n"
            f"修改时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_path.stat().st_mtime))}"
        )

    def import_template(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择模板图片", str(BASE_DIR), "PNG Files (*.png)")
        if not files:
            return
        for f in files:
            src = Path(f)
            dst = TEMPLATES_DIR / src.name
            if src.resolve() != dst.resolve():
                dst.write_bytes(src.read_bytes())
        self.refresh_template_list()
        QMessageBox.information(self, "成功", "模板导入完成")

    def delete_template(self):
        item = self.template_list.currentItem()
        if not item:
            return
        path = Path(item.data(Qt.UserRole))
        if QMessageBox.question(self, "确认", f"删除模板？\n{path.name}") != QMessageBox.Yes:
            return
        path.unlink(missing_ok=True)
        self.refresh_template_list()
        self.preview_label.setText("暂无预览")
        self.info_text.clear()


class RunPanelWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker: RunWorker | None = None
        self._build_ui()
        self.refresh_runs_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.case_path_edit = QLineEdit()
        self.case_path_edit.setPlaceholderText("选择要执行的用例 JSON")
        self.btn_browse_case = QPushButton("选择用例")
        self.btn_run = QPushButton("执行")
        self.btn_refresh_runs = QPushButton("刷新运行记录")
        top.addWidget(self.case_path_edit)
        top.addWidget(self.btn_browse_case)
        top.addWidget(self.btn_run)
        top.addWidget(self.btn_refresh_runs)
        layout.addLayout(top)

        splitter = QSplitter()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("运行日志"))
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        left_layout.addWidget(self.log_text)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("运行目录"))
        self.runs_list = QListWidget()
        self.runs_list.itemClicked.connect(self.on_run_selected)
        right_layout.addWidget(self.runs_list)

        self.run_info = QPlainTextEdit()
        self.run_info.setReadOnly(True)
        right_layout.addWidget(self.run_info)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self.btn_browse_case.clicked.connect(self.browse_case)
        self.btn_run.clicked.connect(self.execute_case)
        self.btn_refresh_runs.clicked.connect(self.refresh_runs_list)

    def browse_case(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择用例", str(CASES_DIR), "JSON Files (*.json)")
        if path:
            self.case_path_edit.setText(path)

    def append_log(self, text: str):
        self.log_text.appendPlainText(text)

    def execute_case(self):
        case_path = self.case_path_edit.text().strip()
        if not case_path:
            QMessageBox.warning(self, "提示", "请先选择用例")
            return
        self.log_text.clear()
        self.worker = RunWorker(case_path)
        self.worker.log.connect(self.append_log)
        self.worker.finished_ok.connect(self.on_run_ok)
        self.worker.finished_fail.connect(self.on_run_fail)
        self.worker.start()

    def on_run_ok(self, msg: str):
        self.append_log(msg)
        self.refresh_runs_list()
        QMessageBox.information(self, "成功", msg)

    def on_run_fail(self, msg: str):
        self.append_log(msg)
        self.refresh_runs_list()
        QMessageBox.critical(self, "失败", msg)

    def refresh_runs_list(self):
        self.runs_list.clear()
        for p in sorted(RUNS_DIR.glob("*"), reverse=True):
            if p.is_dir():
                item = QListWidgetItem(p.name)
                item.setData(Qt.UserRole, str(p))
                self.runs_list.addItem(item)

    def on_run_selected(self, item: QListWidgetItem):
        path = Path(item.data(Qt.UserRole))
        result_path = path / "result.json"
        log_path = path / "run.log"
        text = f"运行目录: {path}\n"
        if result_path.exists():
            text += result_path.read_text(encoding="utf-8")
        elif log_path.exists():
            text += log_path.read_text(encoding="utf-8")
        else:
            text += "暂无结果文件"
        self.run_info.setPlainText(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Windows GUI 自动化测试平台")
        self.resize(1600, 900)
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.case_editor = CaseEditorWidget()
        self.template_manager = TemplateManagerWidget()
        self.run_panel = RunPanelWidget()

        self.tabs.addTab(self.case_editor, "用例编辑器")
        self.tabs.addTab(self.template_manager, "模板管理")
        self.tabs.addTab(self.run_panel, "执行与报告")

        self.setCentralWidget(self.tabs)

        menu = self.menuBar()
        file_menu = menu.addMenu("文件")

        act_refresh = QAction("刷新模板和用例", self)
        act_refresh.triggered.connect(self.refresh_all)
        file_menu.addAction(act_refresh)

    def refresh_all(self):
        self.case_editor.refresh_case_list()
        self.case_editor.refresh_templates_combo()
        self.template_manager.refresh_template_list()
        self.run_panel.refresh_runs_list()

    def run_case_path(self, case_path: str):
        self.tabs.setCurrentWidget(self.run_panel)
        self.run_panel.case_path_edit.setText(case_path)
        self.run_panel.execute_case()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


# ============================================================
# 步骤录制器 (Mouse + Keyboard) → 自动生成 JSON 用例
# ============================================================
# 使用方式：
#   python platform_gui.py record
# 操作你要自动化的软件
#   F9  = 记录点击
#   F10 = 记录滚轮
#   F11 = 记录键盘输入
#   ESC = 停止并生成 JSON
# ============================================================

if len(sys.argv) > 1 and sys.argv[1] == "record":

    import pyautogui
    import keyboard

    steps: List[Dict[str, Any]] = []

    print("=== GUI 自动化录制器 ===")
    print("F9  记录鼠标点击")
    print("F10 记录滚轮")
    print("F11 记录键盘输入")
    print("ESC 结束录制")

    def record_click():
        x, y = pyautogui.position()
        step = {
            "action": "click_relative_from_image",
            "template": "",
            "dx": x,
            "dy": y,
            "timeout": 10
        }
        steps.append(step)
        print(f"记录点击: {x},{y}")

    def record_scroll():
        step = {
            "action": "scroll",
            "amount": 500
        }
        steps.append(step)
        print("记录滚轮")

    def record_text():
        text = input("输入文本: ")
        step = {
            "action": "type_text",
            "text": text
        }
        steps.append(step)
        print(f"记录输入: {text}")

    keyboard.add_hotkey("F9", record_click)
    keyboard.add_hotkey("F10", record_scroll)
    keyboard.add_hotkey("F11", record_text)

    keyboard.wait("esc")

    case = {
        "name": "record_case",
        "steps": steps
    }

    out = BASE_DIR / "cases" / "record_case.json"

    with open(out, "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False, indent=2)

    print(f"用例已生成: {out}")

