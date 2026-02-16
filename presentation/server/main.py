import os
import sys
import json
import time
import socket
import pystray
import uvicorn
import datetime
import threading

from PIL import Image

from zeroconf import Zeroconf, ServiceInfo

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QListWidget, QScrollArea, QLabel
)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

REQ_APP = FastAPI(info=True)
REQ_APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WINDOW, APP = None, None

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

    def loadConnections(self):
        self.listWidget.clear()

        try:
            data = None
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

    def timeoutHandler(timeoutSeconds:int):
        """
        loops through the connected devices inside the JSON and checks the lastupdate key.

        If the key is older than timeoutSeconds, it will be removed from the list and a 403 will be send as a PING response.

        :param timeoutSeconds: Seconds for the timeout and disconnect
        :type timeoutSeconds: int
        :return None:
        """

        time.sleep(5)
        print("call")
        try:

            # datetime.datetime.now().timestamp()
            # -> 1771168987.380141
            #    In seconds

            while True:
                time.sleep(1)

                data = None
                
                try:
                    with open(assetsPath("assets/connections.json"), "r")  as f:
                        data = json.load(f)
                        f.close()
                finally:

                    changes = False

                    if type(data) == list:

                        def rec_check(data:list):
                            for i in range(len(data)):
                                
                                lastupdate = data[i].get("lastupdate", 0)
                                if datetime.datetime.now().timestamp() - lastupdate >= timeoutSeconds:
                                    del data[i]
                                    return rec_check(data)
                                    
                            
                        return ...

                        # -- del
                        for i in range(len(data)):
                            lastupdate = data[i].get("lastupdate", 0)
                            name = data[i].get("name", "Unknown")

                            if datetime.datetime.now().timestamp() - lastupdate >= timeoutSeconds:
                                del data[i]
                                changes = True
                                if not WINDOW == None:
                                    WINDOW.addActivity(f"{name} has been inactive for {timeoutSeconds} seconds. Client has been removed.")

                    if changes:
                        with open(assetsPath("assets/connections.json"), "w") as f:
                            json.dump(data, f, indent=5)
                            f.close()
                            if not WINDOW == None:
                                WINDOW.addActivity(f"connections.json updated after entry removed.")
        finally:
            print("TRUE loop block killed.")
            pass

    def requestInit():

        @REQ_APP.get("/ping")
        async def fapi_ping(request:Request):
            ... 

        @REQ_APP.get("/connect")
        async def fapi_connect(request:Request):
            ...

    requestInit()

    threading.Thread(target=timeoutHandler, args=(10,)).start()
    uvicorn.run(REQ_APP, host="0.0.0.0", port=15248)

def _trayMain():

    threading.Thread(target=startMainWindow).start()
    
    while APP == None and WINDOW == None:
        time.sleep(.01)

    try:

        zc, serviceinfo = None, None

        def mdnsActivity(icon, item):

            nonlocal zc, serviceinfo

            mdnsActivity.enabled = not mdnsActivity.enabled # type: ignore

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
    threading.Thread(target=_trayMain).start()
    threading.Thread(target=_requestsMain).start()