import os
import cv2
import mss
import json
import time
import yaml
import logging
import uvicorn
import asyncio
import threading
import logging.config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from laser import StartLaserpointer, UpdateLaserpointer, ClearLaserpointer, LaserPos
from aiohttp import web

from pydantic import BaseModel

from av import VideoFrame
from args import LOGGER_CONF, customerror, forceLogFolder

try:
    logging.config.dictConfig(LOGGER_CONF)
    logger = logging.getLogger("RePCC")
except:
    logger = forceLogFolder()

APPDATA = os.path.expanduser(os.getenv("USERPROFILE")) + "\\AppData\\Roaming\\.RePCC" # type: ignore[attr-defined]
SETTINGS = APPDATA+"\\settings\\"

VERBOSE = False

App = FastAPI(debug=True)
App.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OfferRequest(BaseModel):
    sdp: str
    type: str

class RePCC_VideoStream(VideoStreamTrack):
    def __init__(self, monitor_id:int = 0) -> None:
        super().__init__()

        loaded_settings = yaml.safe_load(open(SETTINGS+"webrtc.yaml"))
        self.loaded_settings = loaded_settings

        fps = self.loaded_settings["video"].get("framerate", 24)
        
        self.monitor_id = monitor_id
        self.sct = mss.mss()
        self.fps = int(fps)
        self.frame_count = 0

        if self.monitor_id == 0: self.monitor_id = loaded_settings["video"].get("monitor", 1)

    async def recv(self):
        import numpy as np

        qual = self.loaded_settings["video"].get("quality", 2)

        monitor = self.sct.monitors[self.monitor_id]
        screenshot = self.sct.grab(monitor)
        frame = np.array(screenshot)
        frame = cv2.resize(frame, (monitor["width"]//int(qual), monitor["height"]//int(qual)))

        pts, time_base = await self.next_timestamp()
        video_frame = VideoFrame.from_ndarray(frame, format="bgra") # type: ignore[attr-defined]
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

pcs = set()

@App.post("/offer")
async def offer(request: OfferRequest):
    try:
        offer = RTCSessionDescription(sdp=request.sdp, type=request.type)
        pc = RTCPeerConnection()
        pcs.add(pc)

        @pc.on("datachannel")
        def on_datachannel(channel):
            if channel.label == "laser":

                logger.info(f"WebRTC | laser datachannel has been created.")

                lastupdate = time.time()

                @channel.on("message")
                async def on_message(message):
                    try:
                        currenttime = time.time()
                        if currenttime - lastupdate >= 1/30:
                            currenttime = lastupdate
                            data = json.loads(message)
                            pos = LaserPos(x=data["x"], y=data["y"])
                            await UpdateLaserpointer(pos=pos)
                    except Exception as e:
                        logger.error(f"WebRCT | ERROR @ webrct.py/offer/on_datachannel")
                        logger.error(customerror("WebRTC", e))

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            if pc.connectionState == "connected":
                logger.info(f"WebRTC | starting laserpointer...")
                await StartLaserpointer()
                logger.info(f"WebRTC | laserpointer started.")
            elif pc.connectionState == "failed" or pc.connectionState == "closed":
                await ClearLaserpointer()
                await pc.close()
                pcs.discard(pc)
                logger.info(f"WebRTC | Laserpointer cleared and closed PeerConnection")

        video_stream = RePCC_VideoStream()
        pc.addTrack(video_stream)

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Wait for ICE gathering to complete
        while pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)

        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }

    except Exception as e:
        logger.error("WebRCT | ERROR @ webrct.py/offer")
        logger.error(customerror("WebRCT", e))
        return web.json_response({"error": str(e)}, status=500)

def _runWEBRTC():
    logger.info("WebRTC server running.")
    uvicorn.run(App, host="0.0.0.0", port=15249)

def startWebRTCServer():
    threading.Thread(target=_runWEBRTC, daemon=True).start()

if __name__ == "__main__": 
    _runWEBRTC()