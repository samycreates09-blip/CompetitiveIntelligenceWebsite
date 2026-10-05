# Boost Competitive Intelligence

An AI-native competitive intelligence application for exploring telecom competitors, service plans, devices, promotions, detected changes, and grounded AI answers.

## Stack

- React 18, TypeScript, Vite, and TanStack Query
- FastAPI, SQLAlchemy Core, and Pydantic
- PostgreSQL 16 with pgvector
- Gemini for briefings, embeddings, RAG, and bounded tool-calling chat

## Hosted path

The production build is exposed through the Samy Creates gateway at:

`http://127.0.0.1:8080/competitive-intelligence/`

The application backend listens locally on `127.0.0.1:8002`. Its private PostgreSQL cluster listens on `127.0.0.1:5433`.

## Local setup

Install PostgreSQL and pgvector:

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-16-pgvector
```

Create the Python environment and frontend build:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci && cd ..
./scripts/build_frontend.sh
```

Copy `.env.example` to `.env` or place a private `backend/.env` file with a valid `GEMINI_API_KEY` to enable AI features. Environment files are ignored by Git.

The database cluster, schema, and synthetic seed data are initialized automatically by the startup scripts.

## Run directly

In separate terminals:

```bash
./scripts/run_database.sh
./scripts/run_backend.sh
```

## Test

```bash
cd backend
../.venv/bin/pytest
```

The repository includes additional architecture and product documentation in `docs/`.
