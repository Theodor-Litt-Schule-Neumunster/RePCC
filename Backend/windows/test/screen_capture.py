import asyncio
import dxcam
import numpy as np
from av import VideoFrame
from aiortc import MediaStreamTrack

class DXCamVideoStreamTrack(MediaStreamTrack):
    """
    Video Track der den Bildschirm via dxcam captured.
    """
    kind = "video"

    def __init__(self, fps: int = 30):
        super().__init__()
        self.camera = dxcam.create(output_color="RGB")
        self.fps = fps
        self.frame_count = 0
        self._start_time = None

    async def recv(self) -> VideoFrame:
        """
        Liefert den nächsten Frame.
        Wird von aiortc aufgerufen.
        """
        if self._start_time is None:
            self._start_time = asyncio.get_event_loop().time()

        # Frame grabben (in executor weil blocking)
        loop = asyncio.get_event_loop()
        frame = await loop.run_in_executor(None, self._grab_frame)

        # Timing für konstante FPS
        self.frame_count += 1
        target_time = self._start_time + (self.frame_count / self.fps)
        wait_time = target_time - loop.time()
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        # Numpy Array zu VideoFrame konvertieren
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = f"1/{self.fps}"

        return video_frame

    def _grab_frame(self) -> np.ndarray:
        """Grabbed einen Frame von dxcam (blocking)."""
        frame = self.camera.grab()
        if frame is None:
            # Fallback: Schwarzer Frame wenn grab fehlschlägt
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        return frame

    def stop(self) -> None:
        """Stoppt den Track und gibt Ressourcen frei."""
        super().stop()
        if self.camera:
            self.camera.release()
            self.camera = None