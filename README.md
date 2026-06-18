# 🎬 Movie Scraper & REST API

A scalable, containerized backend solution for scraping, storing, and serving movie data. Built with **FastAPI**, **SQLModel**, and **PostgreSQL**, with dependency management powered by **uv**.

***

## 🚀 Quickstart (Under 5 Minutes)

This project is fully containerized to ensure a seamless setup process.

### 1. Environment Setup

Clone the repository and set up your local environment variables:

```bash
cp .env.example .env
```

### 2. Boot the Infrastructure

Start the PostgreSQL database and FastAPI backend simultaneously:

```bash
docker compose up -d --build
```

> ⏳ Wait a few seconds for the database to fully initialize.

### 3. Apply Database Migrations

Create the database tables and apply the schema using Alembic:

```bash
docker compose exec web uv run alembic upgrade head
```

### 4. Populate the Database (The Scraper)

Run the standalone scraper to fetch movie data and populate the database safely. Running this multiple times will inherently skip duplicates based on database constraints:

```bash
docker compose exec web uv run scrape.py
```

### 5. Test the API

The API is now live! Visit the interactive Swagger UI to test all endpoints seamlessly:

👉 **http://localhost:8000/docs**

**Admin Login Credentials:**

| Field    | Value    |
|----------|----------|
| Username | `admin`  |
| Password | `secret` |

***

## 🛠 Tech Stack & Architecture

| Layer            | Technology                              |
|------------------|-----------------------------------------|
| Web Framework    | FastAPI                                 |
| Database ORM     | SQLModel (SQLAlchemy + Pydantic)        |
| Migrations       | Alembic                                 |
| Database         | PostgreSQL                              |
| Security         | Native `bcrypt` + `python-jose` (JWT)  |
| Scraping         | `httpx` + BeautifulSoup4               |
| Package Manager  | `uv` (Lightning-fast, Rust-based)      |

***

## 📡 API Endpoints

### Authentication

| Method | Endpoint       | Auth Required | Description                                         |
|--------|----------------|---------------|-----------------------------------------------------|
| POST   | `/auth/login`  | ❌ No          | Validates credentials and returns a JWT bearer token |

### Movies

> All movie endpoints require a valid **JWT Bearer Token**.

| Method | Endpoint         | Description                                                                 |
|--------|------------------|-----------------------------------------------------------------------------|
| GET    | `/movies`        | List all movies. Supports pagination via `?page=1&limit=10`                |
| GET    | `/movies/{id}`   | Retrieve a single movie by its primary key ID                              |
| PATCH  | `/movies/{id}`   | Update a movie's title or genres (partial updates supported)               |
| DELETE | `/movies/{id}`   | Delete a specific movie from the database                                  |

### System

| Method | Endpoint   | Description                                                    |
|--------|------------|----------------------------------------------------------------|
| GET    | `/health`  | Returns the API status and ISO timestamp of last scraper run  |

***

## 🏗 Architectural Decisions

### Native Bcrypt Implementation

Bypassed the deprecated `passlib` dependency in favor of pure `bcrypt`. This prevents the notorious 72-byte limit crashes and aligns with modern security standards.

### Decoupled Scraper

The scraping logic runs as an isolated script (`scrape.py`) to prevent blocking the asynchronous FastAPI event loop, mimicking production-ready batch-job architecture.

### Idempotent Data Ingestion

The scraper enforces unique constraints at the database level (`source_url`), ensuring **zero duplicates** regardless of how many times the script is executed.

### Dual Environment Strategy

Leveraged `uv` to manage an isolated virtual environment completely within the Docker container, guaranteeing exact parity across different operating systems while keeping builds incredibly fast.