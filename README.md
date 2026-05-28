# BreatheESG Technical Assessment

BreatheESG is a full-stack ESG ingestion and audit demo. It combines a Django REST backend, a React + Vite frontend, and PostgreSQL storage to ingest raw ESG activity, normalize it into emissions records, and support analyst review actions such as approve, flag, lock, and edit.

## What It Does

The platform models three ingestion sources:

* SAP fuel and procurement exports
* Utility electricity billing data
* Navan corporate travel records

Each record is stored as a raw payload, converted into a normalized emissions row, and tracked with issues and audit trail events. The frontend provides a review queue for inspecting rows and triggering workflow actions.

## Tech Stack

* Backend: Django, Django REST Framework
* Database: PostgreSQL
* Frontend: React, Vite
* API client: Fetch-based wrapper in the frontend

## Repository Structure

* `breathe_backend/` - Django project, ingest app, and API endpoints
* `breathe_frontend/` - React review UI and API client
* `docker-compose.yml` - Local PostgreSQL service
* `DECISIONS.md`, `MODEL.md`, `SOURCES.md`, `TRADEOFFS.md` - design and domain notes

## Main Features

* Ingest SAP, Utility, and Navan payloads through JSON API endpoints
* Normalize records into `kgCO2e` emissions values
* Flag suspicious data and create issue records
* Approve, edit, flag, and lock normalized rows
* Record audit events for analyst actions
* Display a dashboard of total emissions and queue status in the frontend

## API Overview

All backend routes are served under `/api/`.

* `GET /api/health/` - basic database health check
* `POST /api/ingest/sap/` - ingest SAP fuel or procurement records
* `POST /api/ingest/utility/` - ingest utility electricity records
* `POST /api/ingest/navan/` - ingest Navan travel records
* `GET /api/rows/normalized/` - list normalized rows for the active tenant
* `POST /api/rows/normalized/<uuid>/approve/` - approve a row
* `POST /api/rows/normalized/<uuid>/flag/` - flag a row
* `POST /api/rows/normalized/<uuid>/lock/` - lock a row as audited
* `PATCH /api/rows/normalized/<uuid>/` - edit raw value and unit

Tenant scoping is controlled by the `X-Tenant-ID` request header. If the header is omitted, the backend falls back to a default tenant.

## Local Setup

### Prerequisites

* Python 3.11 or newer
* Node.js 20 or newer
* Docker Desktop or another PostgreSQL 16-compatible server

### 1. Start PostgreSQL

Use the included Docker Compose file from the repository root:

```bash
docker compose up -d db
```

This starts PostgreSQL on port `5433` with the default database name `breathe_esg` and credentials `postgres` / `postgres`.

### 2. Run the Django backend

```bash
cd breathe_backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The backend uses these common environment variables:

* `DATABASE_URL` - PostgreSQL connection string
* `SECRET_KEY` - Django secret key
* `DEBUG` - enable or disable debug mode
* `ALLOWED_HOSTS` - comma-separated allowed hosts

If `DATABASE_URL` is not set, the project defaults to a local PostgreSQL database at `127.0.0.1:5433`.

### 3. Run the React frontend

```bash
cd breathe_frontend
npm install
npm run dev
```

The frontend points to the deployed backend by default through `VITE_API_URL` in `src/api.js`. To run against a local backend, set your own API base URL in a `.env` file:

```bash
VITE_API_URL=http://127.0.0.1:8000/api
```

## Testing

Run backend tests from the Django project directory:

```bash
cd breathe_backend
python manage.py test
```

Run frontend linting from the React project directory:

```bash
cd breathe_frontend
npm run lint
```

## Data Flow

1. A payload is posted to one of the ingestion endpoints.
2. The backend stores the original payload as a raw row.
3. The matching pipeline normalizes the activity into emissions data.
4. Issues are created when the payload looks invalid or suspicious.
5. Analysts review rows in the frontend and may approve, flag, edit, or lock them.
6. Audit events are written for each workflow action.

## Notes

* The project is configured for cross-origin requests during development.
* The backend and frontend are decoupled, so each can be run independently.
* The frontend is currently seeded with a mock ingest sandbox to make the workflow easy to demonstrate.
