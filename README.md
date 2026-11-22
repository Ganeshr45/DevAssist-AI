# DevAssist AI

DevAssist AI is a full-stack developer support workspace. It combines an authenticated assistant, persistent conversations, streaming OpenAI-compatible chat, a private document knowledge base with pgvector retrieval, and a constrained tool registry.

## What is implemented

- Email/password registration and login with Argon2id, short-lived JWT access tokens, hashed rotating refresh tokens, role-based member/admin assignment, HttpOnly refresh cookies, and same-origin checks on cookie endpoints.
- Authenticated and owner-scoped conversation history, rename/delete/search, SSE assistant responses, markdown/code rendering, source citations, and provider-backed tool selection.
- PDF, Markdown, TXT, and DOCX ingestion; upload size and parser limits; checksum de-duplication; private per-user documents; chunking; OpenAI-compatible embeddings; pgvector cosine retrieval; re-index and status tracking.
- Redis rate limiting and an ARQ indexing worker; PostgreSQL migrations; optional private S3 storage for uploaded originals (local development stores originals in PostgreSQL).
- Scoped analytics and admin metrics, structured JSON logs, request IDs, Prometheus metrics, Grafana dashboard provisioning, OpenTelemetry traces, and optional Sentry reporting.
- Responsive Next.js UI with light/dark themes, accessible forms, copyable code blocks, component tests, Playwright and axe-core accessibility smoke checks.
- Docker Compose services for API, worker, frontend, pgvector PostgreSQL, Redis, Prometheus, Grafana, and an OpenTelemetry collector. GitHub Actions runs checks/builds and publishes container images to GHCR on pushes to `main`.

## Run locally

1. Copy `.env.example` to `.env`; set a random `JWT_SECRET_KEY` of at least 32 bytes and your `OPENAI_API_KEY`. For an administrator, set `ADMIN_EMAILS` before registering that email.
2. Start Docker Desktop or another Docker Engine.
3. Run `docker compose up --build` from this repository directory.
4. Open the app at http://localhost:3000, API docs at http://localhost:8000/docs, Grafana at http://localhost:3001, and Prometheus at http://localhost:9090.

Database migrations run before the API starts. Document indexing runs in the ARQ worker. Without an AI provider key, chat and embedding jobs return clear configuration errors and documents remain in a failed indexing state until re-indexed after configuration.

## Tests and checks

```powershell
cd apps/api
pip install -e ".[dev]"
ruff check app tests
pytest

cd ../web
npm install
npm run lint
npm test
npm run build
npx playwright install chromium
npm run e2e
```

## Configuration and operations

See [docs/architecture.md](docs/architecture.md), [docs/database.md](docs/database.md), [docs/api.md](docs/api.md), [docs/security.md](docs/security.md), and [docs/deployment.md](docs/deployment.md). `.env` is ignored by git. Never commit provider credentials, AWS credentials, tokens, or private files.

The Compose stack is for development and a single-node demonstration. Production should use managed PostgreSQL with pgvector, managed Redis, private S3, workload IAM roles, TLS, a secret manager, private service networking, and a deployed container runtime. See the deployment guide for sizing, IAM, migrations, backups, and rollout notes.
