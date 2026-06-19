# Mini Movie Scraper & FastAPI Backend

A containerized backend system for scraping, storing, and serving movie data. Built with **FastAPI**, **SQLModel**, **PostgreSQL**, and dependency management powered by **uv**.

***

## Installation & Setup


### 1. Clone the Repository


```bash
git clone https://github.com/HuzaifaSaran0/Mini-Movie-Scraper-with-FastAPI.git
cd Mini-Movie-Scraper-with-FastAPI
```


### 2. Configure Environment Variables


You must create a `.env` file in the root directory before running the application.


```bash
# On Unix/macOS:
cp .env.example .env


# On Windows (or manually):
# Create a new file named `.env` and copy the contents of `.env.example` into it.
```

> **Note on Database Routing:** Keep `DATABASE_URL` exactly as it is in the example (`@db:`). The application features environment-aware routing - if you run local `uv` commands on your machine instead of inside Docker, the backend will automatically reroute the connection to `@localhost:` for you.


> Open your new `.env` file and set a secure `SECRET_KEY` and `ADMIN_PASSWORD`.
> Tip: You can quickly generate a cryptographic secret key by running `python3 -c "import secrets; print(secrets.token_hex(32))"` in your terminal.


***

## 💻 Running the Application

### Option A - Docker Compose (Recommended)

Start PostgreSQL and the API, then run migrations and the scraper inside the container:

```bash
docker compose up -d --build
docker compose exec web uv run alembic upgrade head
docker compose exec web uv run scrape.py
```

### Option B - Local `uv` (Hybrid: API + DB in Docker)

Start only the database:

```bash
docker compose up -d db
```

Install dependencies, migrate, scrape, and start the API on your machine:

```bash
uv sync
uv run alembic upgrade head
uv run scrape.py
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

***

## API Endpoints

Once running, access the interactive Swagger documentation at **http://localhost:8000/docs**.

### Authentication

| Method | Endpoint      | Auth Required | Description                                          |
|--------|---------------|---------------|------------------------------------------------------|
| POST   | `/auth/login` | No            | Validates credentials and returns a JWT bearer token |

> `/auth/login` expects **OAuth2 form data** (`application/x-www-form-urlencoded`), not JSON.

In Swagger UI, click **Authorize**, enter your credentials, then call the protected `/movies` endpoints.

Example with `curl`:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=change-me" | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/movies
```

### Movies

> All movie endpoints require a valid **JWT Bearer Token**.

| Method | Endpoint       | Description                                                  |
|--------|----------------|--------------------------------------------------------------|
| GET    | `/movies`      | List all movies. Supports pagination via `?page=1&limit=10`  |
| GET    | `/movies/{id}` | Retrieve a single movie by its primary key ID                |
| PATCH  | `/movies/{id}` | Update a movie's title or genres (partial updates supported) |
| DELETE | `/movies/{id}` | Delete a specific movie from the database                    |

### System

| Method | Endpoint  | Description                                                   |
|--------|-----------|---------------------------------------------------------------|
| GET    | `/health` | Returns the API status and ISO timestamp of last scraper run  |

***

## Tech Stack

| Layer           | Technology                         |
|-----------------|------------------------------------|
| Web Framework   | FastAPI                            |
| Database ORM    | SQLModel (SQLAlchemy + Pydantic)   |
| Migrations      | Alembic                            |
| Database        | PostgreSQL                         |
| Security        | `bcrypt` + `python-jose` (JWT)     |
| Scraping        | `httpx` + BeautifulSoup4           |
| Package Manager | `uv`                               |

***

## Architectural Decisions

### Strict Credential Validation

The app exits immediately on startup if `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, or `DATABASE_URL` are missing. No credential fallbacks are baked into the code, completely eliminating the security risk of hardcoded defaults.

### Polite Detail Crawler

The scraper extracts the top 50 films from Wikipedia's list and programmatically crawls individual detail pages to accurately parse high-res images and genres. It intentionally incorporates a **1-second delay** between requests to respect server policies and prevent IP bans.

> In a production environment, this synchronous pipeline would be offloaded to a **Celery background worker**.

### Idempotent Data Ingestion

The scraper enforces unique constraints at the database level (`source_url`), ensuring **zero duplicates** regardless of how many times `uv run scrape.py` is executed.

### Environment-Aware Routing

The `config.py` module detects the presence of `/.dockerenv`. This allows the exact same `.env` file and scripts to execute flawlessly whether triggered inside the Docker network or directly on the host machine.

### Decoupled Scraper

Scraping runs as an isolated script (`scrape.py`) so it never blocks the async FastAPI event loop, mimicking production-ready batch-job architecture.