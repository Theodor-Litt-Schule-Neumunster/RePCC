# imports

import os
import uuid
import yaml
import socket
import pystray
import logging
import uvicorn
import threading
import logging.config

# --
# from's

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from PIL import Image

from zeroconf import Zeroconf, ServiceInfo

# --
# custom imports
from pcmac import initializePCMAC
from webrtc import startWebRTCServer
from args import LOGGER_CONF, NEW2FA, customerror, forceLogFolder,  assetsPath,  sendNotification

# --

MAC = ':'.join(('%012X' % uuid.getnode())[i:i+2] for i in range(0, 12, 2))
ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
TWOFACODE = None

try:
    logging.config.dictConfig(LOGGER_CONF)
    logger = logging.getLogger("RePCC")
except Exception as e:
    logger = forceLogFolder()

os.system("cls")
App = FastAPI(debug=True)
App.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def requestsInit():
    logger.info("main | Initializing FASTAPI requests...")
    @App.get("/ping")
    async def ping(request:Request):

        macsYaml = yaml.safe_load(open(ROAMING+"\\.RePCC\\settings\\register.yaml"))

        if not macsYaml["IP"] == None:
            if request.client.host in macsYaml["IP"]: # type: ignore[attr-defined]
                return JSONResponse({"message":"Success"}, status_code=202)

        logger.info(f"main | Recieved ping from {request.client.host}. Responding with OK") # type: ignore[attr-defined]
        return JSONResponse({"message":"Success"}, status_code=200)

        # TODO: Add Argparser for manual saving reading opening
        # TODO: Add HTTP requests for saving reading opening

    def _macroRequests():

        @App.get("/macro/getall")
        async def macros_getall(request:Request):
            ...

        @App.get("/macro/get/{name}")
        async def macros_getone(request:Request, name:str):
            ...

        logger.info("main | macro requests init finished.")

    def _settingsRequests():
        ...

    _macroRequests()
    logger.info("main | Requests init finished.")

#   --------------- mDNS AUTO PAIRING

MDNS = None
SERVICEINFO = None

@App.post("/connect")
async def repccConnect(request:Request):

    print("Connect request")

    logger.debug(f"main | Recieving new request to connect by {request.client.host}") # type: ignore[attr-defined]

    data = await request.json()
    macsYAML = yaml.safe_load(open(ROAMING+"\\.RePCC\\settings\\register.yaml"))

    def pair(mac:str, ip:str, macsYAML:dict):
        print("Pair")

        if not macsYAML["MAC"] == None:
            if not mac in macsYAML["MAC"]:
                macsYAML["MAC"].append(mac)
        else: 
            macsYAML["MAC"] = [mac] # type: ignore[attr-defined]
        if not macsYAML["IP"] == None:
            if not mac in macsYAML["IP"]:
                macsYAML["IP"][mac] = ip
        else: 
            macsYAML["IP"] = {str(mac) : str(ip)}
        yaml.safe_dump(macsYAML, open(ROAMING+"\\.RePCC\\settings\\register.yaml", "w"))
        return

    try:

        print(macsYAML)

        if not macsYAML["MAC"] == None:
            if data["mac"] in macsYAML["MAC"]:
                 # type: ignore
                pair(data["mac"], request.client.host, macsYAML) # type: ignore
                logger.debug("main | Connect request accepted due to saved MAC")
                sendNotification("RePCC Connection", f"Device {request.client.host} connected.") # type: ignore
                return JSONResponse({"message":"Accepted"}, status_code=200)

        if int(data["2fa"]) == TWOFACODE:

            NEW2FA()
            print("Check 2fa")
            
            logger.debug("main | Connect request accepted. New 2FA requested.")
            pair(data["mac"], request.client.host, macsYAML) # type: ignore[attr-defined]

            if MDNS and SERVICEINFO:
                SERVICEINFO.properties["2fa"] = str(TWOFACODE) # type: ignore[attr-defined]
                MDNS.update_service(SERVICEINFO)
                logger.debug("main | Updated mDNS service with new 2FA code")

            sendNotification("RePCC Connection", f"Device {request.client.host} connected and paired.") # type: ignore
            return JSONResponse({"message":"Accepted and paired."}, status_code=200)
            
        return ValueError("2fa mismatch & no entry in connected MACs")

    except Exception as e:
        return JSONResponse({"Error":str(e)}, status_code=404)

def registerMDNS(port:int = 15250):

    from args import TWOFACODE
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    serviceinfo = ServiceInfo(
        "_http._tcp.local.",
        f"RePCC.{hostname}._http._tcp.local.",
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties={
            "appversion":"0.1 INDEV",
            "mac":MAC,
            "2fa":TWOFACODE
        },
        server=f"{hostname}.local.",
    )

    zc = Zeroconf()
    zc.register_service(serviceinfo)
    return zc, serviceinfo

#   --------------- SETTINGS 

@App.get("settings/{file}")
async def getSetting(file:str):
    ...

#   --------------- MENU TRAY

def tray_main():

    # TODO:
    #   - Close
    #   - Settings
    #       - Disallow / Allow connections
    #
    #   - Connected Clients
    #       - Disconnect from client
    #
    #   - Open Dashboard (MainWindow)
    #   - Macros (Lists Macros)
    #       - [ANY MACRO]
    #           - Delete / Run / Edit
    #       - Add Macro


    try:
        def testbool(icon, item):
            testbool.enabled = not testbool.enabled # type: ignore
            print("Event")
            print(icon, item)
            print()

        testbool.enabled = False # type: ignore

        tray_menu = pystray.Menu(
            pystray.MenuItem("BoolTest", testbool, checked=lambda item: testbool.enabled), # type: ignore
        )

        image = Image.open(assetsPath("assets/repcclogo.ico"))
        icon = pystray.Icon("repcc", image, "RePCC", tray_menu)
        icon.run()
    except Exception as e:
        print(e)

#   --------------- STARTUP FUNCTIONS  

def wipeSavedIPs():

    logger.debug("main | removing saved IPs from previous session...")

    register = yaml.safe_load(open(ROAMING+"\\.RePCC\\settings\\register.yaml", "r"))
    register["IP"] = None

    yaml.safe_dump(register, open(ROAMING+"\\.RePCC\\settings\\register.yaml", "w"))
    logger.debug(f"main | IPs wiped. Registry data: {register}")

#   --------------- MAIN 

if __name__ == "__main__":

    logger.info("\n\n--------------------START--------------------")
    logger.info("Wakey wakey eggs 'n bakey! Time to run!")

    NEW2FA()

    logger.info("main | Running initual functions at startup...")
    wipeSavedIPs()
    requestsInit()

    logger.info("main | Initializing .pcmac")
    initializePCMAC()

    logger.info("main | Initializing mDNS")
    MDNS, SERVICEINFO = registerMDNS()

    startWebRTCServer()
    logger.info(f"main | WebRTC server started.")

    threading.Thread(target=tray_main, daemon=True).start()
    logger.info("main | Started tray thread.")

    if os.name == "nt":
        logger.info(f"main | Request server started.")
        uvicorn.run(App, host="0.0.0.0", port=15248, log_level="critical")
        logger.info("\n---------------------END---------------------\n") # Not guaranteed to be in log
    else:
        logger.error(f"main | App started on an operating system that is not NTFS.")