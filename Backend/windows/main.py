# imports

import os
import logging
import uvicorn
import logging.config

# --
# from's

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# --
# custom imports

from args import LOGGER_CONF, customerror
from pcmac import initializePCMAC
from webrtc import startWebRTCServer
# --

ROAMING = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming" # type: ignore[attr-defined]

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

@App.get("settings/{file}")
async def getSetting(file:str):
    
    ...

if __name__ == "__main__":

    logger.info("\n\n--------------------START--------------------")
    logger.info("Wakey wakey eggs 'n bakey! Time to run!")


    logger.info("main | Initializing .pcmac")
    initializePCMAC()

    startWebRTCServer()
    logger.info(f"main | WebRTC server started.")

    if os.name == "nt":
        logger.info(f"main | Request server started.")
        uvicorn.run(App, host="0.0.0.0", port=15248, log_level="critical")
        logger.info("\n---------------------END---------------------\n")
    else:
        logger.error(f"main | App started on an operating system that is not NTFS.")