# Entropy

AI-powered application security platform. Register a domain, prove ownership,
run scanners against it, and get normalized findings with an AI-generated
summary.

## Repository layout

| Path        | What it is                                                            |
|-------------|-----------------------------------------------------------------------|
| `server/`   | FastAPI backend, scanner engines, Celery workers (the working system) |
| `client/`   | Next.js dashboard — placeholder, not yet implemented                  |
| `security/` | Security tooling / scanner assets — placeholder                       |

## What works today

- **Auth & multi-tenancy** — register/login (JWT + refresh, Redis token
  revocation), organizations, projects, org-scoped access control.
- **Domain ownership verification** — DNS-TXT or HTTP-file challenge; scans are
  hard-gated on a verified domain.
- **Quick-scan** — `POST /api/v1/quick-scan` auto-provisions
  workspace/project/domain and starts a scan from a single request.
- **Scanner engines** (auto-registered, orchestrated concurrently):
  - `ssl_tls` — stdlib TLS check: expired/expiring certs, hostname mismatch,
    self-signed, deprecated protocols, weak ciphers.
  - `urlscan` — urlscan.io submit+poll; malicious verdict, missing security
    headers, detected tech, TLS summary, screenshot, redirect chains. Runs as a
    progressive background task so it never blocks job completion.
- **AI summaries** — OpenRouter-backed natural-language scan summary with a
  deterministic fallback when unavailable/rate-limited.
- **Persistence** — Supabase (hosted Postgres) via SQLAlchemy + Alembic; Redis
  for Celery and token blacklisting.

## Not yet built

Next.js dashboard, VS Code extension, and additional engines
(Nuclei / Katana / TruffleHog / subfinder / httpx / naabu).

## Running the backend

See [`server/`](server/) — it holds the app, `.env.example`, Dockerfile, and
Alembic migrations. In short: bring up Redis, point `DATABASE_URL` at Postgres,
apply migrations (`alembic upgrade head`), then run the API (`uvicorn
appsec.main:app`) and a worker (`celery -A appsec.infrastructure.celery_app
worker`). `docker-compose.yml` at the repo root wires Redis + API + worker + beat.

## Tests

```bash
cd server
pytest        # 21 tests: auth/quick-scan integration + scanner engine units
```
