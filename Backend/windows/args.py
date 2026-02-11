# Baselevel functions that are reused in multiple files

import os
import sys
import time
import yaml
import random
import logging
import threading
import logging.config

from win11toast import toast

ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
RANDOM_ERROR_LIST = [
    "Well... this is akward!",
    "50 / 50 chance this is your fault, or my coding.",
    "The script ran into a lamppost while looking at its phone.",
    "Dinner is on you for this one.",
    "Maybe I can make a macro that fixes this...?",
    "Low quality code with low quality errors! Hah! Not funny? Alright...",
    "Please do not report this issue on our github issues page, I WILL be ashamed :(",
    "Just pretend this never happened...",
    "The script overslept.",
    "Uh oh.",
    "We are not getting out of the streets with this code!",
    "Git commit -m \"... hmm...",
    "Congrats! You found this before Copilot did!",
    "Erm... Cursor! Fix this!",
    "And I wonder why no company wants me!",
    "This error is probably on me... sorry....",
    "The script was busy searching for the second sock.",
    ":("
]

ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]
TWOFACODE = None

LOGGER_CONF = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simpleFormatter": {
            "format": "%(asctime)s | %(levelname)-7s | %(name)-12s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "consoleHandler": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simpleFormatter",
            "stream": "ext://sys.stdout"
        },
        "fileHandler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "simpleFormatter",
            "filename": str(ROAMING+"\\.RePCC\\logs\\repcc.log"),
            "mode": "a",
            "maxBytes": 10485760,# 10 MB
            "backupCount": 5
        }
    },
    "loggers": {
        "RePCC": {
            "level": "INFO",
            "handlers": ["fileHandler"],
            "propagate": False
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["consoleHandler", "fileHandler"]
    }
}

def customerror(module:str, e):
    return f"""{module} | {RANDOM_ERROR_LIST[random.randint(0, len(RANDOM_ERROR_LIST)-1)]} - {e}"""

def forceLogFolder():

    os.makedirs(ROAMING+"\\.RePCC\\logs")

    logging.config.dictConfig(LOGGER_CONF)
    logger = logging.getLogger("RePCC")

    logger.debug("CONFIG | Log folder forefully created.")

    return logger

def NEW2FA():
    global TWOFACODE
    TWOFACODE = random.randint(11111111,99999999)

def assetsPath(relativepath:str):
    """
    For easy file access in py script or binary
    
    :param relativepath: Relative filepath for asset. e. g. /assets/repcclogo.ico
    """
    basepath = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(basepath, relativepath)

def sendNotification(title:str, body:str):

    def _():
        toast(
            title=title,
            body=body,
            icon=assetsPath("assets/repcclogo.ico"),
            duration="short"
        )

    threading.Thread(target=_).start()

def getDebugSettings() -> dict:
    """
    Fetches the settings for DEBUG yaml in user roaming.
    """

    yamlfile = ROAMING+"\\.RePCC\\settings\\debug.yaml"

    load = yaml.safe_load(open(yamlfile))
    return load

def getRegistryYaml() -> dict:
    """
    Fetches the entries for REGISTRY yaml in user roaming.
    """
    yamlfile = ROAMING+"\\.RePCC\\settings\\register.yaml"

    load = yaml.safe_load(open(yamlfile))
    return load

def getPresentationSettings() -> dict:
    """
    Fetches the settings for PRESENTATIONTOOLS yaml in user roaming.
    """

    yamlfile = ROAMING+"\\.RePCC\\settings\\presentationTools.yaml"

    load = yaml.safe_load(open(yamlfile))
    return load

def findRegisteredHost(ip:str) -> bool:
    registerYAML = getRegistryYaml()
    debugYAML = getDebugSettings()

    _debug_allowExternal = debugYAML.get("allowExternalRequests", False)

    if registerYAML["IP"] == None and _debug_allowExternal == False:
        return False
                    
    found = False
    for key in registerYAML["IP"]:
        if registerYAML["IP"][key] == ip or _debug_allowExternal == True: 
            found = True
            break

    if found:
        return True
    
    return False