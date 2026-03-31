# 🎬 Cinema Project API

A high-performance FastAPI application for managing cinema operations, featuring asynchronous database transactions and background email notifications.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
poetry install
````

### 2. Spin up Infrastructure (Docker)
This project uses Docker to manage external services like the database and mail server.
```bash
docker-compose up -d
````

### 3. Apply migrations
```bash
alembic upgrade head
```

### 4. Run uvicorn server
```bash
uvicorn src.main:app
```

## 📡 Essential Endpoints
API Docs (Swagger): http://127.0.0.1:8000/docs

System Health Check: http://127.0.0.1:8000/health/

Mailhog Interface: http://127.0.0.1:8025 (Check here for activation emails)
