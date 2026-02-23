
# pyinstaller --noconfirm --onefile --noconsole --manifest base/manifest.manifest --add-data "assets;assets" --uac-admin --icon="./assets/repccBin.ico" main.py

# Debugger notes: Please run VSC as Administrator to debug this within VSC. ( Or any IDE you're using )

# imports

import os
import sys
import uuid
import yaml
import json
import socket
import ctypes
import pystray
import logging
import uvicorn
import threading
import subprocess
import logging.config
import re
import xml.etree.ElementTree as ET

# Windows process creation flag to hide console windows
CREATE_NO_WINDOW = 0x08000000

# --
# from's

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from PIL import Image

from zeroconf import Zeroconf, ServiceInfo

# --
# custom imports
from webrtc import startWebRTCServer
from pcmac import initializePCMAC, macro
from args import (
    LOGGER_CONF, NEW2FA, customerror, forceLogFolder, assetsPath, getSetting, sendRandomWakeNotif,
    sendNotification, getDebugSettings, getRegistryYaml, getPresentationSettings, findRegisteredHost
)

# --

MAC = ':'.join(('%012X' % uuid.getnode())[i:i+2] for i in range(0, 12, 2))
ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
TWOFACODE = None

# Redirect stderr to error log file for better debugging
ERROR_LOG_PATH = ROAMING + "\\.RePCC\\logs\\errors.txt"
try:
    os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
    sys.stderr = open(ERROR_LOG_PATH, "a", buffering=1)
except Exception:
    pass

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

        macsYaml = getRegistryYaml()

        if not macsYaml["IP"] == None:
            if request.client.host in macsYaml["IP"]:
                return JSONResponse({"message":"Success"}, status_code=202)

        logger.info(f"main | Recieved ping from {request.client.host}. Responding with OK")
        return JSONResponse({"message":"Success"}, status_code=200)

    def _macroRequests():

        @App.get("/macro/getall")
        async def macros_getall(request:Request): # NOTE: Has IP check now

            logger.info(f"main | getall request recieded by {request.client.host}")

            if not findRegisteredHost(request.client.host): #type: ignore
                logger.error("main | ERROR @ main.py/requestsInit/_macroRequests/macros_getall")
                logger.error("main | Unauthorized host attempted to access macros_getall.")
                return JSONResponse({"error":"Not allowed"}, status_code=405)
            
            logger.info("main | getall request recieded.")
            lis = [str(x)[:-6] for x in os.listdir(ROAMING+"\\.RePCC\\macros")]
            return JSONResponse({"macros":lis}, status_code=200)

        @App.get("/macro/get/{name}")
        async def macros_getone(request:Request, name:str): # NOTE: Has IP check now
            logger.info(f"main | getone request recieded by {request.client.host}")

            if not findRegisteredHost(request.client.host):
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
        
        @App.get("/settings/get/{arg}")
        async def settings_get(request:Request, arg:str):

            logger.info(f"main | settings get request recieded by {request.client.host}") #type: ignore

            if not findRegisteredHost(request.client.host): # type: ignore
                logger.error("main | ERROR @ main.py/requestsInit/_settingsRequests/settings_get")
                logger.error("main | Unauthorized host attempted to access settings_get.")
                return JSONResponse({"error":"Not allowed"}, status_code=405)

            settingsList = [x[:-5] for x in os.listdir(ROAMING+"\\.RePCC\\settings")]

            if arg == "all":
                logger.info(f"main | settings_get all request recieded by {request.client.host}") # type: ignore
                return JSONResponse(settingsList, status_code=200)
            
            elif arg in settingsList:

                logger.info(f"main | settings_get all request is individual setting file.") 
                return getSetting(arg)
            
            return JSONResponse({"error":"Setting not found."})

        @App.post("/settings/post/{arg}")
        async def settings_post(request:Request, arg:str):

            logger.info(f"main | settings_post request recieded by {request.client.host}") #type: ignore

            if not findRegisteredHost(request.client.host): # type: ignore
                logger.error("main | ERROR @ main.py/requestsInit/_settingsRequests/settings_post")
                logger.error("main | Unauthorized host attempted to access settings_post.")
                return JSONResponse({"error":"Not allowed"}, status_code=405)

            settingsList = [x[:-5] for x in os.listdir(ROAMING+"\\.RePCC\\settings")]

            if not arg[-5:] == ".yaml":
                arg = f"{arg}.yaml"

            PATH = ROAMING+"\\.RePCC\\settings\\"+arg

            if os.path.exists(PATH) and arg[:-5] in settingsList:
                try:
                    jsonData = await request.json()

                    with open(PATH, "w") as f:
                        json.dump(jsonData, f)
                        f.close()

                    logger.info(f"main | Setting {arg} saved with new data: {str(jsonData)}") 

                    return JSONResponse({}, status_code=200)             
                except json.decoder.JSONDecodeError as e:
                    return JSONResponse({"error":"No JSON has been parsed"}, status_code=405)
                except Exception as e:
                    print(e.__class__)
                    print(e)

            raise ValueError("SettingFile does not exist.")

        logger.info("main | settings requests init finished.")
    _macroRequests()
    _settingsRequests()
    logger.info("main | Requests init finished.")

