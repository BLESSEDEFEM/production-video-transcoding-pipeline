"""
Test that WebSocket connection works.
Connects, listens for 5 seconds, then disconnects.
"""
import asyncio
import websockets
import json

async def test():
    # Connect to WebSocket for video_id=16
    uri = "ws://localhost:8000/ws/progress/16"
    
    print(f"Connecting to: {uri}")
    
    async with websockets.connect(uri) as ws:
        print("✅ Connected!")
        
        # Listen for messages for 5 seconds
        print("Listening for 5 seconds...")
        try:
            for _ in range(10):
                message = await asyncio.wait_for(ws.recv(), timeout=0.5)
                data = json.loads(message)
                print(f"📨 Received: {data}")
        except asyncio.TimeoutError:
            print("(No messages received — that's fine, no transcoding is running)")
        except Exception as e:
            print(f"Error: {e}")
    
    print("✅ Disconnected cleanly")

asyncio.run(test())