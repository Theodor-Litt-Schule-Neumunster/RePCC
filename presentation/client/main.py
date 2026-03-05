import os
import sys
import time
import socket
import qrcode
import signal
import shutil
import uvicorn
import pystray
import requests
import ipaddress
import threading
import pyautogui
import pygetwindow

from io import BytesIO
from PIL import Image
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

CLIENTWINDOW = None
MDNS_ENABLED = False
PING_SUCCESS = None
SERVER_IP = None

ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore

FAPI = FastAPI(info=True)
FAPI.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        MDNS_ENABLED = True
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

    zeroconf, listener, browser = None, None, None

    def createmDNS():

        nonlocal zeroconf, listener, browser

        zeroconf = Zeroconf()
        listener = mdnsListener()
        browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

    def mdnsHandler():
        global PING_SUCCESS, MDNS_ENABLED, SERVER_IP

        while True:

            time.sleep(2)

            if PING_SUCCESS == None:
                print("first time boot. starting...")
                
                threading.Thread(target=createmDNS).start() # pray
                PING_SUCCESS = True
                print("Started.")
                continue # no checks for first loop

            if PING_SUCCESS == True and SERVER_IP and MDNS_ENABLED == False:
                print("Sending ping")

                try:

                    req = requests.get(f"http://{SERVER_IP}:15247/ping", timeout=1)

                    if req.status_code == 200:
                        PING_SUCCESS = True
                        continue

                    PING_SUCCESS = False
                    continue
                except requests.ReadTimeout:
                    PING_SUCCESS = False
                    print("timeout error")
                    continue

                except requests.exceptions.ConnectTimeout:
                    PING_SUCCESS = False
                    print("timeout error 2")
                    continue

                except requests.exceptions.ConnectionError:
                    PING_SUCCESS = False
                    print("timeout error 3")
                    continue

            if PING_SUCCESS == False and SERVER_IP and MDNS_ENABLED == False:
                print("Resetting...")

                PING_SUCCESS = None
                SERVER_IP = None
                continue

    class mdnsListener(ServiceListener):

        def __init__(self) -> None:
            super().__init__()

            global MDNS_ENABLED

            MDNS_ENABLED = True
            self._connecting = False

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            self._handle_Service(zc, type_, name)

        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            self._handle_Service(zc, type_, name)

        def _handle_Service(self, zc: Zeroconf, type_:str, name:str):

            global MDNS_ENABLED, SERVER_IP

            try:
                info = zc.get_service_info(type_, name)
            finally:
                pass

            if info and "repccpresentationserver" in name.lower():

                if self._connecting:
                    return

                print("Presentaion Server found.")

                candidate_ips = []

                # Prefer parsed_addresses when available, then fall back to raw bytes.
                try:
                    candidate_ips = info.parsed_addresses()
                except Exception:
                    candidate_ips = []

                if not candidate_ips:
                    candidate_ips = [
                        str(ipaddress.ip_address(raw_ip))
                        for raw_ip in info.addresses
                    ]

                # Prefer server-provided primary address when available.
                preferred_ip = None
                api_port = 15247

                properties = info.properties or {}
                if b"preferred_ip" in properties:
                    try:
                        preferred_ip = properties[b"preferred_ip"].decode("utf-8")
                    except Exception:
                        preferred_ip = None

                if b"api_port" in properties:
                    try:
                        api_port = int(properties[b"api_port"].decode("utf-8"))
                    except Exception:
                        api_port = 15247

                if preferred_ip and preferred_ip in candidate_ips:
                    candidate_ips.remove(preferred_ip)
                    candidate_ips.insert(0, preferred_ip)

                print(f"Candidate server IPs: {candidate_ips} (api_port={api_port})")

                def _connect_worker():
                    global MDNS_ENABLED, SERVER_IP

                    try:
                        while True:
                            time.sleep(2)

                            for ip in candidate_ips:
                                try:
                                    r = requests.post(
                                        f"http://{ip}:{api_port}/connect/{socket.gethostname()}",
                                        timeout=(1, 2),
                                    )
                                except requests.RequestException:
                                    continue

                                if r.status_code == 200:
                                    SERVER_IP = ip

                                    if not CLIENTWINDOW == None:
                                        CLIENTWINDOW.setConnection(True)

                                    # Kill zeroconf and reset vars
                                    zeroconf.close() # type: ignore
                                    MDNS_ENABLED = False
                                    print(f"Connected to server on {ip}:{api_port}")
                                    return

                            print("Connection failed for all advertised IPs, retrying...")
                    finally:
                        self._connecting = False

                self._connecting = True
                threading.Thread(target=_connect_worker, daemon=True).start()

    mdnsHandler()

def _httpMain():

    @FAPI.post("/presentaion")
    async def FAPI_PostPresentation(file: UploadFile):
        PATH = ROAMING + "\\.RePCC\\presentation"
        if os.path.exists(PATH):
            shutil.rmtree(PATH)

        os.makedirs(PATH)

        try:
            contents = await file.read()
            filename = file.filename

            with open(f"{PATH}\\{filename}", "wb") as f:
                f.write(contents)
                f.close()

            os.startfile(f"{PATH}\\{filename}")
            time.sleep(2)
            try:
                windows = pygetwindow.getWindowsWithTitle(filename)
                if windows:
                    print(".")
                    windows[0].activate()
            except Exception:
                pass

            return JSONResponse({}, status_code=200)

        except Exception as e:
            print(e)
            return JSONResponse({}, status_code=500)

    @FAPI.get("/next")
    async def FAPI_next():
        try:
            pyautogui.press("right")
            return JSONResponse({}, status_code=200)
        except pyautogui.FailSafeException as e:
            print(f"failsafe on /next: {e}")
            return JSONResponse({"error": "pyautogui fail-safe triggered"}, status_code=409)
        except Exception as e:
            print(f"/next error: {e}")
            return JSONResponse({"error": "failed to send next input"}, status_code=500)

    @FAPI.get("/prev")
    async def FAPI_prev():
        try:
            pyautogui.press("left")
            return JSONResponse({}, status_code=200)
        except pyautogui.FailSafeException as e:
            print(f"failsafe on /prev: {e}")
            return JSONResponse({"error": "pyautogui fail-safe triggered"}, status_code=409)
        except Exception as e:
            print(f"/prev error: {e}")
            return JSONResponse({"error": "failed to send prev input"}, status_code=500)

# TODO:
# - check if connection stays, if not: reopen ZC (Done? idrk atp)

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
    
    _httpMain()
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

    CLIENTWINDOW  = ClientWindow(str(data))

    def _start_api():
        try:
            uvicorn.run(
                FAPI,
                host="0.0.0.0",
                port=11111,
                access_log=False,
                log_config=None,
            )
        except Exception as e:
            print(f"[API] Uvicorn failed: {e}")

    threading.Thread(target=_trayMain, args=(CLIENTWINDOW, app), daemon=True).start()
    threading.Thread(target=_mdnsMain, daemon=True).start()
    threading.Thread(target=_start_api, daemon=True).start()
    sys.exit(app.exec_())