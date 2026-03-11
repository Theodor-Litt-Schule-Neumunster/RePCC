from copy import deepcopy
from typing import Any, Dict, List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from data_access import load_settings, save_settings

Path = Tuple[str, ...]


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.settings_data: Dict[str, Dict[str, Any]] = {}
        self.loaded_snapshot: Dict[str, Dict[str, Any]] = {}
        self.bindings: List[Dict[str, Any]] = []
        self.is_dirty = False

        root_layout = QVBoxLayout()

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        info = QLabel("Changes are staged locally until you click Save")

        buttons_row = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.reset_button = QPushButton("Reset Changes")
        self.reload_button = QPushButton("Reload From Disk")
        self.status_label = QLabel("Loaded")

        self.save_button.clicked.connect(self.save)
        self.reset_button.clicked.connect(self.reset_changes)
        self.reload_button.clicked.connect(self.reload)

        buttons_row.addWidget(self.save_button)
        buttons_row.addWidget(self.reset_button)
        buttons_row.addWidget(self.reload_button)
        buttons_row.addStretch()
        buttons_row.addWidget(self.status_label)

        self.tabs = QTabWidget()

        root_layout.addWidget(title)
        root_layout.addWidget(info)
        root_layout.addLayout(buttons_row)
        root_layout.addWidget(self.tabs)

        self.setLayout(root_layout)
        self.reload()

    def _mark_dirty(self) -> None:
        self.is_dirty = True
        self.status_label.setText("Unsaved changes")

    def _set_clean(self, message: str = "Loaded") -> None:
        self.is_dirty = False
        self.status_label.setText(message)

    def _set_value(self, path: Path, value: Any) -> None:
        node: Any = self.settings_data
        for segment in path[:-1]:
            if isinstance(node, dict):
                node = node[segment]
            elif isinstance(node, list):
                node = node[int(segment)]

        last = path[-1]
        if isinstance(node, dict):
            node[last] = value
        elif isinstance(node, list):
            node[int(last)] = value

        self._mark_dirty()

    def _get_value(self, path: Path) -> Any:
        node: Any = self.settings_data
        for segment in path:
            if isinstance(node, dict):
                node = node[segment]
            elif isinstance(node, list):
                node = node[int(segment)]
        return node

    def _bind_checkbox(self, parent: QFormLayout, label: str, path: Path) -> None:
        checkbox = QCheckBox()
        checkbox.toggled.connect(lambda checked, p=path: self._set_value(p, checked))
        parent.addRow(label, checkbox)
        self.bindings.append({"path": path, "widget": checkbox, "kind": "bool"})

    def _bind_int(self, parent: QFormLayout, label: str, path: Path, value: int) -> None:
        min_value, max_value = self._get_int_range(path, value)

        row = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_value, max_value)

        spin = QSpinBox()
        spin.setRange(min_value, max_value)

        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        spin.valueChanged.connect(lambda current, p=path: self._set_value(p, int(current)))

        row_layout.addWidget(slider)
        row_layout.addWidget(spin)
        row.setLayout(row_layout)

        parent.addRow(label, row)
        self.bindings.append(
            {
                "path": path,
                "widget": slider,
                "buddy": spin,
                "kind": "int",
            }
        )

    def _bind_float(self, parent: QFormLayout, label: str, path: Path, value: float) -> None:
        spin = QDoubleSpinBox()
        spin.setRange(-1000000.0, 1000000.0)
        spin.setDecimals(4)
        spin.setSingleStep(0.1)
        spin.valueChanged.connect(lambda current, p=path: self._set_value(p, float(current)))
        parent.addRow(label, spin)
        self.bindings.append({"path": path, "widget": spin, "kind": "float"})

    def _bind_str(self, parent: QFormLayout, label: str, path: Path, value: str) -> None:
        options = self._enum_options(path)
        if options:
            combo = QComboBox()
            combo.addItems(options)
            combo.currentTextChanged.connect(lambda current, p=path: self._set_value(p, current))
            parent.addRow(label, combo)
            self.bindings.append({"path": path, "widget": combo, "kind": "enum"})
            return

        line = QLineEdit()
        line.textChanged.connect(lambda current, p=path: self._set_value(p, current))
        parent.addRow(label, line)
        self.bindings.append({"path": path, "widget": line, "kind": "str"})

    def _bind_list(self, parent: QFormLayout, label: str, path: Path, value: List[Any]) -> None:
        box = QGroupBox(label)
        group_layout = QFormLayout()

        channel_labels = ["R", "G", "B", "A"]
        is_corecolor = path[-1].lower() == "corecolor"

        for idx, item in enumerate(value):
            if is_corecolor and idx < len(channel_labels):
                item_label = channel_labels[idx]
            else:
                item_label = f"{label}[{idx}]"
            item_path = path + (str(idx),)
            self._build_field(group_layout, item_label, item_path, item)

        box.setLayout(group_layout)
        parent.addRow(box)

    def _build_field(self, parent: QFormLayout, label: str, path: Path, value: Any) -> None:
        if isinstance(value, bool):
            self._bind_checkbox(parent, label, path)
            return

        if isinstance(value, int):
            self._bind_int(parent, label, path, value)
            return

        if isinstance(value, float):
            self._bind_float(parent, label, path, value)
            return

        if isinstance(value, str):
            self._bind_str(parent, label, path, value)
            return

        if isinstance(value, list):
            self._bind_list(parent, label, path, value)
            return

        if isinstance(value, dict):
            section = QGroupBox(label)
            section_layout = QFormLayout()
            for key, nested_value in value.items():
                nested_path = path + (key,)
                self._build_field(section_layout, key, nested_path, nested_value)
            section.setLayout(section_layout)
            parent.addRow(section)
            return

        line = QLineEdit()
        line.textChanged.connect(lambda current, p=path: self._set_value(p, current))
        parent.addRow(label, line)
        self.bindings.append({"path": path, "widget": line, "kind": "str"})

    def _build_tabs(self) -> None:
        self.tabs.clear()
        self.bindings = []

        for file_name, file_data in self.settings_data.items():
            tab = QWidget()
            tab_layout = QVBoxLayout()

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            form = QFormLayout()

            for key, value in file_data.items():
                self._build_field(form, key, (file_name, key), value)

            content.setLayout(form)
            scroll.setWidget(content)
            tab_layout.addWidget(scroll)
            tab.setLayout(tab_layout)

            self.tabs.addTab(tab, file_name)

    def _sync_widgets_from_data(self) -> None:
        for binding in self.bindings:
            value = self._get_value(binding["path"])
            kind = binding["kind"]
            widget = binding["widget"]

            if kind == "bool":
                widget.blockSignals(True)
                widget.setChecked(bool(value))
                widget.blockSignals(False)
                continue

            if kind == "int":
                buddy = binding["buddy"]
                widget.blockSignals(True)
                buddy.blockSignals(True)
                widget.setValue(int(value))
                buddy.setValue(int(value))
                buddy.blockSignals(False)
                widget.blockSignals(False)
                continue

            if kind == "float":
                widget.blockSignals(True)
                widget.setValue(float(value))
                widget.blockSignals(False)
                continue

            if kind == "enum":
                widget.blockSignals(True)
                text = str(value)
                if widget.findText(text) == -1:
                    widget.addItem(text)
                widget.setCurrentText(text)
                widget.blockSignals(False)
                continue

            if kind == "str":
                widget.blockSignals(True)
                widget.setText(str(value))
                widget.blockSignals(False)

    def _enum_options(self, path: Path) -> List[str]:
        key = path[-1].lower()
        if key == "style":
            return ["default", "simple", "trail"]
        if key in {"forward", "backward"}:
            return ["left", "right", "up", "down", "page_up", "page_down"]
        return []

    def _get_int_range(self, path: Path, value: int) -> Tuple[int, int]:
        key = path[-1].lower()

        ranges: Dict[str, Tuple[int, int]] = {
            "verbose": (0, 5),
            "maxsavedmacs": (1, 100),
            "maxsavedips": (1, 100),
            "fadetime": (0, 5000),
            "refreshrate": (1, 240),
            "traillength": (0, 200),
            "size": (1, 100),
            "framerate": (1, 120),
            "quality": (1, 5),
            "monitor": (1, 10),
        }

        if key in ranges:
            return ranges[key]

        if len(path) >= 2 and path[-2].lower() == "corecolor":
            return (0, 255)

        return (min(0, value), max(100, value * 4 if value > 0 else 100))

    def reload(self) -> None:
        self.settings_data = load_settings()
        self.loaded_snapshot = deepcopy(self.settings_data)
        self._build_tabs()
        self._sync_widgets_from_data()
        self._set_clean("Reloaded from disk")

    def reset_changes(self) -> None:
        self.settings_data = deepcopy(self.loaded_snapshot)
        self._sync_widgets_from_data()
        self._set_clean("Changes reset")

    def save(self) -> None:
        save_settings(self.settings_data)
        self.loaded_snapshot = deepcopy(self.settings_data)
        self._set_clean("Saved")
