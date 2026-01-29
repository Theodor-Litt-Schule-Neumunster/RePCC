import cv2
import mss
import uvicorn
import asyncio
import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiohttp import web

from pydantic import BaseModel

from av import VideoFrame

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
    def __init__(self, monitor_id:int = 1) -> None:
        super().__init__()
        
        self.monitor_id = monitor_id
        self.sct = mss.mss()
        self.fps = 30
        self.frame_count = 0

    async def recv(self):
        import numpy as np

        monitor = self.sct.monitors[self.monitor_id]
        screenshot = self.sct.grab(monitor)
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        pts, time_base = await self.next_timestamp()
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24") # type: ignore[attr-defined]
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

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state: {pc.connectionState}")
            if pc.connectionState == "failed" or pc.connectionState == "closed":
                await pc.close()
                pcs.discard(pc)

        video_stream = RePCC_VideoStream(monitor_id=2)
        pc.addTrack(video_stream)

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Wait for ICE gathering to complete
        while pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)

        print("Answer SDP:", pc.localDescription.sdp)

        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }

    except Exception as e:
        print(e)
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


if __name__ == "__main__":
    uvicorn.run(App, host="0.0.0.0", port=15249)