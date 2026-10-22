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

Follow these steps to deploy NCS Downloader on your CasaOS server.

> ⚠️ **Note regarding "No such image" error:**
> CasaOS imports attempt to pull images directly from Docker Hub unless the image is already built locally on the host system. **Step 1 below builds the image locally first to prevent this issue.**

---

### Step 1: Clone the Repository & Build the Docker Image on CasaOS Host

Open terminal / SSH into your CasaOS (Ubuntu 26) server and run:

```bash
# 1. Create directory and clone repository
sudo mkdir -p /DATA/AppData/ncs-downloader
cd /DATA/AppData/ncs-downloader

# Copy/clone the project files into this folder

# 2. Ensure target music directory exists on host
sudo mkdir -p /DATA/Media/Music
sudo chmod -R 777 /DATA/Media/Music

# 3. Build the Docker image locally
docker build -t ncs-downloader:latest .
```

---

### Step 2: Option A — Deploying via Command Line (Quickest)

Once the image is built in Step 1, simply start the container:

```bash
docker compose up -d
```

Check status:
```bash
docker ps | grep ncs-downloader
```

Open your web browser and go to `http://<your-casaos-ip>:8080`.

---

### Step 2: Option B — Deploying via CasaOS Dashboard (Custom App)

If you prefer having the **NCS Downloader tile on your CasaOS Dashboard**:

1. Log in to **CasaOS Web UI** (`http://<your-server-ip>`).
2. Click the **`+` (Install Custom App)** button on the top left of the CasaOS dashboard.
3. Click **`Import`** in the top right corner.
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
7. CasaOS will link the app tile on your main dashboard!

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
