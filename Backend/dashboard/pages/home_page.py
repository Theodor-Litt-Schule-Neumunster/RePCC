from typing import Callable

from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class HomePage(QWidget):
    def __init__(self, on_navigate: Callable[[str], None]) -> None:
        super().__init__()

        layout = QVBoxLayout()
        layout.setSpacing(10)

        title = QLabel("RePCC Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")

        subtitle = QLabel("Bare-bones dashboard skeleton")

        button_settings = QPushButton("Open Settings")
        button_macros = QPushButton("Open Macros")
        button_devices = QPushButton("Open Devices")
        button_credits = QPushButton("Open Credits")

        button_settings.clicked.connect(lambda: on_navigate("settings"))
        button_macros.clicked.connect(lambda: on_navigate("macros"))
        button_devices.clicked.connect(lambda: on_navigate("devices"))
        button_credits.clicked.connect(lambda: on_navigate("credits"))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(button_settings)
        layout.addWidget(button_macros)
        layout.addWidget(button_devices)
        layout.addWidget(button_credits)
        layout.addStretch()

        self.setLayout(layout)
