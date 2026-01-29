from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaStreamTrack
from screen_capture import DXCamVideoStreamTrack
import struct
import dxcam
import cv2

# Aktive Connections speichern
peer_connections: dict[str, RTCPeerConnection] = {}

class WebRTCOffer(BaseModel):
    """SDP Offer vom Client."""
    sdp: str
    type: str  # "offer"

class WebRTCAnswer(BaseModel):
    """SDP Answer vom Server."""
    sdp: str
    type: str  # "answer"

# Callback für Laser-Updates (wird von main.py gesetzt)
on_touch_callback = None

def set_touch_callback(callback) -> None:
    """Setzt die Callback-Funktion für Touch-Events."""
    global on_touch_callback
    on_touch_callback = callback

def parse_touch_binary(data: bytes) -> tuple[int, float, float]:
    """
    Parsed Binary Touch-Event.
    
    Format: [type: 1 byte][x: 4 bytes float][y: 4 bytes float]
    
    :return: (event_type, x, y)
    """
    event_type, x, y = struct.unpack('<Bff', data)
    return event_type, x, y

async def handle_offer(offer: WebRTCOffer) -> WebRTCAnswer:
    """
    Verarbeitet SDP Offer und erstellt Answer mit Video-Track.
    
    :param offer: SDP Offer vom Client
    :return: SDP Answer
    """
    # Neue PeerConnection (lokal, keine ICE-Server nötig)
    pc = RTCPeerConnection(configuration={"iceServers": []})
    
    # Connection-ID für Cleanup
    connection_id = str(id(pc))
    peer_connections[connection_id] = pc

    # Screen Capture Video Track hinzufügen
    video_track = DXCamVideoStreamTrack()
    pc.addTrack(video_track)

    # DataChannel für Touch-Input
    @pc.on("datachannel")
    def on_datachannel(channel):
        print(f"DataChannel '{channel.label}' empfangen")
        
        @channel.on("message")
        def on_message(message):
            if isinstance(message, bytes) and len(message) == 9:
                event_type, x, y = parse_touch_binary(message)
                print(f"Touch: type={event_type}, x={x:.3f}, y={y:.3f}")
                
                if on_touch_callback:
                    on_touch_callback(event_type, x, y)

    # Connection State Logging
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            await cleanup_connection(connection_id)

    # Remote Description setzen (Offer)
    await pc.setRemoteDescription(RTCSessionDescription(
        sdp=offer.sdp,
        type=offer.type
    ))

    # Answer erstellen
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return WebRTCAnswer(
        sdp=pc.localDescription.sdp,
        type=pc.localDescription.type
    )

async def cleanup_connection(connection_id: str) -> None:
    """Räumt eine geschlossene Connection auf."""
    if connection_id in peer_connections:
        pc = peer_connections.pop(connection_id)
        await pc.close()
        print(f"Connection {connection_id} cleaned up")

async def close_all_connections() -> None:
    """Schließt alle aktiven Connections."""
    for conn_id in list(peer_connections.keys()):
        await cleanup_connection(conn_id)

camera = dxcam.create(output_color="BGR")
frame = camera.grab()

if frame is not None:
    cv2.imwrite("screenshot.png", frame)
    print("Frame camputred.")
    print(frame.shape)
else:
    print("No frame.")

camera.release