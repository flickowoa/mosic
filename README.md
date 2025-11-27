# Mosic

**Minimalist Async Music Streamer**

Mosic is a lightweight, high-performance backend for managing and streaming audio. Built on modern Python async foundations, it's designed to handle music uploads, metadata extraction, and streaming with minimal overhead.

It doesn't just store files; it understands them. Upload an audio file, and Mosic extracts the duration and tags automatically. It tracks play counts and exposes Prometheus metrics out of the box, making it ready for production monitoring.

## Features

- [x] **List Clips (`GET /play`):** Returns available sound clips with metadata (id, title, description, duration, audio_url).
- [x] **Stream Clip (`GET /play/{id}/stream`):** Streams audio content and increments play counts in the database.
- [x] **Clip Stats (`GET /play/{id}/stats`):** Returns play count and metadata for specific clips.
- [x] **Database:** PostgreSQL used for storing song metadata and play counts.
- [x] **Monitoring:** Prometheus metrics exposed via `starlette_exporter`. Grafana dashboard ready.
- [x] **Add Clip (`POST /play`):** Endpoint to add new clip entries (supports both metadata-only and file upload).
- [x] **CI/CD:** GitHub Actions workflow configured for linting and testing.
- [x] **Security:** API endpoints protected via API Key authentication.

## Tech Stack

*   **Core:** Python 3.13+, FastAPI
*   **Data:** SQLAlchemy (Async), PostgreSQL, Alembic
*   **Media:** Mutagen (Metadata extraction)
*   **Ops:** Starlette Exporter (Prometheus metrics)
*   **Package Manager:** Poetry

## Quick Start

### Prerequisites

*   Python 3.13 or higher
*   Poetry
*   PostgreSQL instance

### Installation

1.  **Clone and Install:**
    ```bash
    git clone https://github.com/flickowoa/mosic.git
    cd mosic
    poetry install
    ```

2.  **Environment Setup:**
    Create a `.env` file in the root directory. Configuration uses the `MOSIC_` prefix.
    ```ini
    MOSIC_DB_HOST=localhost
    MOSIC_DB_PORT=5432
    MOSIC_DB_NAME=mosic
    MOSIC_DB_USER=postgres
    MOSIC_DB_PASSWORD=password
    
    # Or override the full URL directly
    # MOSIC_DATABASE_URL_OVERRIDE=postgresql+asyncpg://user:pass@localhost/mosic_db
    
    MOSIC_API_KEY=your_super_secret_key
    MOSIC_MEDIA_ROOT=./media
    ```

3.  **Database Migrations:**
    Initialize the database schema:
    ```bash
    poetry run alembic upgrade head
    ```

4.  **Run the Server:**
    ```bash
    poetry run fastapi dev app/main.py
    ```
    The API will be available at `http://localhost:8000`.

## Usage

### Upload a Song
Send a `POST` request to `/play/upload` with an audio file. Mosic supports standard audio formats.

```bash
curl -X POST "http://localhost:8000/play/upload" \
  -H "X-API-Key: your_api_key" \
  -F "file=@/path/to/song.mp3"
```

### Stream Audio
Stream a song by its ID. This endpoint supports range requests for seeking.

```bash
# GET /play/{song_id}/stream
http://localhost:8000/play/123e4567-e89b-12d3-a456-426614174000/stream
```

### Check Stats
See how many times a track has been played.

```bash
# GET /play/{song_id}/stats
{
  "song_id": "123e4567-e89b-12d3-a456-426614174000",
  "play_count": 42
}
```

## Observability

Metrics are exposed at `/metrics` for Prometheus scraping.
*   `mosic_request_latency_seconds`: Histogram of request processing time.
*   `mosic_total_api_requests_total`: Counter of total API requests.

### Grafana
![grafana](image.png)


## Development

**Running Tests:**
```bash
poetry run pytest
```

**Linting:**
```bash
poetry run ruff check .
```