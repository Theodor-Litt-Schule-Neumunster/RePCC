# pyinstaller --noconfirm --onefile --noconsole --add-data "assets;assets" --icon="./assets/repccBin.ico" main.py
# pyinstaller --noconfirm --onefile --add-data "assets;assets" --icon="./assets/repccBin.ico" main.py

import os
import sys
import time
import socket
import subprocess
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
APP_INSTANCE = None

SLIDE_PROGRESS = 0
SLIDE_PROGRESS_LOCK = threading.Lock()

CREATE_NO_WINDOW = 0x08000000

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

def schedule_pc_shutdown(reason: str = "remote request"):
    def _shutdown_worker():
        print(f"PC shutdown requested ({reason}).")

        # Give the HTTP response a moment to return before initiating shutdown.
        time.sleep(0.25)

        if os.name != "nt":
            print("Non-Windows OS detected. Falling back to app exit.")
            try:
                if APP_INSTANCE is not None:
                    APP_INSTANCE.quit()
            finally:
                os._exit(0)

        try:
            subprocess.Popen(
                ["shutdown", "/s", "/f", "/t", "5"],
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception as e:
            print(f"Windows shutdown command failed: {e}")
            return

        try:
            if CLIENTWINDOW is not None:
                CLIENTWINDOW.close()
        except Exception:
            pass

        try:
            if APP_INSTANCE is not None:
                APP_INSTANCE.quit()
        except Exception:
            pass

    threading.Thread(target=_shutdown_worker, daemon=True).start()

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

            def resyncProgress(newProgress:int):
                global SLIDE_PROGRESS, SERVER_IP

                with SLIDE_PROGRESS_LOCK:
                    old_progress = SLIDE_PROGRESS

                if newProgress < 0:
                    newProgress = 0

                difference = newProgress - old_progress
                if difference == 0:
                    print("ReSync not needed, progress already matches.")
                    return

                direction = "right" if difference > 0 else "left"
                steps = abs(difference)

                print(
                    f"ReSync from {old_progress} to {newProgress} ({steps} steps {direction})."
                )

                try:
                    if SERVER_IP:
                        requests.get(
                            f"http://{SERVER_IP}:{api_port}/notify/resync/start",
                            timeout=(1, 2),
                        )
                except requests.RequestException:
                    pass

                try:
                    for _ in range(steps):
                        try:
                            pyautogui.press(direction)
                        except pyautogui.FailSafeException as e:
                            print(f"ReSync aborted by fail-safe: {e}")
                            return
                        except Exception as e:
                            print(f"ReSync input error: {e}")
                            return

                        with SLIDE_PROGRESS_LOCK:
                            if direction == "right":
                                SLIDE_PROGRESS += 1
                            else:
                                SLIDE_PROGRESS = max(0, SLIDE_PROGRESS - 1)

                        time.sleep(2.5)
                finally:
                    try:
                        if SERVER_IP:
                            requests.get(
                                f"http://{SERVER_IP}:{api_port}/notify/resync/end",
                                timeout=(1, 2),
                            )
                    except requests.RequestException:
                        pass

                print(f"ReSync done. Local progress={SLIDE_PROGRESS}")

            

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
                    global MDNS_ENABLED, SERVER_IP, SLIDE_PROGRESS

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

                                    print("Checking slide progress...")
                                    try:
                                        r = requests.get(
                                            f"http://{ip}:{api_port}/present/getprogress",
                                            timeout=(1, 2),
                                        )

                                        if r.status_code == 200:
                                            body = r.json()
                                            progress = body.get("progress")

                                            if progress is not None:
                                                progress = int(progress)

                                                with SLIDE_PROGRESS_LOCK:
                                                    local_progress = SLIDE_PROGRESS

                                                if local_progress == progress:
                                                    print("Same progress.")
                                                    return
                                                else:
                                                    resyncProgress(progress)
                                                    print("ReSync end.")
                                                    return

                                    except requests.RequestException:
                                        print("Request for progress failed.")
                                        continue
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
        global SLIDE_PROGRESS
        try:
            pyautogui.press("right")

            with SLIDE_PROGRESS_LOCK:
                SLIDE_PROGRESS += 1

            return JSONResponse({}, status_code=200)
        except pyautogui.FailSafeException as e:
            print(f"failsafe on /next: {e}")
            return JSONResponse({"error": "pyautogui fail-safe triggered"}, status_code=409)
        except Exception as e:
            print(f"/next error: {e}")
            return JSONResponse({"error": "failed to send next input"}, status_code=500)

    @FAPI.get("/prev")
    async def FAPI_prev():
        global SLIDE_PROGRESS
        try:
            pyautogui.press("left")

            with SLIDE_PROGRESS_LOCK:
                SLIDE_PROGRESS = max(0, SLIDE_PROGRESS - 1)

            return JSONResponse({}, status_code=200)
        except pyautogui.FailSafeException as e:
            print(f"failsafe on /prev: {e}")
            return JSONResponse({"error": "pyautogui fail-safe triggered"}, status_code=409)
        except Exception as e:
            print(f"/prev error: {e}")
            return JSONResponse({"error": "failed to send prev input"}, status_code=500)

    @FAPI.post("/shutdown")
    async def FAPI_shutdown(request: Request):
        host = request.client.host if request.client else "unknown"
        schedule_pc_shutdown(f"server {host}")
        return JSONResponse({"message": "pc shutdown scheduled"}, status_code=200)

    @FAPI.get("/shutdown")
    async def FAPI_shutdown_get(request: Request):
        return await FAPI_shutdown(request)

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
    APP_INSTANCE = app
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