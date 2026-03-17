"""
Parallel Processor — runs multiple chunk workers at the same time.

Think of it as a manager that hires 4 workers, gives each one a chunk,
and waits for all 4 to finish before moving on.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import asyncio
from app.workers.chunk_worker import transcode_chunk
from app.websocket_manager import ws_manager


async def send_update(video_id: int, message: dict):
    """Helper to send a WebSocket message if video_id is provided."""
    if video_id:
        await ws_manager.send_progress(video_id, message)


async def process_chunks_in_parallel(
    chunks: List[Dict],
    quality: str,
    output_dir: str,
    video_id: int = None   # ← optional, needed for WebSocket updates
) -> Dict:
    """
    Process all chunks simultaneously using multiple threads.

    chunks = list of chunk_info dicts from video_splitter.split_video()

    Returns:
        {
            "results": [result_for_chunk_0, result_for_chunk_1, ...],
            "all_passed": True/False,
            "success_count": 3,
            "failed_count": 1
        }
    """
    num_chunks = len(chunks)
    print(f"\n⚡ PARALLEL PROCESSING: {num_chunks} chunks simultaneously")

    # Announce to frontend: we're starting
    await send_update(video_id, {
        "type": "parallel_start",
        "total_chunks": num_chunks,
        "quality": quality,
        "status": f"Starting {num_chunks} parallel workers for {quality}..."
    })

    results = []

    # Run all chunks in threads simultaneously
    # We use a thread pool because FFmpeg is CPU-heavy work
    with ThreadPoolExecutor(max_workers=num_chunks) as executor:
        future_to_chunk = {
            executor.submit(transcode_chunk, chunk, quality, output_dir): chunk
            for chunk in chunks
        }

        # As each chunk finishes (in whatever order), collect result and notify
        for future in as_completed(future_to_chunk):
            result = future.result()
            results.append(result)

            # Send update for THIS chunk finishing
            status_icon = "✅" if result['success'] else "❌"
            await send_update(video_id, {
                "type": "chunk_done",
                "chunk_index": result['chunk_index'],
                "chunks_done": len(results),
                "total_chunks": num_chunks,
                "success": result['success'],
                "frames_match": result.get('frames_match', False),
                "actual_frames": result.get('actual_frames', 0),
                "processing_time": result.get('processing_time', 0),
                "status": f"{status_icon} Chunk {result['chunk_index']} done ({len(results)}/{num_chunks})"
            })

    # Sort results back into chunk order
    results.sort(key=lambda r: r['chunk_index'])

    success_count = sum(1 for r in results if r['success'])
    failed_count = num_chunks - success_count

    await send_update(video_id, {
        "type": "parallel_complete",
        "success_count": success_count,
        "failed_count": failed_count,
        "all_passed": failed_count == 0,
        "status": f"All chunks done: {success_count}/{num_chunks} passed"
    })

    return {
        "results": results,
        "all_passed": failed_count == 0,
        "success_count": success_count,
        "failed_count": failed_count
    }