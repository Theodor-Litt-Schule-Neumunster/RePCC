import json
import os
import re
from typing import Any, Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


_MODIFIER_KEYS = {Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta}

_SPECIAL_KEY_MAP = {
    Qt.Key_Return: "enter",
    Qt.Key_Enter: "enter",
    Qt.Key_Escape: "esc",
    Qt.Key_Tab: "tab",
    Qt.Key_Backspace: "backspace",
    Qt.Key_Delete: "delete",
    Qt.Key_Insert: "insert",
    Qt.Key_Home: "home",
    Qt.Key_End: "end",
    Qt.Key_PageUp: "page_up",
    Qt.Key_PageDown: "page_down",
    Qt.Key_Space: "space",
    Qt.Key_Left: "left",
    Qt.Key_Right: "right",
    Qt.Key_Up: "up",
    Qt.Key_Down: "down",
}


class MacroKeysLineEdit(QLineEdit):
    """A QLineEdit that captures key presses as named tokens.

    Behaviour:
    - Each key event (possibly with modifiers held) **appends** a new token
      (or tokens) to the comma-separated list already in the field.
    - Backspace removes the **last** comma-separated token.
    - Delete clears the whole field.
    - Cursor-movement keys (Left / Right / Home / End) work normally so the
      user can position the cursor to manually edit the text if needed.
    """

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key = event.key()

        # ── Cursor navigation – pass through so QLineEdit handles them ──────
        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
            super().keyPressEvent(event)
            return

        # ── Backspace: remove the last comma-separated token ─────────────────
        if key == Qt.Key_Backspace:
            current = self.text()
            if "," in current:
                self.setText(current.rsplit(",", 1)[0])
            else:
                self.clear()
            event.accept()
            return

        # ── Delete: clear the whole field ────────────────────────────────────
        if key == Qt.Key_Delete:
            self.clear()
            event.accept()
            return

        # ── Modifier-only press: do nothing yet, wait for the real key ───────
        if key in _MODIFIER_KEYS:
            event.accept()
            return

        # ── Build the token(s) for this key event ────────────────────────────
        new_tokens: List[str] = []
        modifiers = event.modifiers()
        if modifiers & Qt.ControlModifier:
            new_tokens.append("ctrl")
        if modifiers & Qt.AltModifier:
            new_tokens.append("alt")
        if modifiers & Qt.ShiftModifier:
            new_tokens.append("shift")
        if modifiers & Qt.MetaModifier:
            new_tokens.append("win")

        key_token: str | None = _SPECIAL_KEY_MAP.get(key)

        if key_token is None and Qt.Key_F1 <= key <= Qt.Key_F35:
            key_token = f"f{key - Qt.Key_F1 + 1}"

        if key_token is None:
            # Use QKeySequence to get the base character name, avoiding
            # control characters that event.text() would return for Ctrl+letter.
            key_token = QKeySequence(key).toString().strip().lower() or None

        if key_token and key_token not in new_tokens:
            new_tokens.append(key_token)

        if new_tokens:
            current = self.text().strip()
            chunk = ",".join(new_tokens)
            self.setText(f"{current},{chunk}" if current else chunk)

        event.accept()


