import os
import logging
import random
import logging.config

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
            "level": "DEBUG",
            "formatter": "simpleFormatter",
            "filename": str(ROAMING+"\\.RePCC\\logs\\repcc.log"),
            "mode": "a",
            "maxBytes": 10485760,# 10 MB
            "backupCount": 5
        }
    },
    "loggers": {
        "RePCC": {
            "level": "DEBUG",
            "handlers": ["fileHandler"],
            "propagate": False
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["consoleHandler", "fileHandler"]
    }
}

def customerror(module:str, e):
    return f"""{module} | {RANDOM_ERROR_LIST[random.randint(0, len(RANDOM_ERROR_LIST))]} - {e}"""

def forceLogFolder():
    os.mkdir(ROAMING+"\\.RePCC\\logs")

    logging.config.dictConfig(LOGGER_CONF)
    logger = logging.getLogger("RePCC")

    logger.debug("CONFIG | Log folder forefully created.")

    return logger