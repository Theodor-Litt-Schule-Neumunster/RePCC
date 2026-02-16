import os
import sys
import time
import socket
import qrcode
import signal
import pystray
import threading

from io import BytesIO
from PIL import Image
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

def assetsPath(relativepath:str):
    """
    For easy file access in py script or binary
    
    :param relativepath: Relative filepath for asset. e. g. /assets/repcclogo.ico
    """
    basepath = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(basepath, relativepath)

class ClientWindow(QWidget):

    toggle_signal = pyqtSignal()

    def __init__(self, data:str) -> None:
        super().__init__()
        self.toggle_signal.connect(self.toggle_visibility)

        self.connected = False
        self.setWindowTitle("RePCC Presenter Client")

        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", black_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG") # type: ignore
        buffer.seek(0)

        pixmap = QPixmap()
        pixmap.loadFromData(buffer.read())

        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter) # type: ignore

        self.status_label = QLabel()
        if self.connected:
            self.status_label.setText("connected")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("disconnected")
            self.status_label.setStyleSheet("color: red;")
        self.status_label.setAlignment(Qt.AlignCenter) # type: ignore

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def setConnection(self, value:bool):
        self.connected = value
        if self.connected:
            self.status_label.setText("connected")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("disconnected")
            self.status_label.setStyleSheet("color: red;")

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

def _trayMain(window: ClientWindow, app: QApplication):
    try:
        def toggleWindow(icon, item):
            window.toggle_signal.emit()

        def quit_app(icon, item):
            app.quit()

        tray_menu = pystray.Menu(
            pystray.MenuItem("Toggle Window", toggleWindow),
            pystray.MenuItem("Quit", quit_app),
        )

        image = Image.open(assetsPath("assets/repccBin.ico"))
        icon = pystray.Icon("repccclient", image, "RePCC Client", tray_menu)
        icon.run()
    except Exception as e:
        print(e)

def _mdnsMain():
    class mdnsListener(ServiceListener):
        def __init__(self) -> None:
            super().__init__()

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            self._handle_Service(zc, type_, name)

        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            self._handle_Service(zc, type_, name)

        def _handle_Service(self, zc: Zeroconf, type_:str, name:str):

            info = zc.get_service_info(type_, name)

            if info and "repccpresentationserver" in name.lower():
                
                print("Presentaion Server found.")

    zeroconf = Zeroconf()
    listener = mdnsListener()
    browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

if __name__ == "__main__":

    def getlocalip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("1.1.1.1", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    def signal_handler(sig, frame):
        app.quit()

    signal.signal(signal.SIGINT, signal_handler)

    app.setWindowIcon(QIcon(assetsPath("assets/repccBin.ico")))

    data = {
        "ip":getlocalip(),
        "name":socket.gethostname()
    }

    window = ClientWindow(str(data))

    threading.Thread(target=_trayMain, args=(window, app), daemon=True).start()
    threading.Thread(target=_mdnsMain, daemon=True).start()
    sys.exit(app.exec_())