#   --------------- mDNS AUTO PAIRING

MDNS = None
SERVICEINFO = None

@App.post("/connect")
async def repccConnect(request:Request):

    logger.info(f"main | Recieving new request to connect by {request.client.host}") # type: ignore[attr-defined]

    data = await request.json()
    macsYAML = getRegistryYaml()
    argsYAML = getDebugSettings()

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
        yaml.safe_dump(macsYAML, open(ROAMING+"\\.RePCC\\data\\register.yaml", "w"))
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

#   --------------- TASK SCHEDULER AUTOSTART

AUTOSTART_TASK_NAME = "RePCC Autostart"

def _autostart_supported() -> bool:
    return os.name == "nt" and getattr(sys, "frozen", False)

def _build_autostart_task_action():
    if not _autostart_supported():
        raise RuntimeError("Autostart task is only supported for frozen Windows binaries.")

    executable = os.path.abspath(sys.executable)
    return f'"{executable}"'

def _autostart_task_exists() -> bool:
    if not _autostart_supported():
        return False

    result = subprocess.run(
        ["schtasks", "/Query", "/TN", AUTOSTART_TASK_NAME],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False
    )
    return result.returncode == 0

def _autostart_enabled() -> bool:
    if not _autostart_supported():
        return False

    result = subprocess.run(
        ["schtasks", "/Query", "/TN", AUTOSTART_TASK_NAME, "/V", "/FO", "LIST"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False
    )

    if result.returncode == 0 and result.stdout.strip():
        state_match = re.search(
            r"^\s*Scheduled Task State\s*:\s*(.+?)\s*$",
            result.stdout,
            re.IGNORECASE | re.MULTILINE
        )
        if state_match:
            state_value = state_match.group(1).strip().lower()
            if state_value == "enabled":
                return True
            if state_value == "disabled":
                return False

        status_match = re.search(
            r"^\s*Status\s*:\s*(.+?)\s*$",
            result.stdout,
            re.IGNORECASE | re.MULTILINE
        )
        if status_match:
            status_value = status_match.group(1).strip().lower()
            if status_value in {"ready", "running", "queued"}:
                return True

    xml_query = subprocess.run(
        ["schtasks", "/Query", "/TN", AUTOSTART_TASK_NAME, "/XML"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False
    )

    if xml_query.returncode == 0 and xml_query.stdout.strip():
        try:
            root = ET.fromstring(xml_query.stdout)
            enabled_node = root.find(".//{*}Settings/{*}Enabled")
            if enabled_node is None:
                return True
            if enabled_node.text is not None:
                return enabled_node.text.strip().lower() == "true"
        except ET.ParseError as e:
            logger.error(customerror("main", f"Failed to parse startup task XML. {e}"))

    logger.error(customerror("main", "Could not determine startup task state from task query output."))
    return False

def _create_autostart_task() -> bool:
    if not _autostart_supported():
        logger.info("main | Startup task creation skipped (script/debug mode).")
        return False

    run_action = _build_autostart_task_action()

    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", AUTOSTART_TASK_NAME,
            "/SC", "ONLOGON",
            "/TR", run_action,
            "/RL", "HIGHEST",
            "/F"
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False
    )

    if result.returncode == 0:
        logger.info(f"main | Created startup task: {AUTOSTART_TASK_NAME}")
        return True

    logger.error(
        customerror(
            "main",
            f"Failed to create startup task. stdout={result.stdout.strip()} stderr={result.stderr.strip()}"
        )
    )
    return False

def _set_autostart_enabled(enable: bool) -> bool:
    if not _autostart_supported():
        logger.info("main | Startup task toggle skipped (script/debug mode).")
        return False

    command = "ENABLE" if enable else "DISABLE"
    result = subprocess.run(
        ["schtasks", "/Change", "/TN", AUTOSTART_TASK_NAME, f"/{command}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
        check=False
    )

    if result.returncode == 0:
        logger.info(f"main | Startup task state changed to {command}")
        return True

    logger.error(customerror("main", f"Failed to set startup task to {command}. {result.stderr.strip()}"))
    return False

def autostartInit():
    if not _autostart_supported():
        logger.info("main | Startup task init skipped (script/debug mode).")
        return

    logger.info("main | Initializing startup task...")
    if _autostart_task_exists():
        logger.info("main | Startup task already exists.")
        return

    if _create_autostart_task():
        sendNotification("RePCC Startup", "Start-on-boot task was enabled.")

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
        def exit_app(icon, item):
            logger.info("main | Tray exit requested.")
            try:
                if MDNS and SERVICEINFO:
                    MDNS.unregister_service(SERVICEINFO)
                    MDNS.close()
            except Exception as e:
                logger.error(customerror("main", f"mDNS shutdown failed: {e}"))

            icon.stop()
            os._exit(0)

        def toggle_autostart(icon, item):
            if not _autostart_supported():
                sendNotification("RePCC Startup", "Start-on-boot is only available in the built binary.")
                return

            enabled_now = _autostart_enabled()

            if not _autostart_task_exists():
                if not _create_autostart_task():
                    sendNotification("RePCC Startup", "Failed to enable start-on-boot.")
                    return
                enabled_now = True

            target_state = not enabled_now
            if _set_autostart_enabled(target_state):
                status = "enabled" if target_state else "disabled"
                sendNotification("RePCC Startup", f"Start-on-boot {status}.")
                logger.info(f"main | Start-on-boot {status} from tray menu.")
            else:
                sendNotification("RePCC Startup", "Could not change start-on-boot state.")

        tray_menu = pystray.Menu(
            pystray.MenuItem(
                "Start on boot",
                toggle_autostart,
                checked=lambda item: _autostart_enabled(),
                enabled=lambda item: _autostart_supported()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", exit_app)
        )

        # Load tray icon with fallback
        image = None
        icon_paths = [
            assetsPath("assets/repcclogo.ico"),
            os.path.join(ROAMING, ".RePCC", "applications", "assets", "repcclogo.ico"),
            os.path.join(os.path.dirname(sys.executable), "assets", "repcclogo.ico") if getattr(sys, "frozen", False) else None
        ]
        
        for icon_path in icon_paths:
            if icon_path and os.path.exists(icon_path):
                try:
                    image = Image.open(icon_path)
                    logger.info(f"main | Loaded tray icon from {icon_path}")
                    break
                except Exception as e:
                    logger.warning(customerror("main", f"Failed to load icon from {icon_path}: {e}"))
        
        if image is None:
            logger.warning(customerror("main", "No tray icon found, creating placeholder"))
            image = Image.new("RGB", (64, 64), color=(73, 109, 137))
        
        icon = pystray.Icon("repcc", image, "RePCC", tray_menu)
        icon.run()
    except Exception as e:
        import traceback
        error_msg = f"Tray initialization failed: {str(e)}\nTraceback: {traceback.format_exc()}"
        logger.error(customerror("main", error_msg))
        print(e)

#   --------------- STARTUP FUNCTIONS  

def wipeSavedIPs():

    logger.info("main | removing saved IPs from previous session...")

    register = getRegistryYaml()
    register["IP"] = None

    yaml.safe_dump(register, open(ROAMING+"\\.RePCC\\data\\register.yaml", "w"))
    logger.info(f"main | IPs wiped. Registry data: {register}")

def firewallInit():

    # RePCC Ports:
    # - 15248 Default Port
    # - 15249 WerRTC Port
    # - 15250 WerRTC Port

    logger.info("main | Checking firewall rules...")

    def _firewall_rule_exists(rule_name: str) -> bool:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule_name}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
            check=False
        )
        out = (result.stdout or "").lower()
        return "no rules match" not in out

    rules = [
        (".RePCC 15248 In", "TCP", 15248),
        (".RePCC 15249 In", "TCP", 15249),
        (".RePCC 15250 In", "TCP", 15250)
    ]

    for name, protocol, port in rules:
        if _firewall_rule_exists(name):
            logger.info(f"main | Firewall rule already exists: {name}")
            continue

        result = subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={name}",
                "dir=in",
                "action=allow",
                f"protocol={protocol}",
                f"localport={port}",
                "profile=private,domain"
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
            check=False
        )

        if result.returncode == 0:
            logger.info(f"main | Firewall rule created: {name}")
        else:
            logger.error(customerror("main", f"Failed firewall rule: {name} | {result.stderr.strip()}"))

