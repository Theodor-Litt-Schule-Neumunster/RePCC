# imports

import os
import asyncio
import uvicorn

#import fastapi     # unused for now

# --
# from's

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --
# custom imports
import laser
from laser import StartLaserpointer, UpdateLaserpointer, ClearLaserpointer, LaserPos
# --

os.system("cls")

print("Imports")

# Not used as of now. Will be used as a IP whitelist
origins = [
    "http://127.0.0.1:15248"
]

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
    return {"message":"Success"}

@App.post("/laser/start")
async def startlaser() -> dict[str, str]:
    try:
        await StartLaserpointer()
        return {"status":"laserpointer_start"}
    except Exception as e:
        print(e)
        return {"error":str(e)}
    
@App.post("/laser/update")
async def updatelaser(pos:laser.LaserPos) -> dict[str, str]:
    try:
        if laser.overlay is None:
            print("overlay not avalible")
            return {"error":"overlay not avalible"}
        
        await UpdateLaserpointer(pos) 
        return {"status":"laserpointer_update_success"}
    except Exception as e:
        print(e)
        return {"error":str(e)}


if __name__ == "__main__":
    if os.name == "nt":
        print("Running main")
        uvicorn.run(App, host="127.0.0.1", port=15248)
    else:
        print("OS is not NTFS")