from typing import Dict

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pages.credits_page import CreditsPage
from pages.devices_page import DevicesPage
from pages.home_page import HomePage
from pages.macros_page import MacrosPage
from pages.settings_page import SettingsPage


class AppWindow(QMainWindow):
    def __init__(self, start_page: str = "home") -> None:
        super().__init__()
        self.setWindowTitle("RePCC Dashboard")
        self.resize(1100, 700)

        self._pages: Dict[str, int] = {}

        root = QWidget()
        root_layout = QHBoxLayout()

        nav_layout = QVBoxLayout()
        self.stack = QStackedWidget()

        button_home = QPushButton("Home")
        button_settings = QPushButton("Settings")
        button_macros = QPushButton("Macros")
        button_devices = QPushButton("Devices")
        button_credits = QPushButton("Credits")

        button_home.clicked.connect(lambda: self.navigate("home"))
        button_settings.clicked.connect(lambda: self.navigate("settings"))
        button_macros.clicked.connect(lambda: self.navigate("macros"))
        button_devices.clicked.connect(lambda: self.navigate("devices"))
        button_credits.clicked.connect(lambda: self.navigate("credits"))

        nav_layout.addWidget(button_home)
        nav_layout.addWidget(button_settings)
        nav_layout.addWidget(button_macros)
        nav_layout.addWidget(button_devices)
        nav_layout.addWidget(button_credits)
        nav_layout.addStretch()

        self.home_page = HomePage(self.navigate)
        self.settings_page = SettingsPage()
        self.macros_page = MacrosPage()
        self.devices_page = DevicesPage()
        self.credits_page = CreditsPage()

        self._register_page("home", self.home_page)
        self._register_page("settings", self.settings_page)
        self._register_page("macros", self.macros_page)
        self._register_page("devices", self.devices_page)
        self._register_page("credits", self.credits_page)

        root_layout.addLayout(nav_layout, 1)
        root_layout.addWidget(self.stack, 4)

        root.setLayout(root_layout)
        self.setCentralWidget(root)

        self.navigate(start_page)

    def _register_page(self, key: str, widget: QWidget) -> None:
        index = self.stack.addWidget(widget)
        self._pages[key] = index

    def navigate(self, key: str) -> None:
        if key not in self._pages:
            key = "home"

        # Keep dynamic pages in sync when opened.
        if key == "devices":
            self.devices_page.reload()
        elif key == "macros":
            self.macros_page.reload()

        self.stack.setCurrentIndex(self._pages[key])
