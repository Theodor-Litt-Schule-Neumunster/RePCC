import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from constants import ROAMING_MACROS_DIR
from pages.macro_builder_dialog import MacroBuilderDialog


class MacrosPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()

        title = QLabel("Macros")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        info = QLabel("Loads .pcmac files from APPDATA/Roaming/.RePCC/macros")

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._update_buttons)

        actions = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.refresh_button = QPushButton("Refresh")
        self.run_button = QPushButton("Run")
        self.delete_button = QPushButton("Delete")
        self.edit_button = QPushButton("Edit")

        self.new_button.clicked.connect(self.new_macro)
        self.refresh_button.clicked.connect(self.reload)
        self.run_button.clicked.connect(self.run_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.edit_button.clicked.connect(self.edit_selected)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.edit_selected())

        actions.addWidget(self.new_button)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.run_button)
        actions.addWidget(self.delete_button)
        actions.addWidget(self.edit_button)
        actions.addStretch()

        self.status_label = QLabel("Ready")

        layout.addWidget(title)
        layout.addWidget(info)
        layout.addWidget(self.list_widget)
        layout.addLayout(actions)
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.reload()

    def _selected_macro_filename(self) -> str | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        text = item.text().strip()
        if not text:
            return None
        return text

    def _update_buttons(self) -> None:
        has_selection = self._selected_macro_filename() is not None
        self.run_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.edit_button.setEnabled(has_selection)

    def reload(self) -> None:
        os.makedirs(ROAMING_MACROS_DIR, exist_ok=True)

        selected = self._selected_macro_filename()

        files = [
            name
            for name in os.listdir(ROAMING_MACROS_DIR)
            if name.lower().endswith(".pcmac") and os.path.isfile(os.path.join(ROAMING_MACROS_DIR, name))
        ]
        files.sort(key=str.lower)

        self.list_widget.clear()
        self.list_widget.addItems(files)

        if selected and selected in files:
            for idx in range(self.list_widget.count()):
                item = self.list_widget.item(idx)
                if item.text() == selected:
                    self.list_widget.setCurrentItem(item)
                    break

        if files:
            self.status_label.setText(f"Loaded {len(files)} macro file(s)")
        else:
            self.status_label.setText("No macros found. Folder can stay empty.")

        self._update_buttons()

    def new_macro(self) -> None:
        name, ok = QInputDialog.getText(self, "New Macro", "Macro name:")
        if not ok:
            return

        clean = name.strip()
        if not clean:
            self.status_label.setText("Macro name can not be empty")
            return

        if clean.lower().endswith(".pcmac"):
            filename = clean
        else:
            filename = f"{clean}.pcmac"

        path = os.path.join(ROAMING_MACROS_DIR, filename)
        dialog = MacroBuilderDialog(path)
        if dialog.exec_() == QDialog.Accepted:
            self.status_label.setText(f"Saved {filename}")
            self.reload()
            for idx in range(self.list_widget.count()):
                item = self.list_widget.item(idx)
                if item.text() == filename:
                    self.list_widget.setCurrentItem(item)
                    break

    def run_selected(self) -> None:
        filename = self._selected_macro_filename()
        if not filename:
            self.status_label.setText("No macro selected")
            return

        macro_name = filename[:-6] if filename.lower().endswith(".pcmac") else filename
        encoded = quote(macro_name)
        url = f"http://127.0.0.1:15248/macro/run/{encoded}"

        try:
            with urlopen(url, timeout=3.0) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")

            message = ""
            try:
                payload = json.loads(body)
                message = payload.get("message") or payload.get("error") or body
            except Exception:
                message = body

            self.status_label.setText(f"Run request returned {status}: {message}")
        except HTTPError as err:
            body = err.read().decode("utf-8", errors="replace")
            self.status_label.setText(f"Run request failed ({err.code}): {body}")
        except URLError as err:
            self.status_label.setText(f"Run request failed: {err.reason}")

    def delete_selected(self) -> None:
        filename = self._selected_macro_filename()
        if not filename:
            self.status_label.setText("No macro selected")
            return

        result = QMessageBox.question(
            self,
            "Delete Macro",
            f"Delete '{filename}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            self.status_label.setText("Delete canceled")
            return

        path = os.path.join(ROAMING_MACROS_DIR, filename)
        if not os.path.exists(path):
            self.status_label.setText("Macro file no longer exists")
            self.reload()
            return

        try:
            os.remove(path)
            self.status_label.setText(f"Deleted {filename}")
            self.reload()
        except OSError as err:
            self.status_label.setText(f"Delete failed: {err}")

    def edit_selected(self) -> None:
        filename = self._selected_macro_filename()
        if not filename:
            self.status_label.setText("No macro selected")
            return

        path = os.path.join(ROAMING_MACROS_DIR, filename)
        dialog = MacroBuilderDialog(path)
        if dialog.exec_() == QDialog.Accepted:
            self.status_label.setText(f"Saved {filename}")
            self.reload()
            for idx in range(self.list_widget.count()):
                item = self.list_widget.item(idx)
                if item.text() == filename:
                    self.list_widget.setCurrentItem(item)
                    break
