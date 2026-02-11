# imports

import os
import uuid
import yaml
import json
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
from pcmac import initializePCMAC, macro
from webrtc import startWebRTCServer

# Multiline because it was getting a little too long
from args import LOGGER_CONF, NEW2FA, customerror, forceLogFolder, assetsPath
from args import sendNotification, getDebugSettings, getRegistryYaml, getPresentationSettings, findRegisteredHost

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
App = FastAPI(info=True)
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
        async def macros_getall(request:Request): # NOTE: Has IP check now

            logger.info(f"main | getall request recieded by {request.client.host}") #type: ignore

            if not findRegisteredHost(request.client.host): #type: ignore
                logger.error("main | ERROR @ main.py/requestsInit/_macroRequests/macros_getall")
                logger.error("main | Unauthorized host attempted to access macros_getall.")
                return JSONResponse({"error":"Not allowed"}, status_code=405)
            
            logger.info("main | getall request recieded.")
            lis = [str(x)[:-6] for x in os.listdir(ROAMING+"\\.RePCC\\macros")]
            return JSONResponse({"macros":lis}, status_code=200)

        @App.get("/macro/get/{name}")
        async def macros_getone(request:Request, name:str): # NOTE: Has IP check now
            logger.info(f"main | getone request recieded by {request.client.host}") #type: ignore

            if not findRegisteredHost(request.client.host): #type: ignore
                logger.error("main | ERROR @ main.py/requestsInit/_macroRequests/macros_getone")
                logger.error("main | Unauthorized host attempted to access macros_getone.")
                return JSONResponse({"error":"Not allowed"}, status_code=405)
            try:
                data = await request.json()
                method = data.get("METHOD", None)

                if not method == None and not name == None:

                    PATH = ROAMING+"\\.RePCC\\macros\\"+name

                    if not name[-6:] == ".pcmac":
                        PATH = PATH + ".pcmac"

                    if method == "DATA":
                        if os.path.exists(PATH):

                            macrodata = None
                            with open(PATH, "r") as macrofile:

                                macrodata = json.load(macrofile)
                                macrofile.close()
                            
                            return JSONResponse(macrodata, status_code=200)
                        return

                    if method == "CHECK":
                        
                        if os.path.exists(PATH):
                            return JSONResponse({}, status_code=200)
                        return JSONResponse({}, status_code=404)
                    return JSONResponse({"error":"Method is not DATA or CHECK"}, status_code=403)
                else:
                    return JSONResponse({"error":"Method is not in JSON"}, status_code=403)
                
            except Exception as e:
                return JSONResponse({"error":str(e)}, status_code=403)

        @App.get("/macro/run/{name}")
        async def macros_run(request:Request, name:str): # NOTE: Has IP check now
            if name:

                if not name[-6:] == ".pcmac":
                    name = name+".pcmac"

                PATHMACRO = ROAMING + "\\.RePCC\\macros\\" + name

                if not os.path.exists(PATHMACRO):
                    logger.error(customerror("main", "Attemted to run macro that does not exist."))
                    return JSONResponse({"error":"Macro does not exist"}, status_code=404)
                
                try:
                    macroHandler = macro()

                    if not findRegisteredHost(request.client.host): #type: ignore
                        return JSONResponse({"error":"Not allowed"}, status_code=405)

                    if macroHandler.verifyStructure(PATHMACRO):
                        threading.Thread(target=macroHandler.runMacro, args=(name,)).start()
                        return JSONResponse({"message":"Great success!"}, status_code=200)
                    
                    return JSONResponse({"error":"Macro structure is not ok"}, status_code=400)

                except Exception as e:
                    logger.error("main | ERROR @ main.py/_macroRequests/macros_run")
                    logger.error(customerror("main", e))
                    return JSONResponse({"error":"Fail inside macros_run"}, status_code=500)
            else: 
                customerror("main", "Attempted to run macro without parsing name.")
                return JSONResponse({"error":"Running needs a name parsed."}, status_code=405)

        @App.post("/macro/save")
        async def macros_save(request:Request): # NOTE: Has IP check now

            logger.info(f"main | save macro post request recieded by {request.client.host}") #type: ignore

            if not findRegisteredHost(request.client.host): #type: ignore
                logger.error("main | ERROR @ main.py/requestsInit/_macroRequests/macros_save")
                logger.error("main | Unauthorized host attempted to access macros_save.")
                return JSONResponse({"error":"Not allowed"}, status_code=405)

            try:
                def verifyName(name:str):

                    nameSuffix = ""
                    i = 0

                    while True:
                        print(f"{name}{nameSuffix}.pcmac")
                        if not os.path.exists(ROAMING+f"\\.RePCC\\macros\\{name}{nameSuffix}.pcmac"):
                            name = f"{name}{nameSuffix}.pcmac"
                            break
                        
                        i=i+1
                        nameSuffix = f"({i})"

                    return name

                jsonData = await request.json()
                if "name" in jsonData and "macro" in jsonData:
                    
                    macrohandler = macro()
                    if macrohandler.verifyStructure(jsonData["macro"]):
                        name = verifyName(jsonData["name"])

                        with open(ROAMING+"\\.RePCC\\macros\\"+name, "w") as f:
                            json.dump(jsonData["macro"], f, indent=5)
                            f.close()

                        sendNotification("Macro update", f"New macro \"{name}\" has been added.")
                        logger.info(f"main | New macro \"{name}\" has been added to Roaming\\.RePCC\\macros")
                        return JSONResponse({"message":"New macro saved."}, status_code=200)

            except json.decoder.JSONDecodeError as e:
                logger.error("main | JSONDECODE ERROR @ main.py/reqiestsInit/_macroRequests/macros_save")
                logger.error(customerror("main", e))
                return JSONResponse({"error":str(e)}, status_code=500)

        @App.get("/macro/presenter/{direction}")
        async def macros_presenter_back(request:Request, direction:str):

            logger.info(f"main | presenter request recieded by {request.client.host}") #type: ignore

            if not findRegisteredHost(request.client.host): #type: ignore
                logger.error("main | ERROR @ main.py/requestsInit/_macroRequests/macros_presenter_back")
                logger.error("main | Unauthorized host attempted to access macros_presenter_back.")
                return JSONResponse({"error":"Not allowed"}, status_code=405)
            
            presentationYaml = getPresentationSettings()
            buttons = presentationYaml["buttons"]
            key = buttons.get(direction, None)

            if not key == None:
                macroHandler = macro()
                macroHandler.presenter(key)
                return JSONResponse({}, status_code=200)
            
            return JSONResponse({"error":"Key not found."}, status_code=404)

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

    logger.info(f"main | Recieving new request to connect by {request.client.host}") # type: ignore[attr-defined]

    data = await request.json()
    macsYAML = yaml.safe_load(open(ROAMING+"\\.RePCC\\settings\\register.yaml"))
    argsYAML = macsYAML["ARGS"]

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

        if not macsYAML["MAC"] == None:
            if data["mac"] in macsYAML["MAC"]:
                pair(data["mac"], request.client.host, macsYAML) # type: ignore
                logger.info("main | Connect request accepted due to saved MAC")
                sendNotification("RePCC Connection", f"Device {request.client.host} connected.") # type: ignore
                return JSONResponse({"message":"Accepted"}, status_code=200)
            
        if argsYAML["allowConnection"] == False:
            print("Connect set to false, denied.")
            logger.info("main | Attempted connection denied. allowConnection: False")
            return JSONResponse({"error":"Connections are unallowed as of now."}, status_code=405)
        
        if not macsYAML["MAC"] == None:
            if len(macsYAML["MAC"]) == argsYAML["maxSavedMACs"]:
                print("MAC limit, false.")
                logger.info("main | Attempted connection denied. Length of saved MACs is at set limit.")
                return JSONResponse({"error":"Connections are unallowed as of now."}, status_code=405)
        
        if not macsYAML["IP"] == None:
            if len(macsYAML["IP"]) == argsYAML["maxSavedIPs"]:
                print("IP limit, false.")
                logger.info("main | Attempted connection denied. Limit of connections reached.")
                return JSONResponse({"error":"Connections are unallowed as of now."}, status_code=405)

        from args import TWOFACODE
        if int(data["2fa"]) == int(TWOFACODE):
            NEW2FA()
            
            logger.info("main | Connect request accepted. New 2FA requested.")
            pair(data["mac"], request.client.host, macsYAML) # type: ignore[attr-defined]

            if MDNS and SERVICEINFO:
                SERVICEINFO.properties["2fa"] = str(TWOFACODE) # type: ignore[attr-defined]
                MDNS.update_service(SERVICEINFO)
                logger.info("main | Updated mDNS service with new 2FA code")

            sendNotification("RePCC Connection", f"Device {request.client.host} connected and paired.") # type: ignore
            return JSONResponse({"message":"Accepted and paired."}, status_code=200)
            
        return ValueError("2fa mismatch & no entry in connected MACs")

    except Exception as e:
        logger.error("main | ERROR @ main.py/repccConnect")
        logger.error(customerror("main", e))
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

    logger.info("main | removing saved IPs from previous session...")

    register = yaml.safe_load(open(ROAMING+"\\.RePCC\\settings\\register.yaml", "r"))
    register["IP"] = None

    yaml.safe_dump(register, open(ROAMING+"\\.RePCC\\settings\\register.yaml", "w"))
    logger.info(f"main | IPs wiped. Registry data: {register}")

#   --------------- MAIN 

# TODO:
# - YAML DEBUG: Integrage verbose level for notifications and debug bool idk
# - Finish Tray icon integration
# - Start settings requests
# - Fix trail from laserpointer not disappearing when let go
# - Add variable trail length in settings

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