#   --------------- MAIN 

# TODO:
# - YAML DEBUG: Integrage verbose level for notifications and debug bool idk
# - Finish Tray icon integration

def MAIN():

    global MDNS, SERVICEINFO

    def is_admin():
        try:
            logger.info("main | Checking admin...")
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            logger.info("main | is not admin.")
            return False
        
    def run_as_admin():
        # integrating this was hell
        if not is_admin():
            if getattr(sys, "frozen", False):
                lp_file = os.path.abspath(sys.executable)
                lp_params = subprocess.list2cmdline(sys.argv[1:])
                lp_dir = os.path.dirname(lp_file)
            else:
                lp_file = os.path.abspath(sys.executable)  # python.exe
                script = os.path.abspath(sys.argv[0])
                lp_params = subprocess.list2cmdline([script, *sys.argv[1:]])
                lp_dir = os.path.dirname(script)

            rc = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", lp_file, lp_params, lp_dir, 1
            )

            if rc <= 32:
                logger.error(customerror("main", f"Admin failed. ShellExecuteW rc={rc}"))
                return
            
            logger.info("\n\n-------------------RESTART-------------------")
            sys.exit(0)

        logger.info("main | Script is running in admin! Yippie!")

    logger.info("\n\n--------------------START--------------------")
    logger.info("Wakey wakey eggs 'n bakey! Time to run!")

    if not getattr(sys, "frozen", False):
        run_as_admin()
    else:
        logger.info("main | Frozen build detected; skipping run_as_admin().")

    logger.info("main | Initializing .pcmac")
    initializePCMAC()
    NEW2FA()

    logger.info("main | Running initial functions at startup...")
    wipeSavedIPs()
    requestsInit()
    autostartInit()
    firewallInit()

    logger.info("main | Initializing mDNS")
    MDNS, SERVICEINFO = registerMDNS()

    startWebRTCServer()
    logger.info(f"main | WebRTC server started.")

    threading.Thread(target=tray_main, daemon=True).start()
    logger.info("main | Started tray thread.")

    if os.name == "nt":
        logger.info(f"main | Request server started.")
        sendRandomWakeNotif()
        uvicorn.run(App, host="0.0.0.0", port=15248, log_config=None, access_log=False)
        logger.info("\n---------------------END---------------------\n") # Not guaranteed to be in log
    else:
        logger.error(f"main | App started on an operating system that is not NTFS.")

MAIN()