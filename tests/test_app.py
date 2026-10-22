import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.scraper import clean_text
from app.downloader import DownloadQueueManager, DownloadItem

client = TestClient(app)

def test_clean_text():
    assert clean_text("  Test   Title  ") == "Test Title"
    assert clean_text(None) == ""

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "NCS Downloader" in response.text

def test_extract_invalid_url():
    response = client.post("/api/extract", json={"url": "https://example.com/invalid"})
    assert response.status_code == 400
    assert "Invalid Apple Music URL" in response.json()["detail"]

@patch("app.scraper.httpx.AsyncClient.get")
def test_extract_apple_music_playlist(mock_get):
    html_content = """
    <html>
    <head>
        <title>Top NCS Songs on Apple Music</title>
        <script type="application/ld+json">
        {
            "@type": "MusicPlaylist",
            "name": "NCS Hits",
            "track": [
                {
                    "item": {
                        "name": "Fade",
                        "byArtist": {"name": "Alan Walker"}
                    }
                },
                {
                    "item": {
                        "name": "Spectre",
                        "byArtist": [{"name": "Alan Walker"}]
                    }
                }
            ]
        }
        </script>
    </head>
    <body></body>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = html_content
    mock_get.return_value = mock_response

    response = client.post("/api/extract", json={"url": "https://music.apple.com/us/playlist/ncs-hits/pl.12345"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "NCS Hits"
    assert len(data["tracks"]) == 2
    assert data["tracks"][0]["title"] == "Fade"
    assert data["tracks"][0]["artist"] == "Alan Walker"

def test_download_queue_enqueue(tmp_path):
    qm = DownloadQueueManager(output_dir=str(tmp_path))
    tracks = [
        {"id": "tr_1", "title": "Fade", "artist": "Alan Walker"},
        {"id": "tr_2", "title": "Invincible", "artist": "DEAF KEV"}
    ]
    ids = qm.enqueue_tracks(tracks, search_suffix="NCS audio")
    assert len(ids) == 2
    assert qm.get_item("tr_1").title == "Fade"
    assert qm.get_item("tr_2").artist == "DEAF KEV"
