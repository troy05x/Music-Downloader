import re
import json
import logging
from typing import List, Dict, Optional, Any
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("ncs_downloader.scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Strip whitespace, unescape html, fix weird spaces
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned

async def scrape_apple_music_url(url: str) -> Dict[str, Any]:
    """
    Scrapes an Apple Music URL (Playlist, Album, or Track) using httpx and BeautifulSoup4.
    Extracts metadata including title, type, and list of tracks (artist + song title).
    """
    if "music.apple.com" not in url:
        raise ValueError("Invalid Apple Music URL. URL must contain 'music.apple.com'.")

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15.0) as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch Apple Music page. HTTP Status Code: {response.status_code}")

    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")

    tracks: List[Dict[str, str]] = []
    title = "Apple Music Collection"
    collection_type = "collection"

    # Try 1: Look for JSON-LD script tags
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    for script in json_ld_scripts:
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                items = data
            else:
                items = [data]

            for item in items:
                item_type = item.get("@type", "")
                if item_type in ["MusicPlaylist", "MusicAlbum"]:
                    title = item.get("name", title)
                    collection_type = "playlist" if item_type == "MusicPlaylist" else "album"
                    track_items = item.get("track", []) or item.get("tracks", [])
                    if isinstance(track_items, dict):
                        track_items = track_items.get("itemListElement", [])

                    for index, t in enumerate(track_items, start=1):
                        t_item = t.get("item", t) if isinstance(t, dict) else t
                        if isinstance(t_item, dict):
                            t_title = t_item.get("name", "")
                            by_artist = t_item.get("byArtist", {})
                            if isinstance(by_artist, list):
                                artist = ", ".join([a.get("name", "") for a in by_artist if isinstance(a, dict)])
                            elif isinstance(by_artist, dict):
                                artist = by_artist.get("name", "")
                            else:
                                artist = str(by_artist) if by_artist else ""

                            if t_title:
                                tracks.append({
                                    "id": f"tr_{index}",
                                    "title": clean_text(t_title),
                                    "artist": clean_text(artist) or "Unknown Artist"
                                })

                elif item_type == "MusicRecording":
                    # Single track
                    t_title = item.get("name", "")
                    by_artist = item.get("byArtist", {})
                    if isinstance(by_artist, list):
                        artist = ", ".join([a.get("name", "") for a in by_artist if isinstance(a, dict)])
                    elif isinstance(by_artist, dict):
                        artist = by_artist.get("name", "")
                    else:
                        artist = str(by_artist) if by_artist else ""

                    if t_title:
                        title = t_title
                        collection_type = "song"
                        tracks.append({
                            "id": "tr_1",
                            "title": clean_text(t_title),
                            "artist": clean_text(artist) or "Unknown Artist"
                        })
        except Exception as e:
            logger.warning(f"Failed to parse JSON-LD script: {e}")

    # Fallback Try 2: DOM Parsing if JSON-LD didn't yield tracks
    if not tracks:
        # Check meta title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = clean_text(og_title["content"])

        # Scraping HTML elements (Apple music Web Player track rows)
        # Look for track rows in Apple Music web DOM structure
        track_rows = soup.find_all("div", class_=re.compile(r"track-lockup|songs-list-row|row"))
        if not track_rows:
            track_rows = soup.find_all("div", {"data-testid": re.compile(r"track|song")})

        for index, row in enumerate(track_rows, start=1):
            title_el = row.find(class_=re.compile(r"title|song-name|track-name"))
            artist_el = row.find(class_=re.compile(r"artist|sub-title|by-line"))

            song_title = clean_text(title_el.get_text()) if title_el else ""
            artist_name = clean_text(artist_el.get_text()) if artist_el else ""

            if song_title:
                tracks.append({
                    "id": f"tr_{index}",
                    "title": song_title,
                    "artist": artist_name or "Unknown Artist"
                })

    # Fallback Try 3: Regex match script metadata tags if DOM didn't work
    if not tracks:
        # Search page title for "Song by Artist" or "Playlist by Artist"
        page_title = soup.title.get_text() if soup.title else ""
        if page_title:
            title = clean_text(page_title.split(" - ")[0].split(" on Apple Music")[0])

    return {
        "url": url,
        "title": title,
        "type": collection_type,
        "total_tracks": len(tracks),
        "tracks": tracks
    }
