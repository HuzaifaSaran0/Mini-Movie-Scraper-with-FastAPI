# 🎬 Movie Scraper & REST API

A backend for scraping, storing, and serving movie data. Built with **FastAPI**, **SQLModel**, and **PostgreSQL**, with dependency management powered by **uv**.

***

## 🚀 Quickstart (Under 5 Minutes)

### 1. Environment Setup

```bash
cp .env.example .env
```

Edit `.env` and set `SECRET_KEY` and `ADMIN_PASSWORD` to your own values. Default admin username is `admin` (see `.env.example`).

**`DATABASE_URL` host depends on where you run commands:**

| Where you run commands | `DATABASE_URL` host |
|------------------------|---------------------|
| Inside Docker (`web` container) | `db` |
| On your machine (local `uv` / `alembic` / `scrape.py`) | `localhost` |

When using Docker Compose with the default `.env.example`, keep `@db:` — the app and scripts running inside the `web` container resolve it automatically. For local `uv` commands against a Dockerized Postgres, change `@db:` to `@localhost:` (or the scripts will rewrite it for you when not inside Docker).

### Option A — Docker Compose (recommended)

Start PostgreSQL and the API:

```bash
docker compose up -d --build
```

Apply migrations and run the scraper inside the `web` container:

```bash
docker compose exec web uv run alembic upgrade head
docker compose exec web uv run scrape.py
```

### Option B — Local `uv` (API + DB in Docker)

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

> For Option B, ensure `DATABASE_URL` in `.env` uses `@localhost:` (or keep `@db:` — local scripts auto-rewrite it when run outside Docker).

### 2. Test the API

Open the interactive docs:

👉 **http://localhost:8000/docs**

#### Authenticating

`POST /auth/login` expects **OAuth2 form data** (`application/x-www-form-urlencoded`), not JSON:

| Field      | Value                          |
|------------|--------------------------------|
| `username` | value of `ADMIN_USERNAME`      |
| `password` | value of `ADMIN_PASSWORD`      |

In Swagger UI, click **Authorize**, enter the credentials, then call the protected `/movies` endpoints.

Example with `curl`:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=change-me" | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/movies
```

***

## 🛠 Tech Stack

| Layer            | Technology                              |
|------------------|-----------------------------------------|
| Web Framework    | FastAPI                                 |
| Database ORM     | SQLModel (SQLAlchemy + Pydantic)        |
| Migrations       | Alembic                                 |
| Database         | PostgreSQL                              |
| Security         | `bcrypt` + `python-jose` (JWT)          |
| Scraping         | `httpx` + BeautifulSoup4                |
| Package Manager  | `uv`                                    |

***

## 📡 API Endpoints

### Authentication

| Method | Endpoint       | Auth Required | Description                                         |
|--------|----------------|---------------|-----------------------------------------------------|
| POST   | `/auth/login`  | No            | Validates credentials and returns a JWT bearer token |

### Movies

> All movie endpoints require a valid **JWT Bearer Token**.

| Method | Endpoint         | Description                                                                 |
|--------|------------------|-----------------------------------------------------------------------------|
| GET    | `/movies`        | List all movies. Supports pagination via `?page=1&limit=10`                  |
| GET    | `/movies/{id}`   | Retrieve a single movie by its primary key ID                               |
| PATCH  | `/movies/{id}`   | Update a movie's title or genres (partial updates supported)                |
| DELETE | `/movies/{id}`   | Delete a specific movie from the database                                   |

### System

| Method | Endpoint   | Description                                                    |
|--------|------------|----------------------------------------------------------------|
| GET    | `/health`  | Returns the API status and ISO timestamp of last scraper run     |

***

## 🏗 Architectural Decisions

### Required environment variables

The app exits on startup if `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, or `DATABASE_URL` are missing. No credential fallbacks are baked into the code.

### Idempotent data ingestion

The scraper enforces unique constraints at the database level (`source_url`), ensuring **zero duplicates** regardless of how many times `uv run scrape.py` is executed.

### Decoupled scraper

Scraping runs as an isolated script (`scrape.py`) so it does not block the async FastAPI event loop.
