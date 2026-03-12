# pyinstaller --onefile --icon="./assets/repccBin.ico" openfile.py
# pyinstaller --onefile --noconsole --icon="./assets/repccBin.ico" openfile.py

# ISSUES:
# - None as of now.

import os
import sys
import time
import json
import ctypes
import logging
import threading
import logging.config

from pcmac import macro
from pathlib import Path

from win11toast import toast

from args import forceLogFolder, customerror, LOGGER_CONF, log_exception, log_state

ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming"

try:
    logging.config.dictConfig(LOGGER_CONF)
    logger = logging.getLogger("RePCC")
except Exception as e:
    logger = forceLogFolder()

def get_opened_file_path() -> str | None:
    if len(sys.argv) < 2:
        logger.warning("openfile | get_opened_file_path called without argv path")
        return None
    path = os.path.abspath(sys.argv[1].strip('"'))
    logger.info(f"openfile | resolved opened path | path={path} | exists={os.path.exists(path)}")
    return path if os.path.exists(path) else None

def sendErrorBox(title:str="None", text:str="None"):
    style = 0x10
    ctypes.windll.user32.MessageBoxW(0, text, title, style)

def sendNotification(title:str, body:str, option:int=0):

    def on_click(args):
        arg = args.get("arguments", None)
        logger.info(f"openfile | notification action clicked | action={arg}")

        if arg == "http:Save":
            
            path = get_opened_file_path()
            log_state(logger, "openfile.save.request", path=path)
            if not path:
                logger.error(customerror("openfile", "Can not save macro with no path parsed."))
                sendErrorBox(".PCMAC File Error", "No path has been parsed. Did you open a .pcmac?")
                return
            
            if os.path.exists(path):
                macH = macro()
                verifF = macH.verifyStructure(path)

                if not verifF:

                    logger.error(customerror("openfile", "Can not save macro that is not proper macro format."))
                    sendErrorBox(".PCMAC File Error", "File is not proper macro format. Your .PCMAC might be corrupt.")
                    return
                    
                if os.path.dirname(path) == ROAMING + r"\.RePCC\macros":
                    logger.error(customerror("openfile", "Attempted to save macro that is already in saved macros."))
                    sendErrorBox(".PCMAC File Error", "Can not save macro if file is in macro save location.")
                    return
                
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
                
                name = Path(path).stem
                name = verifyName(name)
                logger.info(f"openfile | save target resolved | source={path} | macro_name={name}")

                data = None
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                        f.close()

                    log_state(logger, "openfile.save.loaded", keys=list(data.keys()) if isinstance(data, dict) else None, metadata=data.get("$data") if isinstance(data, dict) else None)

                    with open(ROAMING + f"\\.RePCC\\macros\\{name}", "w") as f:
                        json.dump(data, f, indent=5)
                        f.close()

                    sendNotification("Macro file", f"Macro was saved as {name}")
                    logger.info(f"openfile | saved new external macro: {name}")
                    return
                except Exception as e:
                    log_exception(logger, "openfile", "save/write", e, source=path, target=name)
                    sendErrorBox(".PCMAC File Error", f"Write block in save ran into a wall. {e}")
                    return

            else:
                logger.error(customerror("openfile", "Can not access path that does not exist."))
                sendErrorBox(".PCMAC File Error", "Opened file does not exist. If it does, then you must be hallucinating!")
                return

        elif arg == "http:Run":
            path = get_opened_file_path()
            log_state(logger, "openfile.run.request", path=path)

            if not path or not os.path.exists(path):
                logger.error(customerror("openfile", "Attempted to run macro that does not exist."))
                sendErrorBox(".PCMAC File Error", "Can not run macro that does not exist.")
                return
            
            macH = macro()
            if not macH.verifyStructure(path):
                logger.error(customerror("openfile", "Attempted to run macro with invalid structure."))
                sendErrorBox(".PCMAC File Error", "Can not run macro because the structure is invalid.")
                return
            
            try:
                name = Path(path).stem
                logger.info(f"openfile | starting macro from external file | source={path} | macro_name={name}.pcmac")
                macH.runMacro(name+".pcmac")
            except Exception as e:
                log_exception(logger, "openfile", "run/direct", e, source=path, macro=name)
                sendErrorBox(".PCMAC File Error", e)
            return

        elif arg == "http:Ignore":
            pass

    def on_dismissed():
        pass

    def sendwithbtn():
        toast(
            title=title,
            body=body,
            app_id="RePCC",
            duration="long",
            buttons=[
                "Save", "Run", "Ignore"
            ],
            on_click=on_click,
            on_dismissed=on_dismissed,
        )

    def send():
        toast(
            title=title,
            body=body,
            app_id="RePCC",
            duration="short",
        )

    if option == 0:
        logger.info(f"openfile | sending notification | title={title} | option=short")
        send()
    else:
        logger.info(f"openfile | sending notification | title={title} | option=interactive")
        sendwithbtn()

if __name__ == "__main__":
    opened_path = get_opened_file_path()
    log_state(logger, "openfile.main", argv=sys.argv, opened_path=opened_path)

    if not opened_path:
        sendErrorBox(".PCMAC File Error", "Can not run openfile.py because no PATH arg has been parsed.")
        sys.exit(1)

    sendNotification("Macro file", "You've opened a macro file. Would you like to save it to your Macro collection or would you like to directly run it?", 1)