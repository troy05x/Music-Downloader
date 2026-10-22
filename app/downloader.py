import asyncio
import os
import logging
from typing import Dict, List, Optional, Any, Callable
import yt_dlp

logger = logging.getLogger("ncs_downloader.downloader")

def get_default_download_dir() -> str:
    env_dir = os.environ.get("DOWNLOAD_DIR")
    if env_dir:
        return env_dir
    # Check if root /downloads exists or can be created
    try:
        os.makedirs("/downloads", exist_ok=True)
        return "/downloads"
    except (PermissionError, OSError):
        local_dir = os.path.abspath("./downloads")
        os.makedirs(local_dir, exist_ok=True)
        return local_dir

class DownloadItem:
    def __init__(self, id: str, title: str, artist: str, search_suffix: str = "NCS audio"):
        self.id = id
        self.title = title
        self.artist = artist
        self.search_suffix = search_suffix
        self.status = "pending"  # pending, downloading, converting, completed, error
        self.progress = 0.0      # percentage 0 - 100
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed = 0.0
        self.eta = 0
        self.filename: Optional[str] = None
        self.bitrate: Optional[int] = None
        self.is_below_320kbps: bool = False
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "search_suffix": self.search_suffix,
            "status": self.status,
            "progress": round(self.progress, 1),
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "speed": self.speed,
            "eta": self.eta,
            "filename": self.filename,
            "bitrate": self.bitrate,
            "is_below_320kbps": self.is_below_320kbps,
            "error_message": self.error_message,
        }

class DownloadQueueManager:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or get_default_download_dir()
        os.makedirs(self.output_dir, exist_ok=True)
        self.items: Dict[str, DownloadItem] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []
        self.worker_task: Optional[asyncio.Task] = None
        self.current_item_id: Optional[str] = None

    def add_listener(self, listener: Callable[[Dict[str, Any]], None]):
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Dict[str, Any]], None]):
        if listener in self.listeners:
            self.listeners.remove(listener)

    def notify_listeners(self, item: DownloadItem):
        data = item.to_dict()
        for listener in list(self.listeners):
            try:
                listener(data)
            except Exception as e:
                logger.error(f"Error notifying listener: {e}")

    def enqueue_tracks(self, tracks: List[Dict[str, str]], search_suffix: str = "NCS audio") -> List[str]:
        added_ids = []
        for track in tracks:
            track_id = track.get("id") or f"tr_{len(self.items) + 1}"
            title = track.get("title", "Unknown Title")
            artist = track.get("artist", "Unknown Artist")

            # Re-enqueue or create item
            item = DownloadItem(id=track_id, title=title, artist=artist, search_suffix=search_suffix)
            self.items[track_id] = item
            self.queue.put_nowait(item)
            added_ids.append(track_id)
            self.notify_listeners(item)

        try:
            loop = asyncio.get_running_loop()
            if self.worker_task is None or self.worker_task.done():
                self.worker_task = loop.create_task(self._process_queue())
        except RuntimeError:
            logger.warning("No running event loop found when enqueueing tracks; worker task will start when loop runs.")

        return added_ids

    def get_all_items(self) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self.items.values()]

    def get_item(self, item_id: str) -> Optional[DownloadItem]:
        return self.items.get(item_id)

    async def _process_queue(self):
        while not self.queue.empty():
            item: DownloadItem = await self.queue.get()
            self.current_item_id = item.id
            item.status = "downloading"
            self.notify_listeners(item)

            try:
                await asyncio.to_thread(self._download_track, item)
            except Exception as e:
                logger.exception(f"Error downloading track {item.title}: {e}")
                item.status = "error"
                item.error_message = str(e)
                self.notify_listeners(item)
            finally:
                self.queue.task_done()
                self.current_item_id = None

    def _download_track(self, item: DownloadItem):
        search_query = f"ytsearch1:{item.title} {item.artist} {item.search_suffix}"

        # File naming format: "Artist - Title.mp3"
        out_template = os.path.join(self.output_dir, "%(artist,uploader)s - %(title)s.%(ext)s")

        def progress_hook(d):
            if d.get("status") == "downloading":
                item.status = "downloading"
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                item.downloaded_bytes = downloaded
                item.total_bytes = total
                item.speed = d.get("speed") or 0
                item.eta = d.get("eta") or 0
                if total > 0:
                    item.progress = min(99.0, (downloaded / total) * 100)
                self.notify_listeners(item)
            elif d.get("status") == "finished":
                item.progress = 99.0
                item.status = "converting"
                self.notify_listeners(item)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                }
            ],
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Searching and downloading: {search_query}")
            info = ydl.extract_info(search_query, download=True)

            if "entries" in info and len(info["entries"]) > 0:
                entry = info["entries"][0]
            else:
                entry = info

            # Check extracted audio bitrate
            abr = entry.get("abr") or entry.get("tbr") or 0
            if abr and isinstance(abr, (int, float)):
                item.bitrate = int(abr)
                if int(abr) < 320:
                    item.is_below_320kbps = True

            # Expected filename
            expected_filename = ydl.prepare_filename(entry)
            base, _ = os.path.splitext(expected_filename)
            mp3_filename = base + ".mp3"

            item.filename = os.path.basename(mp3_filename)
            item.progress = 100.0
            item.status = "completed"
            self.notify_listeners(item)


download_manager = DownloadQueueManager()
