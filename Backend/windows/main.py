# imports

import os
import asyncio
import uvicorn

#import fastapi     # unused for now

# --
# from's

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# --
# custom imports

from webrtc import startWebRTCServer
# --

os.system("cls")

App = FastAPI(debug=True)

App.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change later to IP whitelist          
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@App.get("/ping")
async def root():
    return JSONResponse({"message":"Success"}, status_code=202)

    # TODO: Add Argparser for manual saving reading opening
    # TODO: Add HTTP requests for saving reading opening

if __name__ == "__main__":

    startWebRTCServer()

    if os.name == "nt":
        uvicorn.run(App, host="0.0.0.0", port=15248)
    else:
        print("OS is not NTFS")