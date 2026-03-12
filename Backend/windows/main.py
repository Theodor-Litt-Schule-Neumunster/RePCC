
# pyinstaller --noconfirm --onefile --noconsole --manifest base/manifest.manifest --add-data "assets;assets" --uac-admin --icon="./assets/repccBin.ico" main.py

# Debugger notes: Please run VSC as Administrator to debug this within VSC. ( Or any IDE you're using ) (Not required to run with admin)

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
    sendNotification, getDebugSettings, getRegistryYaml, getPresentationSettings, findRegisteredHost,
    getWebRtcSettings, log_exception, log_state
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
                logger.info(f"main | macro run request received | client={request.client.host} | raw_name={name}") #type: ignore[attr-defined]

                if not name[-6:] == ".pcmac":
                    name = name+".pcmac"

                PATHMACRO = ROAMING + "\\.RePCC\\macros\\" + name
                log_state(logger, "main.macros_run.request", client=request.client.host, macro=name, path=PATHMACRO) #type: ignore[attr-defined]

                if not os.path.exists(PATHMACRO):
                    logger.error(customerror("main", "Attemted to run macro that does not exist."))
                    return JSONResponse({"error":"Macro does not exist"}, status_code=404)
                
                try:
                    macroHandler = macro()

                    if not findRegisteredHost(request.client.host): #type: ignore
                        logger.warning(f"main | macro run denied for unregistered host | client={request.client.host} | macro={name}") #type: ignore[attr-defined]
                        return JSONResponse({"error":"Not allowed"}, status_code=405)

                    if macroHandler.verifyStructure(PATHMACRO):
                        logger.info(f"main | macro structure verified | macro={name}")
                        macro_thread = threading.Thread(target=macroHandler.runMacro, args=(name,), daemon=True, name=f"macro-run-{os.path.splitext(name)[0]}")
                        macro_thread.start()
                        logger.info(f"main | macro thread started | macro={name} | thread={macro_thread.name}")
                        return JSONResponse({"message":"Great success!"}, status_code=200)
                    
                    logger.warning(f"main | macro structure invalid | macro={name}")
                    return JSONResponse({"error":"Macro structure is not ok"}, status_code=400)

                except Exception as e:
                    logger.error("main | ERROR @ main.py/_macroRequests/macros_run")
                    log_exception(logger, "main", "_macroRequests/macros_run", e, client=request.client.host, macro=name, path=PATHMACRO) #type: ignore[attr-defined]
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
            if len(macsYAML["MAC"]) == argsYAML["maxSavedMacs"]:
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

    def _is_private_ipv4(ip: str) -> bool:
        return (
            ip.startswith("10.") or
            ip.startswith("192.168.") or
            (ip.startswith("172.") and 16 <= int(ip.split(".")[1]) <= 31)
        )

    def _get_local_ip() -> str:
        candidates = []

        # Prefer interface-derived IPv4 addresses, not DNS hostname resolution.
        try:
            for _, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                ip = sockaddr[0]
                if ip != "127.0.0.1":
                    candidates.append(ip)
        except Exception:
            pass

        # Also ask OS routing table for the preferred outbound interface without sending traffic.
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            candidates.append(s.getsockname()[0])
        except Exception:
            pass
        finally:
            try:
                s.close()
            except Exception:
                pass

        for ip in candidates:
            if _is_private_ipv4(ip):
                return ip

        for ip in candidates:
            if ip != "127.0.0.1":
                return ip

        try:
            logger.warning("main | Could not determine non-loopback IP for mDNS; falling back to 127.0.0.1")
        except Exception:
            pass
        return "127.0.0.1"
    
    hostname = socket.gethostname()
    local_ip = _get_local_ip()

    # Changed service type from "_http._tcp.local." to "_repcc._tcp.local."
    # Added "ports" to properties as required by the app
    serviceinfo = ServiceInfo(
        "_repcc._tcp.local.",
        f"RePCC.{hostname}._repcc._tcp.local.",
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties={
            "appversion":"0.1 INDEV",
            "mac":MAC,
            "ports":str(port), # Added ports property
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
    try:
        MACROS_DIR = os.path.join(ROAMING, ".RePCC", "macros")
        PROGRAM_FILES = os.environ.get("ProgramW6432", os.environ.get("ProgramFiles", "C:\\Program Files"))
        DESKTOP_APP_PATH = os.path.join(PROGRAM_FILES, "RePCC", "RePCC-Desktop.exe")

        active_macro_runner = None
        active_macro_thread = None
        macro_thread_lock = threading.Lock()
        error_box_lock = threading.Lock()
        error_box_showing = False

        def show_error_box(title: str, message: str):
            nonlocal error_box_showing

            def _show_box():
                nonlocal error_box_showing
                try:
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        message,
                        title,
                        0x10 | 0x10000 | 0x40000,
                    )
                except Exception as e:
                    logger.error(customerror("main", f"Failed to show error box: {e}"))
                finally:
                    with error_box_lock:
                        error_box_showing = False

            with error_box_lock:
                if error_box_showing:
                    return
                error_box_showing = True

            threading.Thread(target=_show_box, daemon=True).start()

        def launch_desktop_app(arguments: list, show_error: bool = False, notify_missing: bool = False):
            if not os.path.exists(DESKTOP_APP_PATH):
                if notify_missing:
                    sendNotification("RePCC", "RePCC-Desktop app does not exist.")
                if show_error:
                    show_error_box("RePCC", "RePCC-Desktop.exe was not found in Program Files.")
                return False

            try:
                subprocess.Popen([DESKTOP_APP_PATH, *arguments], creationflags=CREATE_NO_WINDOW)
                return True
            except Exception as e:
                logger.error(customerror("main", f"Failed to open desktop app: {e}"))
                if notify_missing:
                    sendNotification("RePCC", "Failed to open RePCC-Desktop app.")
                if show_error:
                    show_error_box("RePCC", "Failed to launch RePCC-Desktop.exe.")
                return False

        def list_macro_files():
            if not os.path.exists(MACROS_DIR):
                return []

            return sorted([x for x in os.listdir(MACROS_DIR) if x.lower().endswith(".pcmac")])

        def stop_active_macro():
            nonlocal active_macro_runner
            nonlocal active_macro_thread

            with macro_thread_lock:
                runner = active_macro_runner
                thread = active_macro_thread

            if not runner or not thread:
                return

            runner.kill = True
            if hasattr(runner, "listener") and runner.listener:
                try:
                    runner.listener.stop()
                except Exception:
                    pass

            if thread.is_alive():
                thread.join(timeout=5)

            with macro_thread_lock:
                if active_macro_thread is thread and not thread.is_alive():
                    active_macro_runner = None
                    active_macro_thread = None

        def refresh_menu(icon):
            icon.menu = build_tray_menu()
            icon.update_menu()

        def run_macro_from_tray(icon, item, macro_file_name: str):
            nonlocal active_macro_runner
            nonlocal active_macro_thread

            logger.info(f"main | tray macro run requested | macro={macro_file_name}")

            stop_active_macro()

            macro_path = os.path.join(MACROS_DIR, macro_file_name)
            log_state(logger, "main.tray.run_macro", macro=macro_file_name, path=macro_path)
            if not os.path.exists(macro_path):
                sendNotification("Macro", f"Macro '{macro_file_name}' does not exist.")
                logger.warning(f"main | tray macro missing | macro={macro_file_name}")
                refresh_menu(icon)
                return

            runner = macro()
            if not runner.verifyStructure(macro_path):
                sendNotification("Macro", f"Macro '{macro_file_name}' has invalid structure.")
                logger.warning(f"main | tray macro invalid structure | macro={macro_file_name}")
                refresh_menu(icon)
                return

            def worker():
                try:
                    logger.info(f"main | tray macro worker starting | macro={macro_file_name} | thread={threading.current_thread().name}")
                    runner.runMacro(macro_file_name)
                    logger.info(f"main | tray macro worker finished | macro={macro_file_name}")
                except Exception as e:
                    log_exception(logger, "main", "tray/run_macro", e, macro=macro_file_name, path=macro_path)
                finally:
                    nonlocal active_macro_runner
                    nonlocal active_macro_thread
                    with macro_thread_lock:
                        if active_macro_runner is runner:
                            active_macro_runner = None
                            active_macro_thread = None

            thread = threading.Thread(target=worker, daemon=True, name=f"tray-macro-{os.path.splitext(macro_file_name)[0]}")

            with macro_thread_lock:
                active_macro_runner = runner
                active_macro_thread = thread

            thread.start()
            logger.info(f"main | tray macro thread started | macro={macro_file_name} | thread={thread.name}")
            sendNotification("Macro", f"Started macro '{macro_file_name}'.")
            refresh_menu(icon)

        def delete_macro_from_tray(icon, item, macro_file_name: str):
            macro_path = os.path.join(MACROS_DIR, macro_file_name)

            if not os.path.exists(macro_path):
                sendNotification("Macro", f"Macro '{macro_file_name}' does not exist.")
                refresh_menu(icon)
                return

            try:
                os.remove(macro_path)
                sendNotification("Macro", f"Deleted macro '{macro_file_name}'.")
            except Exception as e:
                logger.error(customerror("main", f"Failed deleting macro {macro_file_name}: {e}"))
                sendNotification("Macro", f"Failed to delete macro '{macro_file_name}'.")

            refresh_menu(icon)

        def edit_macro_from_tray(icon, item, macro_file_name: str):
            macro_path = os.path.join(MACROS_DIR, macro_file_name)

            desktop_opened = launch_desktop_app(["--edit", macro_path], show_error=True, notify_missing=False)
            if desktop_opened:
                refresh_menu(icon)
                return

            try:
                subprocess.Popen(["notepad.exe", macro_path], creationflags=CREATE_NO_WINDOW)
            except Exception as e:
                logger.error(customerror("main", f"Failed opening notepad for macro edit: {e}"))

            refresh_menu(icon)

        def open_dashboard(icon, item):
            if not launch_desktop_app(["--dashboard"], show_error=True, notify_missing=False):
                return

        def add_macro(icon, item):
            if not launch_desktop_app(["--create"], show_error=False, notify_missing=True):
                return

            refresh_menu(icon)

        def exit_app(icon, item):
            logger.info("main | Tray exit requested.")

            stop_active_macro()

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

            # write setting = False
            sendNotification("RePCC", "Connections blocked.")

        def _setting_enabled(fileName:str=None, setting:str=None):
            
            settings = None

            if fileName.lower() == "debug":
                settings = getDebugSettings()

            if fileName.lower() == "presentation":
                settings = getPresentationSettings()

            if fileName.lower() == "webrtc":
                settings = getWebRtcSettings()

            if not settings is None:
                
                return settings.get(setting, False)

        def toggle_setting(fileName:str=None, setting:str=None):
            
            settings = None

            if fileName.lower() == "debug":
                settings = getDebugSettings()

            if fileName.lower() == "presentation":
                settings = getPresentationSettings()

            if fileName.lower() == "webrtc":
                settings = getWebRtcSettings()

            if not settings is None and not settings.get(setting, None) is None:
                settings[setting] = not settings[setting]

                yaml.safe_dump(settings, open(ROAMING+"\\.RePCC\\settings\\debug.yaml", "w"))

        def build_macro_menu_items():
            items = []
            macro_files = list_macro_files()

            def run_handler(macro_file_name: str):
                def _handler(icon, item):
                    run_macro_from_tray(icon, item, macro_file_name)
                return _handler

            def delete_handler(macro_file_name: str):
                def _handler(icon, item):
                    delete_macro_from_tray(icon, item, macro_file_name)
                return _handler

            def edit_handler(macro_file_name: str):
                def _handler(icon, item):
                    edit_macro_from_tray(icon, item, macro_file_name)
                return _handler

            if len(macro_files) == 0:
                items.append(pystray.MenuItem("No macros found", lambda icon, item: None, enabled=False))
            else:
                for macro_file in macro_files:
                    macro_name = macro_file[:-6]
                    items.append(
                        pystray.MenuItem(
                            macro_name,
                            pystray.Menu(
                                pystray.MenuItem(
                                    "Run",
                                    run_handler(macro_file),
                                ),
                                pystray.MenuItem(
                                    "Delete",
                                    delete_handler(macro_file),
                                ),
                                pystray.MenuItem(
                                    "Edit",
                                    edit_handler(macro_file),
                                ),
                            ),
                        )
                    )

            items.append(pystray.Menu.SEPARATOR)
            items.append(pystray.MenuItem("Add Macro", add_macro))
            items.append(pystray.MenuItem("Refresh", lambda icon, item: refresh_menu(icon)))
            return items

        def build_tray_menu():
            return pystray.Menu(
                pystray.MenuItem(
                    "Settings",
                    pystray.Menu( 
                        pystray.MenuItem(
                            "Connections",
                            lambda icon, item: toggle_setting("debug", "allowConnection"),
                            checked=lambda item: _setting_enabled("debug", "allowConnection"),
                        ),
                        pystray.MenuItem(
                            "External requests",
                            lambda icon, item: toggle_setting("debug", "allowExternalRequests"),
                            checked=lambda item: _setting_enabled("debug", "allowExternalRequests"),
                        ),
                        pystray.MenuItem(
                            "Macro execution",
                            lambda icon, item: toggle_setting("debug", "allowMacroExecution"),
                            checked=lambda item: _setting_enabled("debug", "allowMacroExecution"),
                        ),
                        pystray.MenuItem(
                            "Start on boot",
                            toggle_autostart,
                            checked=lambda item: _autostart_enabled(),
                            enabled=lambda item: _autostart_supported(),
                        ),
                    ),
                ),
                pystray.MenuItem("Open Dashboard", open_dashboard),
                pystray.MenuItem(
                    "Macros",
                    pystray.Menu(*build_macro_menu_items()),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", exit_app),
            )

        tray_menu = build_tray_menu()

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
    # - 15249 WebRTC Port
    # - 15250 mDNS Port

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