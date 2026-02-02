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

from args import LOGGER_CONF, customerror, forceLogFolder
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

@App.get("/ping")
async def ping(request:Request):

    macsYaml = yaml.safe_load(open(ROAMING+"\\.RePCC\\settings\\register.yaml"))

    if not macsYaml["IP"] == None:
        if request.client.host in macsYaml["IP"]:
            return JSONResponse({"message":"Success"}, status_code=202)

    logger.info(f"main | Recieved ping from {request.client.host}. Responding with OK") # type: ignore[attr-defined]
    return JSONResponse({"message":"Success"}, status_code=200)

    # TODO: Add Argparser for manual saving reading opening
    # TODO: Add HTTP requests for saving reading opening

#   --------------- mDNS AUTO PAIRING

@App.post("/connect")
async def repccConnect(request:Request):

    # TODO: 'NoneType' object has no attribute 'append', FIX THISSSSSS!!!!!!!!!!!!!!!!!!!

    print("Request to connect")
    logger.debug(f"main | Recieving new request to connect by {request.client.host}") # type: ignore[attr-defined]

    data = await request.json()
    print(data)
    
    macsYAML = yaml.safe_load(open(ROAMING+"\\.RePCC\\settings\\register.yaml"))

    def pair(mac:str, ip:str, macsYAML:dict):

        macsYAML = macsYAML["MAC"].append(mac)

        if not macsYAML["IP"] == None:
            if not ip in macsYAML["IP"]:
                macsYAML = macsYAML["IP"].append(ip)
        else: macsYAML = macsYAML["IP"].append(ip)

        yaml.safe_dump(macsYAML, open(ROAMING+"\\.RePCC\\settings\\register.yaml"))
        print("dump")
        return

    try:
        if int(data["2fa"]) == TWOFACODE:

            print("2FA OK")

            NEW2FA()
            pair(data["mac"], request.client.host, macsYAML)
            return JSONResponse({"message":"Accepted and paired."}, status_code=200)
        
        if not macsYAML["MAC"] == None:
            if data["mac"] in macsYAML["MAC"]:
                return JSONResponse({"message":"Accepted"}, status_code=200)
            
        return ValueError("2fa mismatch & no entry in connected MACs")

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