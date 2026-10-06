# ChemRAG 🧪

**ChemRAG** is a chemistry-domain Retrieval-Augmented Generation (RAG) system that ingests scientific PDFs, recognizes chemical structures (SMILES, InChI, IUPAC names), normalizes chemical entities, and answers research questions with full citation provenance.

---

## Architecture Overview

```
chemrag/
├── backend/          # Python FastAPI backend (core logic, AI pipeline)
│   └── app/
│       ├── api/          # REST + WebSocket endpoints (v1)
│       ├── core/         # Config, logging, lifespan, security
│       ├── db/           # Database session, migrations (Alembic)
│       ├── models/       # SQLAlchemy ORM models
│       ├── schemas/      # Pydantic request/response schemas
│       ├── repositories/ # Data access layer (CRUD abstraction)
│       ├── services/     # Business logic orchestration
│       ├── ingestion/    # Document upload, queue, pipeline orchestration
│       ├── parsing/      # Scientific PDF parsing (GROBID, PyMuPDF)
│       ├── chemistry/    # Structure recognition (DECIMER, MolScribe), NER, normalization
│       ├── embeddings/   # Embedding models (chemical-aware)
│       ├── retrieval/    # Vector + BM25 hybrid retrieval
│       ├── reranking/    # Cross-encoder reranking
│       ├── agents/       # LangGraph multi-agent orchestration
│       ├── safety/       # Chemical safety & compliance checks
│       ├── evaluation/   # RAG evaluation metrics (RAGAS, custom)
│       └── observability/# Tracing (OpenTelemetry), metrics, logging
│
├── frontend/         # React + TypeScript + Vite SPA
│   └── src/
│       ├── components/   # Shared UI components
│       ├── pages/        # Route-level page components
│       ├── features/     # Feature-sliced domain modules
│       ├── hooks/        # Custom React hooks
│       ├── services/     # API client, WebSocket services
│       ├── stores/       # Zustand state stores
│       ├── types/        # TypeScript type definitions
│       └── utils/        # Utility functions
│
├── infra/            # Infrastructure as code
│   ├── docker/       # Dockerfiles, compose overrides
│   └── nginx/        # Nginx reverse proxy config
│
├── scripts/          # Dev scripts (seed, migrate, lint, etc.)
├── docs/             # Architecture docs, ADRs, API specs
└── tests/            # Test suite
    ├── unit/         # Unit tests (pytest)
    ├── integration/  # Integration tests (Docker-backed)
    └── e2e/          # End-to-end tests (Playwright)
```

---

## Quick Start

### Prerequisites
- Docker ≥ 24 & Docker Compose v2
- Python ≥ 3.11 (for local dev without Docker)
- Node.js ≥ 20

### Start all services

```bash
cp .env.example .env          # fill in your API keys
docker compose up -d           # starts postgres, redis, grobid, backend, frontend
docker compose ps              # verify all services are healthy
```

### Backend only (local)

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Frontend only (local)

```bash
cd frontend
npm install
npm run dev
```

---

## Services & Ports

| Service    | Port  | Description                        |
|------------|-------|------------------------------------|
| Backend    | 8000  | FastAPI REST + WS API              |
| Frontend   | 5173  | React Vite dev server              |
| PostgreSQL | 5432  | Primary DB with pgvector extension |
| Redis      | 6379  | Cache, task queue (Celery)         |
| GROBID     | 8070  | Scientific PDF structure parser    |

---

## Environment Variables

Copy `.env.example` → `.env` and configure:

```bash
cp .env.example .env
```

See `.env.example` for all required/optional variables.

---

## Testing

```bash
# Backend tests
cd backend && pytest tests/ -v

# Frontend tests
cd frontend && npm test

# Integration (requires Docker)
pytest tests/integration/ -v --docker
```

---

## Documentation

- [Architecture Decision Records](docs/adr/)
- [API Reference](docs/api.md)
- [Chemical Pipeline](docs/chemistry_pipeline.md)
- [Deployment Guide](docs/deployment.md)

---

## License

MIT — see [LICENSE](LICENSE)
