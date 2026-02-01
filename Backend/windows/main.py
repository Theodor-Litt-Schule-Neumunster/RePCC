# imports

import os
import uuid
import yaml
import socket
import random
import logging
import uvicorn
import logging.config

# --
# from's

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from zeroconf import Zeroconf, ServiceInfo

# --
# custom imports

from args import LOGGER_CONF, customerror
from pcmac import initializePCMAC
from webrtc import startWebRTCServer
# --

MAC = ':'.join(('%012X' % uuid.getnode())[i:i+2] for i in range(0, 12, 2))
ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
TWOFACODE = None

def NEW2FA():
    global TWOFACODE
    TWOFACODE = random.randint(11111111,99999999)

NEW2FA()

logging.config.dictConfig(LOGGER_CONF)
logger = logging.getLogger("RePCC")

os.system("cls")
App = FastAPI(debug=True)
App.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@App.get("/ping")
async def ping(request:Request):
    logger.info(f"main | Recieved ping from {request.client.host}. Responding with OK") # type: ignore[attr-defined]
    return JSONResponse({"message":"Success"}, status_code=202)

    # TODO: Add Argparser for manual saving reading opening
    # TODO: Add HTTP requests for saving reading opening

#--------------- mDNS AUTO PAIRING

@App.post("/connect")
async def repccConnect(request:Request):
    print("Request to connect")
    logger.debug(f"main | Recieving new request to connect by {request.client.host}") # type: ignore[attr-defined]

    data = await request.json()
    print(data)
    
    macsYAML = yaml.safe_load(open(ROAMING+"\\.RePCC\\settings\\register.yaml"))
    print(macsYAML)

    def pair(mac:str, macsYAML:dict):

        macsYAML = macsYAML["MAC"].append(mac)
        yaml.safe_dump(macsYAML, open(ROAMING+"\\.RePCC\\settings\\register.yaml"))
        return

    try:
        if macsYAML["MAC"] == None:
            if data["2fa"] == TWOFACODE:

                NEW2FA()

    except Exception as e:
        print(e)
        return JSONResponse({"Error":str(e)}, status_code=404)

#--------------- SETTINGS 

@App.get("settings/{file}")
async def getSetting(file:str):
    ...

def registerMDNS(port:int = 15250):
    
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
    return zc

if __name__ == "__main__":

    logger.info("\n\n--------------------START--------------------")
    logger.info("Wakey wakey eggs 'n bakey! Time to run!")

    logger.info("main | Initializing mDNS")
    mdns = registerMDNS()

    logger.info("main | Initializing .pcmac")
    #initializePCMAC()

    #startWebRTCServer()
    logger.info(f"main | WebRTC server started.")

    if os.name == "nt":
        logger.info(f"main | Request server started.")
        uvicorn.run(App, host="0.0.0.0", port=15248, log_level="critical")
        logger.info("\n---------------------END---------------------\n")
    else:
        logger.error(f"main | App started on an operating system that is not NTFS.")