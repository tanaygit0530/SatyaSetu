# SachCheck Backend Foundation

> **"Forward it. Know if it's true. In your language, with proof."**

This is the backend foundation for SachCheck, built with **Python 3.13**, **FastAPI**, and **Pydantic**.

---

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory, CORS, exception handlers, lifespan
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/                 # Endpoint routers
│   │   │   ├── __init__.py         # Consolidated api_router
│   │   │   └── health.py           # GET /api/v1/health
│   │   └── dependencies.py         # Injected route dependencies (settings, logger, security)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic BaseSettings environment configuration
│   │   ├── logging.py              # Structured console logging
│   │   ├── exceptions.py           # SachCheckException hierarchy
│   │   └── security.py             # Security utilities & API key verifier
│   │
│   ├── schemas/                    # Pydantic request & response schemas
│   │   ├── __init__.py
│   │   └── health.py               # HealthResponse model
│   │
│   ├── models/                     # Database/ORM models (reserved for future persistence)
│   │   └── __init__.py
│   │
│   ├── repositories/               # Data access layers
│   │   └── __init__.py
│   │
│   ├── services/                   # Business logic services
│   │   └── __init__.py
│   │
│   ├── workers/                    # Background task workers
│   │   └── __init__.py
│   │
│   └── utils/                      # Helper utilities
│       └── __init__.py
│
├── tests/
│   ├── __init__.py
│   └── test_health.py              # Health endpoint and CORS tests
├── scripts/                        # Utility scripts
├── .env.example                    # Environment template
├── pytest.ini                      # Pytest runner configuration
├── requirements.txt                # Production & test dependencies
└── README.md
```

---

## Foundation Features Implemented

1. **API Version Prefix:**
   - Routes mounted under `/api/v1`.
2. **Health Check Endpoint:**
   - `GET /api/v1/health`
   - Response:
     ```json
     {
       "status": "ok",
       "service": "sachcheck-backend",
       "version": "0.1.0"
     }
     ```
3. **CORS Configuration:**
   - Configured for `http://localhost:3000` and `http://127.0.0.1:3000`.
4. **Structured Logging:**
   - Standardized timestamps, level, function, and file tracking via `app/core/logging.py`.
5. **Centralized Environment Configuration:**
   - Typed settings using `pydantic-settings` via `app/core/config.py`.
6. **Exception Handling:**
   - Global exception handlers for `SachCheckException` and unexpected 500 errors with structured JSON payloads.

---

## Setup & Running Instructions

### 1. Create & Activate Virtual Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

### 3. Start the FastAPI Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server will run at:
👉 **http://localhost:8000**  
Interactive API Docs (Swagger UI):  
👉 **http://localhost:8000/docs**

### 4. Test the Health Endpoint
```bash
curl -s http://localhost:8000/api/v1/health
```
Output:
```json
{"status":"ok","service":"sachcheck-backend","version":"0.1.0"}
```

### 5. Run the Test Suite
```bash
pytest -v
```
