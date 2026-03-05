# pyinstaller --noconfirm --onefile --noconsole --add-data "assets;assets" --uac-admin --icon="./assets/repccBin.ico" main.py

import os
import sys
import json
import time
import shutil
import socket
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
    QPushButton, QListWidget, QScrollArea, QLabel, QFileDialog
)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore

file_lock = threading.Lock()

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

    def __init__(self) -> None:
        super().__init__()

        self.toggle_signal.connect(self.toggle_visibility)

        self.setWindowTitle("RePCC presenter control")
        self.resize(950,520)

        mainWidget = QWidget()
        self.setCentralWidget(mainWidget)
        mainLayout = QHBoxLayout(mainWidget)

        panel_left = QWidget()
        panel_left.setFixedWidth(100)
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

    def addActivity(self, message:str):
        self.logList.insertItem(0, f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}")

    def loadConnections(self): # NOTE: LOCK FILE integrated.
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
            pass

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
        
        try:
            filename = os.path.basename(self.selected_file_path)
            
            files = None
            connections = None
            with open(self.selected_file_path, "rb") as f:
                files = {"file": (filename, f.read())}
                f.close()

            with file_lock:
                with open(assetsPath("assets/connections.json")) as f:
                    connections = json.load(f)
                    f.close()

            if connections == None:
                connections = []

            for i in range(len(connections)):
                data = connections[i]

                ip = data.get("host", None)
                ad = f"http://{ip}:11111/presentaion" # NOTE: ad as in ADDRESS, NOTE: POST IS TESTPORT! NORMAL IS 15247
                if not ip == None:
                    self.addActivity(f"Sending {filename} to {ad}")
                    r = requests.post(ad, files=files, timeout=5)

                    if r.status_code == 200:
                        self.addActivity("Successfully uploaded.")
                    else:
                        self.addActivity(f"Upload failed with code {r.status_code}")

            self.addActivity(" -- Upload finished.")

        except Exception as e:
            print(e)

    def nextClientSlide(self, direction:str="next"):
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

        for i in range(len(data)):

            subdata = data[i]
            address = subdata.get("host", "None")

            if not address == None:

                http = f"http://{address}:11111/{direction}" # NOTE: TEST PORT!
                r = requests.get(http)

                if r.status_code == 200:
                    addActivity(f"Send {direction} slide for {address}")
                else:
                    addActivity(f"!! ERROR! Failed {direction} slide for {address} !!")

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

def _mdnsMain(port:int):
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    serviceinfo = ServiceInfo(
        "_http._tcp.local.",
        f"repccpresentationserver.{hostname}._http._tcp.local.",
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        server=f"{hostname}.local.",
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

                found, i = findHost(data, request.client.host) # type: ignore
                if found:
                    data[i]["lastupdate"] = datetime.datetime.now().timestamp() # type: ignore

                    with file_lock:
                        with open(assetsPath("assets/connections.json"), "w") as f:
                            json.dump(data, f, indent=5)
                            f.close()
                    return JSONResponse({}, status_code=200)
                
                return JSONResponse({}, status_code=403)
                    
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
            if not WINDOW == None:
                pyautogui.press("right")
                WINDOW.nextClientSlide("next")

        @REQ_APP.get("/present/prev")
        async def fapi_present_prev(request:Request):
            if not WINDOW == None:
                pyautogui.press("left")
                WINDOW.nextClientSlide("prev")

    requestInit()

    threading.Thread(target=timeoutHandler, args=(10,)).start()
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
                zc, serviceinfo = _mdnsMain(15248)

                icon.notify("mDNS service started", "RePCC")
            if mdnsActivity.enabled == False: # type: ignore
                zc.unregister_service(serviceinfo) # type: ignore
                zc.close() # type: ignore
                icon.notify("mDNS service stopped", "RePCC")

            return

        mdnsActivity.enabled = False # type: ignore

        def toggleWindow():
            WINDOW.toggle_signal.emit() #type: ignore

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