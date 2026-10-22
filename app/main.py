import asyncio
import json
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from app.scraper import scrape_apple_music_url
from app.downloader import download_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ncs_downloader.main")

app = FastAPI(title="NCS Downloader API")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

class ScrapeRequest(BaseModel):
    url: str

class TrackInfo(BaseModel):
    id: str
    title: str
    artist: str

class DownloadRequest(BaseModel):
    tracks: List[TrackInfo]
    search_suffix: Optional[str] = "NCS audio"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/extract")
async def extract_playlist(payload: ScrapeRequest):
    try:
        data = await scrape_apple_music_url(payload.url)
        return {"success": True, "data": data}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Error extracting Apple Music playlist")
        raise HTTPException(status_code=500, detail=f"Failed to scrape Apple Music page: {str(e)}")

@app.post("/api/download")
async def queue_download(payload: DownloadRequest):
    if not payload.tracks:
        raise HTTPException(status_code=400, detail="No tracks provided for download.")

    track_dicts = [t.model_dump() for t in payload.tracks]
    search_suffix = payload.search_suffix or "NCS audio"

    added_ids = download_manager.enqueue_tracks(track_dicts, search_suffix=search_suffix)
    return {"success": True, "queued_tracks": len(added_ids), "track_ids": added_ids}

@app.get("/api/queue")
async def get_queue():
    return {"success": True, "items": download_manager.get_all_items()}

@app.get("/api/events")
async def sse_events(request: Request):
    async def event_generator():
        queue_events = asyncio.Queue()

        def listener(data: dict):
            queue_events.put_nowait(data)

        download_manager.add_listener(listener)

        # Send initial status of all items
        initial_items = download_manager.get_all_items()
        yield f"event: initial\ndata: {json.dumps(initial_items)}\n\n"

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_data = await asyncio.wait_for(queue_events.get(), timeout=15.0)
                    yield f"event: update\ndata: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    # Ping to keep connection alive
                    yield "event: ping\ndata: {}\n\n"
        finally:
            download_manager.remove_listener(listener)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
