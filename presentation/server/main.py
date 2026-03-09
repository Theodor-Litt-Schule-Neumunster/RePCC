# pyinstaller --noconfirm --onefile --noconsole --add-data "assets;assets" --uac-admin --icon="./assets/repccBin.ico" main.py
# pyinstaller --noconfirm --onefile --add-data "assets;assets" --uac-admin --icon="./assets/repccBin.ico" main.py

import os
import sys
import json
import time
import socket
import subprocess
import ipaddress
import pystray
import uvicorn
import datetime
import requests
import pyautogui
import threading

from PIL import Image

from zeroconf import Zeroconf, ServiceInfo

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QListWidget, QScrollArea, QLabel, QFileDialog, QComboBox
)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore
SLIDE_PROGRESS = 0 # When reconnecting mid slide, client will auto adjust based on this number

file_lock = threading.Lock()
slide_progress_lock = threading.Lock()

REQ_APP = FastAPI(info=True)
REQ_APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WINDOW, APP = None, False

class MainWindow(QMainWindow):

    toggle_signal = pyqtSignal()
    activity_signal = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()

        self.toggle_signal.connect(self.toggle_visibility)
        self.activity_signal.connect(self._appendActivity)

        self.setWindowTitle("RePCC presenter control")
        self.resize(950,520)

        mainWidget = QWidget()
        self.setCentralWidget(mainWidget)
        mainLayout = QHBoxLayout(mainWidget)

        panel_left = QWidget()
        panel_left.setFixedWidth(150)
        layout_left = QVBoxLayout(panel_left)

        button_reload = QPushButton("Refresh")
        button_reload.clicked.connect(self.loadConnections)
        layout_left.addWidget(button_reload)

        button_select_file = QPushButton("Select File")
        button_select_file.clicked.connect(self.selectFile)
        layout_left.addWidget(button_select_file)

        self.selected_file_label = QLabel("No file selected")
        self.selected_file_label.setWordWrap(True)
        layout_left.addWidget(self.selected_file_label)

        self.selected_file_path = None

        button_upload = QPushButton("Upload")
        button_upload.clicked.connect(self.sendFile)
        layout_left.addWidget(button_upload)

        button_next = QPushButton("Next slide")
        button_next.clicked.connect(lambda: self.nextClientSlide("next"))
        layout_left.addWidget(button_next)

        button_prev = QPushButton("Prev slide")
        button_prev.clicked.connect(lambda: self.nextClientSlide("prev"))
        layout_left.addWidget(button_prev)

        button_shutdown = QPushButton("Shutdown clients")
        button_shutdown.clicked.connect(self.shutdownClients)
        layout_left.addWidget(button_shutdown)

        layout_left.addWidget(QLabel("mDNS Adapter"))

        self.mdns_adapter_combo = QComboBox()
        self.mdns_adapter_combo.currentIndexChanged.connect(self._on_mdns_adapter_changed)
        layout_left.addWidget(self.mdns_adapter_combo)

        button_refresh_adapters = QPushButton("Refresh adapters")
        button_refresh_adapters.clicked.connect(self.reloadMdnsAdapters)
        layout_left.addWidget(button_refresh_adapters)

        self.mdns_adapter_options = []
        self.selected_mdns_ip = None
        self.reloadMdnsAdapters(log_result=False)

        layout_left.addStretch(1)

        self.listWidget = QListWidget()
        self.listWidget.setAlternatingRowColors(True)

        scroll = QScrollArea()
        scroll.setWidget(self.listWidget)
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(400)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # type: ignore

        mainLayout.addWidget(panel_left)
        mainLayout.addWidget(scroll, stretch=1)

        panel_right = QWidget()
        layout_right = QVBoxLayout(panel_right)

        label_logs = QLabel("Activity")
        layout_right.addWidget(label_logs)

        self.logList = QListWidget()
        self.logList.setAlternatingRowColors(True)
        
        scroll_logs = QScrollArea()
        scroll_logs.setWidget(self.logList)
        scroll_logs.setWidgetResizable(True)
        scroll_logs.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # type: ignore

        layout_right.addWidget(scroll_logs)

        mainLayout.addWidget(panel_right)

        threading.Thread(target=self._reloadThread, daemon=True).start()

    def _appendActivity(self, message:str):
        self.logList.insertItem(0, f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}")

    def addActivity(self, message:str):
        self.activity_signal.emit(message)

    def reloadMdnsAdapters(self, log_result:bool=True):
        options = _discover_ipv4_interface_options()

        self.mdns_adapter_options = [{"label": "Auto (Default Route)", "ip": None}] + options

        old_selected_ip = self.selected_mdns_ip
        self.mdns_adapter_combo.blockSignals(True)
        self.mdns_adapter_combo.clear()

        target_index = 0
        for idx, option in enumerate(self.mdns_adapter_options):
            self.mdns_adapter_combo.addItem(option["label"])
            if old_selected_ip and option.get("ip") == old_selected_ip:
                target_index = idx

        self.mdns_adapter_combo.setCurrentIndex(target_index)
        self.selected_mdns_ip = self.mdns_adapter_options[target_index].get("ip")
        self.mdns_adapter_combo.blockSignals(False)

        if log_result:
            if self.selected_mdns_ip:
                self.addActivity(f"mDNS adapter set to {self.selected_mdns_ip}")
            else:
                self.addActivity("mDNS adapter set to Auto (Default Route)")

    def _on_mdns_adapter_changed(self, index:int):
        if index < 0 or index >= len(self.mdns_adapter_options):
            self.selected_mdns_ip = None
            return

        selected = self.mdns_adapter_options[index]
        self.selected_mdns_ip = selected.get("ip")
        if self.selected_mdns_ip:
            self.addActivity(f"Selected mDNS adapter IP: {self.selected_mdns_ip}")
        else:
            self.addActivity("Selected mDNS adapter: Auto (Default Route)")

    def getSelectedMdnsIp(self):
        return self.selected_mdns_ip

    def loadConnections(self): # NOTE: LOCK FILE integrated.
        # Preserve list scroll position across periodic refreshes.
        scroll_bar = self.listWidget.verticalScrollBar()
        old_scroll_value = scroll_bar.value()

        self.listWidget.clear()

        try:
            data = None
            with file_lock:
                with open(assetsPath("assets/connections.json"), "r") as f:
                    
                    data = json.load(f)
                    f.close()

            if not len(data) == 0:
                for i in range(len(data)):

                    keydata = data[i]
                    name = keydata.get("name", "UNKNOWN")
                    host = keydata.get("host", "UNKNOWN")
                    last = keydata.get("lastupdate", "UNKNOWN")

                    listText = f"Client {name}\n    Host: {host}\n    Last update at {last}"

                    self.listWidget.addItem(listText)
        finally:
            scroll_bar.setValue(min(old_scroll_value, scroll_bar.maximum()))

    def _reloadThread(self):
        while True:
            self.loadConnections()
            time.sleep(1)

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

            self.addActivity("Toggle visibility toggled visible.")

    def selectFile(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Share",
            "",
            "All Files (*.*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            file_name = os.path.basename(file_path)
            self.selected_file_label.setText(f"Selected: {file_name}")
            self.addActivity(f"File selected: {file_name}")

    def sendFile(self):
        if not self.selected_file_path:
            self.addActivity("Can't upload file if none is selected.")
            return

        self.addActivity("Starting upload thread.")
        threading.Thread(target=self._sendFileWorker, daemon=True).start()

    def _sendFileWorker(self):

        global SLIDE_PROGRESS
        with slide_progress_lock:
            SLIDE_PROGRESS = 0
        
        try:
            filename = os.path.basename(self.selected_file_path)
            
            connections = None
            with open(self.selected_file_path, "rb") as f:
                file_bytes = f.read()
                f.close()

            with file_lock:
                with open(assetsPath("assets/connections.json")) as f:
                    connections = json.load(f)
                    f.close()

            if connections == None:
                connections = []

            stats_lock = threading.Lock()
            stats = {
                "ok": 0,
                "failed": 0,
            }

            threads = []

            def _upload_to_client(ip: str):
                ad = f"http://{ip}:11111/presentaion" # NOTE: ad as in ADDRESS, NOTE: POST IS TESTPORT! NORMAL IS 15247
                self.addActivity(f"Sending {filename} to {ad}")

                try:
                    r = requests.post(ad, files={"file": (filename, file_bytes)}, timeout=5)
                except requests.RequestException as e:
                    with stats_lock:
                        stats["failed"] += 1
                    self.addActivity(f"Upload failed for {ip}: {e}")
                    return

                if r.status_code == 200:
                    with stats_lock:
                        stats["ok"] += 1
                    self.addActivity(f"Successfully uploaded to {ip}.")
                else:
                    with stats_lock:
                        stats["failed"] += 1
                    self.addActivity(f"Upload failed for {ip} with code {r.status_code}")

            for i in range(len(connections)):
                data = connections[i]
                ip = data.get("host", None)
                if ip == None:
                    continue

                t = threading.Thread(target=_upload_to_client, args=(ip,), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            self.addActivity(f" -- Upload finished. success={stats['ok']} failed={stats['failed']}")

        except Exception as e:
            print(e)

    def nextClientSlide(self, direction:str="next"):
        global SLIDE_PROGRESS

        normalized_direction = (direction or "").strip().lower()
        with slide_progress_lock:
            if normalized_direction == "next":
                SLIDE_PROGRESS += 1
            elif normalized_direction == "prev":
                # Slide index cannot go below zero.
                SLIDE_PROGRESS = max(0, SLIDE_PROGRESS - 1)
            current_progress = SLIDE_PROGRESS

        addActivity(f"Slide progress is now {current_progress} ({normalized_direction})")

        data = None

        with file_lock:
            try:
                with open(assetsPath("assets/connections.json")) as f:
                    data = json.load(f)
                    f.close()
            except:
                pass

        if data == None:
            data = []

        summary = {
            "ok": 0,
            "failed": 0,
            "failsafe": 0,
            "recovered": 0,
        }

        def _is_failsafe_response(resp: requests.Response) -> bool:
            if resp.status_code != 409:
                return False

            try:
                payload = resp.json()
                err = str(payload.get("error", "")).lower()
                return "fail-safe" in err or "failsafe" in err
            except Exception:
                return False

        summary_lock = threading.Lock()
        threads = []

        def _send_slide(address: str):
            http = f"http://{address}:11111/{direction}" # NOTE: TEST PORT!
            try:
                r = requests.get(http, timeout=3)
            except requests.RequestException as e:
                with summary_lock:
                    summary["failed"] += 1
                addActivity(f"!! ERROR! Failed {direction} slide for {address}: {e}")
                return

            if r.status_code == 200:
                with summary_lock:
                    summary["ok"] += 1
                addActivity(f"Send {direction} slide for {address}")
                return

            if _is_failsafe_response(r):
                with summary_lock:
                    summary["failsafe"] += 1
                addActivity(f"Fail-safe on {address}. Retrying {direction} once...")


                try:
                    retry = requests.get(http, timeout=3)
                except requests.RequestException as e:
                    with summary_lock:
                        summary["failed"] += 1
                    addActivity(f"!! ERROR! Retry failed for {address}: {e}")
                    return

                if retry.status_code == 200:
                    with summary_lock:
                        summary["ok"] += 1
                        summary["recovered"] += 1
                    addActivity(f"Recovered {direction} slide for {address} after fail-safe")
                else:
                    with summary_lock:
                        summary["failed"] += 1
                    addActivity(f"!! ERROR! Retry {direction} failed for {address} (code {retry.status_code})")
                return

            with summary_lock:
                summary["failed"] += 1
            addActivity(f"!! ERROR! Failed {direction} slide for {address} (code {r.status_code})")

        for i in range(len(data)):

            subdata = data[i]
            address = subdata.get("host", "None")

            if address == None:
                continue

            t = threading.Thread(target=_send_slide, args=(address,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        with slide_progress_lock:
            summary["progress"] = SLIDE_PROGRESS

        return summary

    def shutdownClients(self):
        data = None

        with file_lock:
            try:
                with open(assetsPath("assets/connections.json"), "r") as f:
                    data = json.load(f)
                    f.close()
            except Exception:
                data = []

        if data is None:
            data = []

        summary = {
            "ok": 0,
            "failed": 0,
            "targets": 0,
        }

        summary_lock = threading.Lock()
        threads = []

        def _send_shutdown(address: str):
            endpoint = f"http://{address}:11111/shutdown"

            try:
                response = requests.post(endpoint, timeout=3)
            except requests.RequestException as e:
                with summary_lock:
                    summary["failed"] += 1
                addActivity(f"!! ERROR! Shutdown request failed for {address}: {e}")
                return

            if response.status_code == 200:
                with summary_lock:
                    summary["ok"] += 1
                addActivity(f"Shutdown sent to {address}")
                return

            with summary_lock:
                summary["failed"] += 1
            addActivity(f"!! ERROR! Shutdown failed for {address} (code {response.status_code})")

        for i in range(len(data)):
            subdata = data[i]
            address = subdata.get("host", None)

            if not address:
                continue

            with summary_lock:
                summary["targets"] += 1

            t = threading.Thread(target=_send_shutdown, args=(address,), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        addActivity(
            f"Shutdown broadcast finished. targets={summary['targets']} ok={summary['ok']} failed={summary['failed']}"
        )
        return summary

def addActivity(message:str):
    if not WINDOW == None:
        WINDOW.addActivity(message)

def startMainWindow():

    global WINDOW, APP

    APP = QApplication(sys.argv)
    APP.setQuitOnLastWindowClosed(False)
    APP.setWindowIcon(QIcon(assetsPath("assets/repccbin.ico")))

    WINDOW = MainWindow()

    sys.exit(APP.exec())

def assetsPath(relativepath:str):
    """
    For easy file access in py script or binary
    
    :param relativepath: Relative filepath for asset. e. g. /assets/repcclogo.ico
    """

    # NOTE: Error when run inside a dosbox. "__file__" not found ?
    
    basepath = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(basepath, relativepath)

def _get_primary_ipv4() -> str:
    """
    Resolve the IPv4 currently used for outbound traffic.
    This avoids advertising host-only/virtual adapter addresses.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 80))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        sock.close()

def _is_valid_ipv4(ip:str) -> bool:
    try:
        parsed = ipaddress.ip_address(ip)
        return isinstance(parsed, ipaddress.IPv4Address)
    except Exception:
        return False

def _get_host_ipv4_candidates() -> list:
    ordered_ips = []

    primary_ip = _get_primary_ipv4()
    if _is_valid_ipv4(primary_ip) and not primary_ip.startswith("127."):
        ordered_ips.append(primary_ip)

    try:
        host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in host_ips:
            if _is_valid_ipv4(ip) and not ip.startswith("127.") and ip not in ordered_ips:
                ordered_ips.append(ip)
    except Exception:
        pass

    return ordered_ips

def _discover_ipv4_interface_options() -> list:
    """
    Discover adapter/IP pairs that can be used for mDNS advertisement.
    On Windows this uses PowerShell adapter metadata so users can avoid VPN/tunnel adapters.
    """

    options = []
    ethernet_options = []
    seen = set()

    if os.name == "nt":
        try:
            ps_command = (
                "$items = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
                "Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254*' } | "
                "ForEach-Object { "
                "$adapter = Get-NetAdapter -InterfaceIndex $_.InterfaceIndex -ErrorAction SilentlyContinue; "
                "if ($adapter -and $adapter.Status -eq 'Up') { "
                "[PSCustomObject]@{ Alias=$adapter.InterfaceAlias; Description=$adapter.InterfaceDescription; IP=$_.IPAddress } "
                "} "
                "}; "
                "$items | Sort-Object Alias, IP | ConvertTo-Json -Compress"
            )

            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=4,
            )

            if result.returncode == 0 and result.stdout.strip():
                parsed = json.loads(result.stdout)
                if isinstance(parsed, dict):
                    parsed = [parsed]

                for entry in parsed:
                    ip = str(entry.get("IP", "")).strip()
                    alias = str(entry.get("Alias", "Interface")).strip() or "Interface"
                    description = str(entry.get("Description", "")).strip()

                    if not _is_valid_ipv4(ip) or ip in seen:
                        continue

                    option = {"label": f"{alias} ({ip})", "ip": ip}
                    adapter_text = f"{alias} {description}".lower()
                    if "ethernet" in adapter_text:
                        ethernet_options.append(option)

                    options.append(option)
                    seen.add(ip)
        except Exception:
            pass

    if ethernet_options:
        return ethernet_options

    if not options:
        for ip in _get_host_ipv4_candidates():
            if ip not in seen:
                options.append({"label": f"Detected ({ip})", "ip": ip})
                seen.add(ip)

    return options

def _get_mdns_ipv4_addresses(preferred_ip:str=None) -> list:
    """
    Build an ordered IPv4 list for mDNS announcement.
    The first address is the preferred LAN address used by the client.
    """

    ordered_ips = []

    if preferred_ip and _is_valid_ipv4(preferred_ip) and not preferred_ip.startswith("127."):
        ordered_ips.append(preferred_ip)

    host_ips = _get_host_ipv4_candidates()
    for ip in host_ips:
        if ip not in ordered_ips:
            ordered_ips.append(ip)

    if not ordered_ips:
        ordered_ips.append("127.0.0.1")

    return [socket.inet_aton(ip) for ip in ordered_ips]

def _get_mdns_ipv4_strings(preferred_ip:str=None) -> list:
    addresses = _get_mdns_ipv4_addresses(preferred_ip=preferred_ip)
    return [str(ipaddress.ip_address(addr)) for addr in addresses]

def _mdnsMain(port:int, preferred_ip:str=None):
    hostname = socket.gethostname()
    mdns_addresses = _get_mdns_ipv4_addresses(preferred_ip=preferred_ip)
    mdns_address_strings = _get_mdns_ipv4_strings(preferred_ip=preferred_ip)

    preferred_ip = mdns_address_strings[0] if mdns_address_strings else "127.0.0.1"

    addActivity(f"mDNS advertise IPs: {', '.join(mdns_address_strings)}")
    addActivity(f"Preffered: {preferred_ip}")

    serviceinfo = ServiceInfo(
        "_http._tcp.local.",
        f"repccpresentationserver.{hostname}._http._tcp.local.",
        addresses=mdns_addresses,
        port=port,
        server=f"{hostname}.local.",
        properties={
            "api_port": "15247",
            "preferred_ip": preferred_ip,
        },
    )

    zc = Zeroconf()
    zc.register_service(serviceinfo)
    return zc, serviceinfo

def _requestsMain():

    def findHost(data:list, host:str):

        found = False
        key_i = None

        for i in range(len(data)):
            subdata = data[i]
            hostdata = subdata.get("host", None)

            if host == hostdata:
                found = True
                key_i = i
                break

        return found, key_i

    def removeHostEntries(data:list, host:str):
        """
        Remove all entries for a specific host from the in-memory connection list.
        Returns the updated list and number of removed entries.
        """

        if not isinstance(data, list):
            return [], 0

        filtered = [entry for entry in data if entry.get("host", None) != host]
        removed_count = len(data) - len(filtered)
        return filtered, removed_count

    def timeoutHandler(timeoutSeconds:int):
        """
        loops through the connected devices inside the JSON and checks the lastupdate key.

        If the key is older than timeoutSeconds, it will be removed from the list and a 403 will be send as a PING response.

        :param timeoutSeconds: Seconds for the timeout and disconnect
        :type timeoutSeconds: int
        :return None:
        """

        time.sleep(10)

        try:
            while True:
                time.sleep(1)

                data = None
                
                try:
                    with file_lock:
                        with open(assetsPath("assets/connections.json"), "r")  as f:
                            data = json.load(f)
                            f.close()
                finally:

                    if type(data) == list:

                        def rec_check(data:list):
                            for i in range(len(data)):
                                
                                lastupdate = data[i].get("lastupdate", 0)
                                name = data[i].get("name", "Unknown")
                                if datetime.datetime.now().timestamp() - lastupdate >= timeoutSeconds:
                                    if not WINDOW == None:
                                        WINDOW.addActivity(f"{name} has been inactive for {timeoutSeconds} seconds. Client has been removed.")
                                    del data[i]
                                    return rec_check(data)
                                
                            return data
                            
                        data = rec_check(data)
                        if data == None:
                            data = []

                        with file_lock:
                            with open(assetsPath("assets/connections.json"), "w") as f:
                                json.dump(data, f, indent=5)
                                f.close()

        finally:
            if not WINDOW == None:
                WINDOW.addActivity(f"Warning! Timeouthandler has been killed. Restarting in 10.")
            timeoutHandler(timeoutSeconds)
            pass

    def requestInit():

        @REQ_APP.get("/ping")
        async def fapi_ping(request:Request):

            try:
                data = None
                with file_lock:
                    with open(assetsPath("assets/connections.json"), "r") as f:
                        data = json.load(f)
                        f.close()

                if not type(data) == list:
                    data = []

                client_host = request.client.host  # type: ignore
                found, i = findHost(data, client_host)
                if found:
                    data[i]["lastupdate"] = datetime.datetime.now().timestamp() # type: ignore

                    with file_lock:
                        with open(assetsPath("assets/connections.json"), "w") as f:
                            json.dump(data, f, indent=5)
                            f.close()
                    return JSONResponse({}, status_code=200)

                # Defensive cleanup: ensure unauthorized ping hosts are not kept in the registry.
                cleaned_data, removed_count = removeHostEntries(data, client_host)
                if removed_count > 0:
                    with file_lock:
                        with open(assetsPath("assets/connections.json"), "w") as f:
                            json.dump(cleaned_data, f, indent=5)
                            f.close()
                    addActivity(f"Removed {client_host} from connections after ping returned 405")

                return JSONResponse({}, status_code=405)
                    
            except Exception as e:
                
                return JSONResponse({"error":"Ping failed."}, status_code=500)

        @REQ_APP.post("/connect/{name}")
        async def fapi_connect(request:Request, name:str):
            try:
                data = None
                with file_lock:
                    with open(assetsPath("assets/connections.json"), "r") as f:
                        data = json.load(f)
                        f.close()

                if not type(data) == list:
                    data = []

                found, _ = findHost(data, request.client.host) # type: ignore

                if not found:
                    newDict = {
                        "name":name,
                        "host":request.client.host, # type: ignore
                        "lastupdate":datetime.datetime.now().timestamp()
                    }

                    data.append(newDict)

                    with file_lock:
                        with open(assetsPath("assets/connections.json"), "w") as f:
                            json.dump(data, f, indent=5)
                            f.close()

                    addActivity(f"Added new device: {name}")

                    return JSONResponse({}, status_code=200)
                return JSONResponse({}, status_code=405)
            except Exception as e:
                return JSONResponse({"error":"Connect failed."}, status_code=500)

        @REQ_APP.get("/present/next")
        async def fapi_present_next(request:Request):
            if WINDOW == None:
                return JSONResponse({"error":"window not ready"}, status_code=503)

            try:
                pyautogui.press("right")
            except pyautogui.FailSafeException as e:
                addActivity(f"Local fail-safe on /present/next: {e}")
                return JSONResponse({"error":"local pyautogui fail-safe triggered"}, status_code=409)
            except Exception as e:
                addActivity(f"Local /present/next failed: {e}")
                return JSONResponse({"error":"local next input failed"}, status_code=500)

            result = WINDOW.nextClientSlide("next")
            failed = result.get("failed", 0)
            status = 200 if failed == 0 else 207
            return JSONResponse(result, status_code=status)

        @REQ_APP.get("/present/prev")
        async def fapi_present_prev(request:Request):
            if WINDOW == None:
                return JSONResponse({"error":"window not ready"}, status_code=503)

            try:
                pyautogui.press("left")
            except pyautogui.FailSafeException as e:
                addActivity(f"Local fail-safe on /present/prev: {e}")
                return JSONResponse({"error":"local pyautogui fail-safe triggered"}, status_code=409)
            except Exception as e:
                addActivity(f"Local /present/prev failed: {e}")
                return JSONResponse({"error":"local prev input failed"}, status_code=500)

            result = WINDOW.nextClientSlide("prev")
            failed = result.get("failed", 0)
            status = 200 if failed == 0 else 207
            return JSONResponse(result, status_code=status)

        @REQ_APP.get("/present/getprogress")
        async def fapi_present_progress(request:Request):
            addActivity(f"{request.client.host} requested current slide progress.")
            try:
                data = None
                with file_lock:
                    with open(assetsPath("assets/connections.json"), "r") as f:
                        data = json.load(f)
                        f.close()

                found, _ = findHost(data, request.client.host)

                if found:
                    with slide_progress_lock:
                        progress = SLIDE_PROGRESS
                    return JSONResponse({"progress":progress}, status_code=200)
                
                return JSONResponse({"message":"Not allowed"}, status_code=405)
            except Exception as e:
                print(f"fapi present progress {e}")
                return JSONResponse({"error":"fapi_resent_progress error, check print"}, status_code=405)

        @REQ_APP.get("/notify/resync/{status}")
        async def fapi_notify_resync(request:Request, status:str):
            
            from win11toast import toast

            addActivity(f"Client resync notification. {status}")

            def sendNotification(status:str):
                toast(f"RESYNC CLIENT WARNING", "STATUS: {status}")

            threading.Thread(target=sendNotification, args=(status, )).start()

        @REQ_APP.post("/present/shutdownclients")
        async def fapi_shutdown_clients(request:Request):
            if WINDOW is None:
                return JSONResponse({"error":"window not ready"}, status_code=503)

            result = WINDOW.shutdownClients()
            failed = result.get("failed", 0)
            status = 200 if failed == 0 else 207
            return JSONResponse(result, status_code=status)

    requestInit()

    threading.Thread(target=timeoutHandler, args=(30,)).start()
    uvicorn.run(REQ_APP, host="0.0.0.0", port=15247)

def _trayMain():

    threading.Thread(target=startMainWindow).start()
    
    while APP == None and WINDOW == None:
        time.sleep(.01)
    try:

        zc, serviceinfo = None, None

        def mdnsActivity(icon, item):

            nonlocal zc, serviceinfo

            mdnsActivity.enabled = not mdnsActivity.enabled # type: ignore

            addActivity(f"Toggled mDNS to {mdnsActivity.enabled}") # type: ignore

            if mdnsActivity.enabled == True: # type: ignore
                selected_ip = None
                if WINDOW is not None:
                    selected_ip = WINDOW.getSelectedMdnsIp() # type: ignore

                zc, serviceinfo = _mdnsMain(15248, preferred_ip=selected_ip)

                icon.notify("mDNS service started", "RePCC")
            if mdnsActivity.enabled == False: # type: ignore
                zc.unregister_service(serviceinfo) # type: ignore
                zc.close() # type: ignore
                icon.notify("mDNS service stopped", "RePCC")

            return

        mdnsActivity.enabled = False # type: ignore

        def toggleWindow():
            try:
                WINDOW.toggle_signal.emit() #type: ignore
            except:
                from win11toast import toast

                toast("RePCC Window", "Open fail. Try again")

        def quit_app():
            APP.quit() #type: ignore
            icon.stop()

        tray_menu = pystray.Menu(
            pystray.MenuItem("mDNS Active", mdnsActivity, checked=lambda item: mdnsActivity.enabled), # type: ignore
            pystray.MenuItem("Toggle Window", toggleWindow),
            pystray.MenuItem("Quit", quit_app)
        )

        image = Image.open(assetsPath("assets/repccBin.ico"))
        icon = pystray.Icon("repccserver", image, "RePCC Server", tray_menu)
        icon.run()

    except Exception as e:
        print(e)

if __name__ == "__main__":
    with file_lock:
        with open(assetsPath("assets/connections.json"), "w") as f:
            json.dump([], f)
            f.close()

    threading.Thread(target=_trayMain).start()
    threading.Thread(target=_requestsMain).start()