class MacroBuilderDialog(QDialog):
    def __init__(self, macro_path: str) -> None:
        super().__init__()
        self.macro_path = macro_path
        self.steps: List[Dict[str, Any]] = []
        self.loading_ui = False

        self.setWindowTitle(f"Macro Builder - {os.path.basename(macro_path)}")
        self.resize(980, 620)

        root = QVBoxLayout()

        data_box = QGroupBox("Macro Data")
        data_layout = QHBoxLayout()
        self.is_loop_checkbox = QCheckBox("Loop forever")
        self.amt_loops_spin = QSpinBox()
        self.amt_loops_spin.setRange(1, 10000)
        self.amt_loops_spin.setValue(1)
        data_layout.addWidget(self.is_loop_checkbox)
        data_layout.addWidget(QLabel("Amount loops"))
        data_layout.addWidget(self.amt_loops_spin)
        data_layout.addStretch()
        data_box.setLayout(data_layout)

        row = QHBoxLayout()

        palette_box = QGroupBox("Block Palette")
        palette_layout = QVBoxLayout()
        self.palette = QListWidget()
        self.palette.addItems([
            "Keyboard Single",
            "Keyboard Multi",
            "Mouse Click",
            "Mouse Move",
        ])
        add_button = QPushButton("Add Block")
        add_button.clicked.connect(self.add_selected_palette_block)
        self.palette.itemDoubleClicked.connect(lambda _: self.add_selected_palette_block())
        palette_layout.addWidget(self.palette)
        palette_layout.addWidget(add_button)
        palette_box.setLayout(palette_layout)

        sequence_box = QGroupBox("Macro Steps")
        sequence_layout = QVBoxLayout()
        self.step_list = QListWidget()
        self.step_list.setDragDropMode(QListWidget.InternalMove)
        self.step_list.setDefaultDropAction(Qt.MoveAction)
        self.step_list.model().rowsMoved.connect(self.sync_steps_from_list_order)
        self.step_list.currentRowChanged.connect(self.on_step_selected)

        seq_btn_row = QHBoxLayout()
        up_button = QPushButton("Up")
        down_button = QPushButton("Down")
        remove_button = QPushButton("Remove")
        up_button.clicked.connect(self.move_step_up)
        down_button.clicked.connect(self.move_step_down)
        remove_button.clicked.connect(self.remove_selected_step)
        seq_btn_row.addWidget(up_button)
        seq_btn_row.addWidget(down_button)
        seq_btn_row.addWidget(remove_button)

        sequence_layout.addWidget(self.step_list)
        sequence_layout.addLayout(seq_btn_row)
        sequence_box.setLayout(sequence_layout)

        editor_box = QGroupBox("Step Properties")
        editor_layout = QFormLayout()

        self.type_label = QLabel("-")
        self.sleep_spin = QSpinBox()
        self.sleep_spin.setRange(0, 600000)
        self.sleep_spin.valueChanged.connect(self.on_field_changed)

        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(["singlekey", "multikey", "click", "move"])
        self.action_type_combo.currentTextChanged.connect(self.on_field_changed)

        self.keys_line = MacroKeysLineEdit()
        self.keys_line.setPlaceholderText("Press keys or type: ctrl+alt+del / ctrl,alt,del")
        self.keys_line.textChanged.connect(self.on_field_changed)

        self.press_sleep_spin = QSpinBox()
        self.press_sleep_spin.setRange(0, 600000)
        self.press_sleep_spin.valueChanged.connect(self.on_field_changed)

        self.mouse_button_combo = QComboBox()
        self.mouse_button_combo.addItems(["left", "right"])
        self.mouse_button_combo.currentTextChanged.connect(self.on_field_changed)

        self.x_spin = QDoubleSpinBox()
        self.x_spin.setDecimals(3)
        self.x_spin.setRange(0.0, 1.0)
        self.x_spin.setSingleStep(0.01)
        self.x_spin.valueChanged.connect(self.on_field_changed)

        self.y_spin = QDoubleSpinBox()
        self.y_spin.setDecimals(3)
        self.y_spin.setRange(0.0, 1.0)
        self.y_spin.setSingleStep(0.01)
        self.y_spin.valueChanged.connect(self.on_field_changed)

        self.transition_combo = QComboBox()
        self.transition_combo.addItems(["quadratic", "linear"])
        self.transition_combo.currentTextChanged.connect(self.on_field_changed)

        self.transition_time_spin = QSpinBox()
        self.transition_time_spin.setRange(0, 600000)
        self.transition_time_spin.valueChanged.connect(self.on_field_changed)

        editor_layout.addRow("Type", self.type_label)
        editor_layout.addRow("Sleep (ms)", self.sleep_spin)
        editor_layout.addRow("Action type", self.action_type_combo)
        editor_layout.addRow("Keys", self.keys_line)
        editor_layout.addRow("Press sleep (ms)", self.press_sleep_spin)
        editor_layout.addRow("Mouse button", self.mouse_button_combo)
        editor_layout.addRow("Move X", self.x_spin)
        editor_layout.addRow("Move Y", self.y_spin)
        editor_layout.addRow("Transition", self.transition_combo)
        editor_layout.addRow("Transition time (ms)", self.transition_time_spin)

        editor_container = QWidget()
        editor_container.setLayout(editor_layout)
        editor_box_layout = QVBoxLayout()
        editor_box_layout.addWidget(editor_container)
        editor_box_layout.addStretch()
        editor_box.setLayout(editor_box_layout)

        row.addWidget(palette_box, 1)
        row.addWidget(sequence_box, 2)
        row.addWidget(editor_box, 2)

        footer = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        save_button.clicked.connect(self.save_macro)
        cancel_button.clicked.connect(self.reject)
        footer.addStretch()
        footer.addWidget(save_button)
        footer.addWidget(cancel_button)

        root.addWidget(data_box)
        root.addLayout(row)
        root.addLayout(footer)

        self.setLayout(root)

        self.load_macro()

    def load_macro(self) -> None:
        self.steps = []
        self.is_loop_checkbox.setChecked(False)
        self.amt_loops_spin.setValue(1)

        if os.path.exists(self.macro_path):
            with open(self.macro_path, "r", encoding="utf-8") as stream:
                data = json.load(stream)

            data_meta = data.get("$data", {}) if isinstance(data, dict) else {}
            self.is_loop_checkbox.setChecked(bool(data_meta.get("isLoop", False)))
            self.amt_loops_spin.setValue(int(data_meta.get("amtLoops", 1)))

            step_keys = [k for k in data.keys() if k != "$data"]
            step_keys.sort(key=lambda x: int(x) if str(x).isdigit() else 999999)
            for key in step_keys:
                step = data.get(key)
                if isinstance(step, dict):
                    self.steps.append(step)

        self.refresh_step_list()
        if self.step_list.count() > 0:
            self.step_list.setCurrentRow(0)
        else:
            self.on_step_selected(-1)

    def make_step_from_block(self, block_name: str) -> Dict[str, Any]:
        if block_name == "Keyboard Single":
            return {
                "type": "keyboard",
                "actiontype": "singlekey",
                "actiondata": [],
                "sleep": 100,
                "presssleep": 10,
            }
        if block_name == "Keyboard Multi":
            return {
                "type": "keyboard",
                "actiontype": "multikey",
                "actiondata": [],
                "sleep": 100,
                "presssleep": 10,
            }
        if block_name == "Mouse Click":
            return {
                "type": "mouse",
                "actiontype": "click",
                "actiondata": [0],
                "sleep": 100,
                "presssleep": 10,
            }
        return {
            "type": "mouse",
            "actiontype": "move",
            "actiondata": [0.5, 0.5],
            "sleep": 100,
            "transition": "quadratic",
            "transitiontime": 500,
        }

    def step_summary(self, step: Dict[str, Any], index: int) -> str:
        step_type = step.get("type", "?")
        action_type = step.get("actiontype", "?")
        data = step.get("actiondata", [])
        return f"{index + 1}. {step_type}/{action_type} {data}"

    def refresh_step_list(self) -> None:
        self.step_list.clear()
        for idx, step in enumerate(self.steps):
            item = QListWidgetItem(self.step_summary(step, idx))
            self.step_list.addItem(item)

    def sync_steps_from_list_order(self) -> None:
        reordered: List[Dict[str, Any]] = []
        for i in range(self.step_list.count()):
            text = self.step_list.item(i).text()
            prefix = text.split(".", 1)[0].strip()
            old_idx = int(prefix) - 1 if prefix.isdigit() else i
            if 0 <= old_idx < len(self.steps):
                reordered.append(self.steps[old_idx])
        if len(reordered) == len(self.steps):
            self.steps = reordered
            self.refresh_step_list()
            current = min(self.step_list.count() - 1, self.step_list.currentRow())
            if current >= 0:
                self.step_list.setCurrentRow(current)

    def add_selected_palette_block(self) -> None:
        item = self.palette.currentItem()
        if item is None:
            return
        step = self.make_step_from_block(item.text())
        self.steps.append(step)
        self.refresh_step_list()
        self.step_list.setCurrentRow(self.step_list.count() - 1)

    def remove_selected_step(self) -> None:
        idx = self.step_list.currentRow()
        if idx < 0:
            return
        self.steps.pop(idx)
        self.refresh_step_list()
        if self.step_list.count() > 0:
            self.step_list.setCurrentRow(max(0, idx - 1))
        else:
            self.on_step_selected(-1)

    def move_step_up(self) -> None:
        idx = self.step_list.currentRow()
        if idx <= 0:
            return
        self.steps[idx - 1], self.steps[idx] = self.steps[idx], self.steps[idx - 1]
        self.refresh_step_list()
        self.step_list.setCurrentRow(idx - 1)

    def move_step_down(self) -> None:
        idx = self.step_list.currentRow()
        if idx < 0 or idx >= len(self.steps) - 1:
            return
        self.steps[idx + 1], self.steps[idx] = self.steps[idx], self.steps[idx + 1]
        self.refresh_step_list()
        self.step_list.setCurrentRow(idx + 1)

    def on_step_selected(self, idx: int) -> None:
        has_selection = 0 <= idx < len(self.steps)
        self.loading_ui = True
        try:
            self.set_editor_enabled(has_selection)
            if not has_selection:
                self.type_label.setText("-")
                return

            step = self.steps[idx]
            step_type = str(step.get("type", ""))
            action_type = str(step.get("actiontype", ""))
            action_data = step.get("actiondata", [])

            self.type_label.setText(step_type)
            self.sleep_spin.setValue(int(step.get("sleep", 0)))

            if self.action_type_combo.findText(action_type) != -1:
                self.action_type_combo.setCurrentText(action_type)

            if step_type == "keyboard":
                if isinstance(action_data, list):
                    self.keys_line.setText(",".join(str(x) for x in action_data))
                self.press_sleep_spin.setValue(int(step.get("presssleep", 0)))

            if step_type == "mouse" and action_type == "click":
                button_value = 0
                if isinstance(action_data, list) and len(action_data) >= 1:
                    button_value = int(action_data[0])
                self.mouse_button_combo.setCurrentText("right" if button_value == 1 else "left")
                self.press_sleep_spin.setValue(int(step.get("presssleep", 0)))

            if step_type == "mouse" and action_type == "move":
                x_val = 0.5
                y_val = 0.5
                if isinstance(action_data, list) and len(action_data) >= 2:
                    x_val = float(action_data[0])
                    y_val = float(action_data[1])
                self.x_spin.setValue(x_val)
                self.y_spin.setValue(y_val)
                self.transition_combo.setCurrentText(str(step.get("transition", "quadratic")))
                self.transition_time_spin.setValue(int(step.get("transitiontime", 0)))
        finally:
            self.loading_ui = False
            self.update_editor_visibility()

    def set_editor_enabled(self, enabled: bool) -> None:
        self.sleep_spin.setEnabled(enabled)
        self.action_type_combo.setEnabled(enabled)
        self.keys_line.setEnabled(enabled)
        self.press_sleep_spin.setEnabled(enabled)
        self.mouse_button_combo.setEnabled(enabled)
        self.x_spin.setEnabled(enabled)
        self.y_spin.setEnabled(enabled)
        self.transition_combo.setEnabled(enabled)
        self.transition_time_spin.setEnabled(enabled)

    def update_editor_visibility(self) -> None:
        idx = self.step_list.currentRow()
        if idx < 0 or idx >= len(self.steps):
            return

        step = self.steps[idx]
        step_type = str(step.get("type", ""))
        action_type = str(step.get("actiontype", ""))

        is_keyboard = step_type == "keyboard"
        is_mouse_click = step_type == "mouse" and action_type == "click"
        is_mouse_move = step_type == "mouse" and action_type == "move"

        self.keys_line.setVisible(is_keyboard)
        self.press_sleep_spin.setVisible(is_keyboard or is_mouse_click)
        self.mouse_button_combo.setVisible(is_mouse_click)
        self.x_spin.setVisible(is_mouse_move)
        self.y_spin.setVisible(is_mouse_move)
        self.transition_combo.setVisible(is_mouse_move)
        self.transition_time_spin.setVisible(is_mouse_move)

    def on_field_changed(self) -> None:
        if self.loading_ui:
            return

        idx = self.step_list.currentRow()
        if idx < 0 or idx >= len(self.steps):
            return

        step = self.steps[idx]
        step_type = str(step.get("type", ""))
        action_type = str(step.get("actiontype", ""))

        step["sleep"] = int(self.sleep_spin.value())

        if step_type == "keyboard":
            chosen = self.action_type_combo.currentText()
            if chosen not in ["singlekey", "multikey"]:
                chosen = "singlekey"
            step["actiontype"] = chosen
            keys = self._parse_keys_text(self.keys_line.text())
            if chosen == "singlekey" and len(keys) > 1:
                keys = [keys[0]]
            step["actiondata"] = keys
            step["presssleep"] = int(self.press_sleep_spin.value())
            step.pop("transition", None)
            step.pop("transitiontime", None)

        if step_type == "mouse" and action_type == "click":
            step["actiontype"] = "click"
            step["actiondata"] = [1 if self.mouse_button_combo.currentText() == "right" else 0]
            step["presssleep"] = int(self.press_sleep_spin.value())
            step.pop("transition", None)
            step.pop("transitiontime", None)

        if step_type == "mouse" and action_type == "move":
            step["actiontype"] = "move"
            step["actiondata"] = [float(self.x_spin.value()), float(self.y_spin.value())]
            step["transition"] = self.transition_combo.currentText()
            step["transitiontime"] = int(self.transition_time_spin.value())
            step.pop("presssleep", None)

        self.refresh_step_list()
        self.step_list.setCurrentRow(idx)

    def _parse_keys_text(self, text: str) -> List[str]:
        raw = text.strip()
        if not raw:
            return []

        if "," in raw:
            parts = raw.split(",")
        elif "+" in raw:
            parts = raw.split("+")
        else:
            parts = re.split(r"\s+", raw)

        return [part.strip() for part in parts if part.strip()]

    def save_macro(self) -> None:
        data: Dict[str, Any] = {
            "$data": {
                "isLoop": bool(self.is_loop_checkbox.isChecked()),
                "amtLoops": int(self.amt_loops_spin.value()),
            }
        }

        for idx, step in enumerate(self.steps, start=1):
            data[str(idx)] = step

        os.makedirs(os.path.dirname(self.macro_path), exist_ok=True)
        with open(self.macro_path, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=4)

        QMessageBox.information(self, "Macro Builder", "Macro saved.")
        self.accept()
