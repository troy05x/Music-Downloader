# NCS Downloader 🎵

**NCS Downloader** is a lightweight, containerized full-stack web application tailored for **CasaOS** (Ubuntu 26). It takes public Apple Music playlist, album, or track URLs, extracts the song titles and artists, searches open-license/NCS audio using `yt-dlp`, converts the audio to high-quality **320 Kbps MP3** files using `ffmpeg`, and saves them directly to your local CasaOS media directory (`/DATA/Media/Music`).

---

## 🚀 Tech Stack

* **Backend:** Python 3.11 with FastAPI and Uvicorn.
* **Frontend:** Single-page HTML/JS with Tailwind CSS (CDN) in dark mode, updated in real time via Server-Sent Events (SSE).
* **Scraper:** `httpx` and `BeautifulSoup4` (parses JSON-LD metadata & DOM elements).
* **Audio Processing:** `yt-dlp` python module with `ffmpeg` post-processing for 320kbps MP3 conversion and metadata tagging.
* **Containerization:** Docker & Docker Compose with full `x-casaos` dashboard metadata support.

---

## 📂 Project Structure

```text
.
├── Dockerfile              # Docker container configuration with Python 3.11 & ffmpeg
├── docker-compose.yml      # Docker Compose setup including x-casaos metadata
├── requirements.txt        # Python dependencies
├── README.md               # Documentation & CasaOS deployment guide
├── app/
│   ├── main.py             # FastAPI REST endpoints & SSE streaming updates
│   ├── scraper.py          # Apple Music playlist, album & track scraper
│   ├── downloader.py       # Sequential download queue manager & yt-dlp processor
│   └── static/
│       └── index.html      # Dark mode frontend UI with Tailwind CSS
└── tests/
    └── test_app.py         # Pytest test suite
```

---

## 🛠️ Step-by-Step CasaOS Deployment Guide

Follow these steps to deploy NCS Downloader on your CasaOS server:

### Prerequisites
* A running **CasaOS** installation (e.g., on Ubuntu 26).
* The target music folder exists on your host system:
  ```bash
  sudo mkdir -p /DATA/Media/Music
  sudo chmod -R 777 /DATA/Media/Music
  ```

---

### Method 1: Deploying via CasaOS Web Dashboard (Recommended)

1. **Log in to CasaOS Web UI** (usually `http://<your-server-ip>`).
2. Click the **`+` (Install Custom App)** button on the top left of the CasaOS main dashboard.
3. In the top right corner of the app installation window, click **`Import`**.
4. Select **`Docker Compose`**.
5. Paste the complete contents of `docker-compose.yml`:

   ```yaml
   version: '3.8'

   services:
     ncs-downloader:
       build:
         context: .
         dockerfile: Dockerfile
       image: ncs-downloader:latest
       container_name: ncs-downloader
       restart: unless-stopped
       ports:
         - "8080:8080"
       volumes:
         - /DATA/Media/Music:/downloads
       environment:
         - DOWNLOAD_DIR=/downloads
         - TZ=UTC

   x-casaos:
     architectures:
       - amd64
       - arm64
       - arm
     main: ncs-downloader
     description:
       en_us: "Extract Apple Music tracks and search, download, and convert open-license/NCS audio directly to your local media directory in 320kbps MP3 format."
     tagline:
       en_us: "Apple Music Open-License & NCS Audio Downloader"
     developer: "NCS Downloader Team"
     author: "NCS Downloader"
     icon: "https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/music.png"
     thumbnail: "https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/music.png"
     title:
       en_us: "NCS Downloader"
     category: "Music"
     port_map: "8080"
     index: /
   ```

6. Click **Submit** / **Install**.
7. CasaOS will automatically create the application tile named **NCS Downloader** on your dashboard with its icon.

---

### Method 2: Deploying via Command Line (Terminal)

1. **Clone or copy the application files** to your CasaOS host:
   ```bash
   git clone <repository-url> /DATA/AppData/ncs-downloader
   cd /DATA/AppData/ncs-downloader
   ```

2. **Build and start the container**:
   ```bash
   docker compose up -d --build
   ```

3. **Verify the container is running**:
   ```bash
   docker ps | grep ncs-downloader
   ```

4. **Access the application**:
   Open your browser and navigate to `http://<your-casaos-ip>:8080`.

---

## 🎵 How to Use NCS Downloader

1. Copy a public **Apple Music** URL (Playlist, Album, or Track), e.g.:
   `https://music.apple.com/us/playlist/ncs-releases/pl.u-...`
2. Paste the link into the **Import Apple Music Tracks** input field and click **Extract**.
3. View the extracted track listing. Uncheck any tracks you wish to exclude.
4. (Optional) Adjust the **Search Query Suffix** (default: `NCS audio`).
5. Click **Download Selected**.
6. Track progress in real time under **Download Queue & Status**.
7. Once completed, your high-quality MP3 files will appear directly inside `/DATA/Media/Music` on your CasaOS host!

---

## 🧪 Running Tests Locally

To execute the automated test suite locally:

```bash
pip install -r requirements.txt
PYTHONPATH=. pytest
```
