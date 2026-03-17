"""
WebSocket Manager — keeps track of all connected browsers.

Think of it like a phone exchange operator:
- Users "call in" (connect) and are assigned a line (video_id)
- When something happens, operator rings the right line
- When call ends, operator removes that line
"""
from fastapi import WebSocket
from typing import Dict, List


class WebSocketManager:
    def __init__(self):
        # Dictionary: video_id → list of connected browsers watching that video
        # Example: {16: [websocket_A, websocket_B], 20: [websocket_C]}
        # video 16 has 2 people watching, video 20 has 1 person watching
        self.connections: Dict[int, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, video_id: int):
        """
        A browser connected and wants to watch video_id's progress.

        1. Accept the WebSocket handshake (like picking up the phone)
        2. Add this browser to the list for that video_id
        """
        await websocket.accept() # must do this to establish connection
        
        # If no one was watching this video yet, create empty list
        if video_id not in self.connections:
            self.connections[video_id] = []
            
        self.connections[video_id].append(websocket)
        print(f"✅ WebSocket connected: video_id={video_id} | total watchers: {len(self.connections[video_id])}")
        
    def disconnect(self, websocket: WebSocket, video_id: int):
        """
        A browser disconnected (closed tab, lost internet, etc.)
        Remove it from our list.
        """
        if video_id in self.connections:
            self.connections[video_id].remove(websocket)
            # If nobody is watching anymore, clean up the entry
            if not self.connections[video_id]:
                del self.connections[video_id]
                
        print(f"🔌 Websocket disconnected: video_id={video_id}")
        
    async def send_progress(self, video_id: int, message: dict):
        """
        Send a progress update to ALL browsers watching this video.

        message is a dict like:
        {
            "type": "chunk_done",
            "chunk_index": 2,
            "total_chunks": 4,
            "status": "Chunk 2 transcoded ✅"
        }

        We convert it to JSON string and send it.
        """
        if video_id not in self.connections:
            return  # Nobody watching, nothing to send
        
        # Send to every browser watching this video
        dead_connections = []
        for websocket in self.connections[video_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                # Browser disconnected unexpectedly — mark for removal
                dead_connections.append(websocket)
                
        # Clean up any dead connections
        for ws in dead_connections:
            self.connections[video_id].remove(ws)
            
            
# Create ONE global instance — shared across the whole app
# Like one operator for the whole phone exchange
ws_manager = WebSocketManager()