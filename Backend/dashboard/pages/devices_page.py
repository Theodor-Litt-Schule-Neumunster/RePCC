from PyQt5.QtWidgets import QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from data_access import load_register, parse_devices


class DevicesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()

        title = QLabel("Devices")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")

        connected_title = QLabel("Connected Right Now")
        self.connected_list = QListWidget()

        known_title = QLabel("Known / Old Devices")
        self.known_list = QListWidget()

        reload_button = QPushButton("Reload Devices")
        reload_button.clicked.connect(self.reload)

        layout.addWidget(title)
        layout.addWidget(connected_title)
        layout.addWidget(self.connected_list)
        layout.addWidget(known_title)
        layout.addWidget(self.known_list)
        layout.addWidget(reload_button)

        self.setLayout(layout)
        self.reload()

    def reload(self) -> None:
        data = load_register()
        connected_now, known_or_old = parse_devices(data)

        self.connected_list.clear()
        self.known_list.clear()

        if connected_now:
            self.connected_list.addItems(connected_now)
        else:
            self.connected_list.addItem("No active device IPs found")

        if known_or_old:
            self.known_list.addItems(known_or_old)
        else:
            self.known_list.addItem("No known devices found")
