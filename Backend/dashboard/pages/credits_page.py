from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget


class CreditsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout()

        title = QLabel("Credits")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")

        body = QLabel("Temporary credits text.\n\nRePCC team and contributors.")

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addStretch()

        self.setLayout(layout)
