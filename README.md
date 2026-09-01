# ThreatIntelX

**Modular Threat Intelligence, IOC Analysis and Threat Correlation Platform**

ThreatIntelX is a self-contained, Dockerized Threat Intelligence Platform (TIP) for collecting,
validating, scoring, correlating, and investigating Indicators of Compromise (IOCs), threat actors,
malware, campaigns, and vulnerabilities. It runs fully populated with safe synthetic demo data out
of the box — no external API keys required — and can be pointed at authorized real feeds later.

This is a defensive intelligence and analysis system. It does not contain or generate offensive
tooling, exploits, malware, or live malicious infrastructure. See [Security Boundary](#security-boundary).

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Docker Setup](#docker-setup)
- [Demo Mode](#demo-mode)
- [Database](#database)
- [API](#api)
- [Authentication](#authentication)
- [Threat Feed Configuration](#threat-feed-configuration)
- [Enrichment Configuration](#enrichment-configuration)
- [STIX / TAXII](#stix--taxii)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [Known Limitations](#known-limitations)
- [Future Enhancements](#future-enhancements)

---

## Overview

ThreatIntelX ingests indicators from pluggable feed adapters, validates and normalizes them,
deduplicates against existing records, runs a provider-independent enrichment pass, computes an
explainable 0–100 threat score, and deterministically correlates related objects (IOCs, threat
actors, malware, campaigns) into a browsable graph. Everything is exposed through a documented
REST API and a dark, SOC-style React dashboard.

## Features

- IOC lifecycle: validation, normalization, deduplication, scoring, correlation
- Support for IPv4, IPv6, Domain, URL, MD5, SHA1, SHA256, Email, CVE, ASN, CIDR
- Explainable threat scoring with a visible factor-by-factor breakdown
- Confidence tracked separately from severity/threat score
- Deterministic correlation engine + interactive threat graph (React Flow)
- Pluggable feed collector architecture with manual and scheduled ingestion
- Provider-independent enrichment that degrades gracefully without API keys
- Threat actor / malware / campaign / vulnerability tracking pages
- JWT authentication with role-based access control (Admin / Analyst / Viewer)
- Full audit logging of security-relevant actions
- Alerting on critical indicators, score threshold crossings, and feed failures
- Celery + Redis background workers and a scheduled-job beat process
- STIX 2.1 export and import; TAXII client architecture
- Demo mode: safe synthetic data populates the platform immediately on first boot
- Health checks, structured JSON logging, rate limiting, automated tests

## Architecture

```text
                         INTERNET / THREAT FEEDS
                                  │
                                  ▼
                        ┌───────────────────┐
                        │ Feed Collectors   │   (pluggable adapters, app/services/feed_collectors.py)
                        └─────────┬─────────┘
                                  ▼
                        ┌───────────────────┐
                        │ Ingestion Engine  │   (app/services/ioc_pipeline.py)
                        └─────────┬─────────┘
                                  ▼
                    ┌─────────────▼─────────────┐
                    │ Validation + Normalization│
                    └─────────────┬─────────────┘
                                  ▼
                        ┌───────────────────┐
                        │ Deduplication     │
                        └─────────┬─────────┘
                                  ▼
                        ┌───────────────────┐
                        │ PostgreSQL        │
                        └─────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
       Enrichment Engine   Scoring Engine     Correlation Engine
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  ▼
                            REST API (FastAPI)
                                  ▼
                       Web Dashboard (React/Vite)
                                  ▼
                              Analyst
```

Background jobs (feed collection, enrichment sweeps, correlation sweeps, cleanup) run on a
Celery worker, scheduled by Celery Beat, both backed by Redis.

## Technology Stack

**Frontend:** React, TypeScript, Vite, Tailwind CSS, Recharts, React Flow, React Router, Axios, lucide-react
**Backend:** Python, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic
**Database:** PostgreSQL 16
**Background processing:** Redis, Celery (worker + beat)
**Auth:** JWT (python-jose), bcrypt password hashing (passlib)
**Deployment:** Docker, Docker Compose, Nginx (production frontend)
**Standards:** STIX 2.1 export/import, TAXII client architecture

## Requirements

Only **Docker** and **Docker Compose** are required on the host machine. You do **not** need to
install Python, Node.js, PostgreSQL, Redis, npm, or pip locally — everything runs in containers.

## Installation

```bash
git clone <repository-url>
cd threatintelx
cp .env.example .env
docker compose up --build
```

Then open the frontend in your browser.

## Configuration

All configuration lives in `.env` (copied from `.env.example`). Nothing is hardcoded in source.
Key variables:

| Variable | Purpose | Default |
|---|---|---|
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Database credentials | `threatintelx` / `threatintelx` / `threatintelx` |
| `JWT_SECRET` | Signs auth tokens — **change before any real deployment** | `change-me-in-production` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Initial admin account, created idempotently on first boot | `admin@threatintelx.local` / `ChangeMe123!` |
| `DEMO_MODE` | Seeds safe synthetic intelligence so the dashboard is populated immediately | `true` |
| `API_KEY_1` / `API_KEY_2` | Optional external enrichment/feed provider keys | empty |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173,http://localhost:8080` |
| `FEED_INTERVAL_MINUTES` | Scheduled feed ingestion cadence | `30` |
| `ENRICHMENT_INTERVAL_MINUTES` | Scheduled enrichment sweep cadence | `60` |
| `CORRELATION_INTERVAL_MINUTES` | Scheduled correlation sweep cadence | `60` |
| `CLEANUP_INTERVAL_HOURS` | Scheduled maintenance cadence | `24` |

The platform runs completely even if `API_KEY_1`/`API_KEY_2` are left blank — enrichment falls
back to internal heuristics and reports `external_status: unavailable`.

## Docker Setup

`docker-compose.yml` defines: `postgres`, `redis`, `backend` (FastAPI API), `worker` (Celery),
`scheduler` (Celery beat), `frontend` (Vite dev server with hot reload). All services share a
Docker network, use health checks, and Postgres/Redis data persists in named volumes.

```bash
docker compose up --build        # start everything
docker compose down               # stop
docker compose down -v            # stop and wipe all data (full reset)
docker compose logs -f backend    # tail backend logs
```

On startup, the `backend` container automatically waits for Postgres, runs Alembic migrations,
and idempotently seeds roles/permissions, the admin account, demo accounts, sources/feeds, and
(if `DEMO_MODE=true`) synthetic demo intelligence. Running this sequence multiple times does not
duplicate data.

## Demo Mode

With `DEMO_MODE=true` (the default), the platform seeds itself with **safe, non-operational**
synthetic intelligence: RFC 5737 documentation IP ranges (`192.0.2.0/24`, `198.51.100.0/24`,
`203.0.113.0/24`), RFC 2606 reserved example domains (`*.example`, `*.invalid`), synthetic hashes,
a demo threat actor, malware family, campaign, and CVEs — all clearly labeled as synthetic. No
live malicious infrastructure is ever used as demo data.

## Database

PostgreSQL with SQLAlchemy models covering: `users`, `roles`, `permissions`, `user_roles`, `iocs`,
`sources`, `feeds`, `feed_runs`, `observations`, `enrichments`, `scores`, `threat_actors`,
`malware`, `campaigns`, `attack_patterns`, `vulnerabilities`, `relationships`, `tags`, `ioc_tags`,
`stix_objects`, `audit_logs`, `alerts`. UUID primary keys, proper foreign keys, unique constraints
(e.g. one IOC per `(type, normalized_value)`), and indexes on hot lookup columns. Migrations run
through Alembic (`backend/alembic/versions/0001_initial_schema.py`).

## API

FastAPI serves a full REST API at `/api/*`, with interactive docs at `/docs` (Swagger) and
`/redoc`. Key routes: `/api/health`, `/api/iocs` (CRUD + search + relationships/enrichment/timeline
sub-resources), `/api/sources`, `/api/feeds` (+ `/run`), `/api/threat-actors`, `/api/malware`,
`/api/campaigns`, `/api/vulnerabilities`, `/api/graph`, `/api/statistics`, `/api/alerts`,
`/api/audit-logs`, `/api/stix/export` and `/api/stix/import`.

## Authentication

JWT bearer tokens issued via `POST /api/auth/login`, verified on every protected route. Passwords
are hashed with bcrypt. The initial admin account is created from `ADMIN_EMAIL`/`ADMIN_PASSWORD`
on first startup — no credentials are ever hardcoded in source. Two additional demo accounts are
seeded for testing RBAC:

| Role | Email | Password |
|---|---|---|
| Admin | value of `ADMIN_EMAIL` | value of `ADMIN_PASSWORD` |
| Analyst | `analyst@threatintelx.local` | `Analyst123!` |
| Viewer | `viewer@threatintelx.local` | `Viewer123!` |

**Change these demo passwords (or disable the demo accounts) before any non-local deployment.**

## Threat Feed Configuration

Feeds are managed at `/feeds` in the UI or via `/api/feeds`. Each feed has a `feed_type` that maps
to a collector function in `backend/app/services/feed_collectors.py` — new sources are added by
registering another entry in the `COLLECTORS` dict, no other code changes needed. The bundled demo
feed generates rotating synthetic indicators; a second feed demonstrates reaching an authorized
public data source (NVD) and falls back to bundled data if unreachable, so ingestion can never
break the platform.

## Enrichment Configuration

Enrichment (`backend/app/services/enrichment.py`) is provider-independent. Without `API_KEY_1`/
`API_KEY_2` set, it still runs internal heuristic enrichment (ASN/geo placeholders, reputation
heuristics, DNS record checks) so the UI is never empty, and marks `external_status: unavailable`
rather than failing.

## STIX / TAXII

STIX 2.1 export (`GET /api/stix/export`) maps IOCs, threat actors, malware, campaigns, and
relationships to STIX objects and bundles them. Import (`POST /api/stix/import`) accepts a STIX
bundle and runs its indicators through the same validation/normalization/dedup pipeline as any
other feed. TAXII client architecture is scaffolded in the feed collector interface; full TAXII
server functionality was intentionally not built to keep scope focused on reliable client-side
ingestion (see [Known Limitations](#known-limitations)).

## Testing

```bash
docker compose exec backend pytest -v
```

Backend tests (`backend/tests/`) cover IOC validation, normalization, scoring bounds, JWT auth,
RBAC enforcement (viewer blocked from write/audit endpoints), IOC CRUD, and deduplication, using
an in-memory SQLite database with the same SQLAlchemy models as production.

## Troubleshooting

- **Frontend can't reach the API**: confirm `backend` is healthy (`docker compose ps`) and that
  `CORS_ORIGINS` in `.env` includes the frontend's origin.
- **Backend keeps restarting**: check `docker compose logs backend` — it waits for Postgres to
  become available before running migrations; a persistently unhealthy Postgres container is the
  most common cause.
- **Port already in use**: change the host-side port mappings in `docker-compose.yml`.
- **Full reset**: `docker compose down -v && docker compose up --build` wipes all data and
  re-seeds from scratch.

## Security

Password hashing (bcrypt), JWT auth, RBAC on every mutating/sensitive endpoint, parameterized
queries via SQLAlchemy (no string-built SQL), input validation via Pydantic, CORS restricted to
configured origins, a per-IP rate-limiting middleware, no secrets in source or Git (all via env),
audit logging that explicitly never records passwords/secrets/API keys, and a dedicated production
Compose overlay that disables debug mode and removes host port exposure for the database and Redis.

## Project Structure

```text
threatintelx/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers
│   │   ├── core/            # config, security, logging, rate limiting
│   │   ├── db/               # session, startup migration/seed runner
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/         # validation, normalization, scoring, correlation,
│   │   │                     # enrichment, feed collectors, STIX, seed, audit
│   │   ├── workers/          # Celery app + scheduled tasks
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/            # one file per route
│   │   ├── components/       # shared UI primitives
│   │   ├── layouts/           # app shell / sidebar
│   │   ├── services/          # axios client
│   │   ├── hooks/             # auth context
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
├── docker/                    # production nginx config + prod frontend Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

## Deployment

For a Linux VPS: install Docker + Docker Compose, clone the repo, set strong values for
`JWT_SECRET`/`POSTGRES_PASSWORD`/`ADMIN_PASSWORD` in `.env`, then run:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

The production overlay serves the frontend as a static Nginx build, disables backend debug mode,
and removes host-level exposure of Postgres/Redis. Put a TLS-terminating reverse proxy (Nginx,
Caddy, or a managed load balancer) in front of the `frontend` container for HTTPS. Back up the
`postgres_data` named volume regularly (`docker compose exec postgres pg_dump ...`). Application
logs are structured JSON on stdout — collect them with your platform's standard log driver.

## Known Limitations

Given the scope of this platform, the following were deliberately simplified rather than fully
built out, to keep what's here genuinely working end-to-end:

- **TAXII**: client-side architecture and STIX bundle handling exist; a full TAXII 2.1 server
  (collections, discovery endpoints) was not implemented.
- **Enrichment**: internal heuristic enrichment always runs; live third-party enrichment providers
  (e.g. AbuseIPDB, VirusTotal, Shodan) are not wired to specific SDKs — `API_KEY_1`/`API_KEY_2`
  are reserved slots you can wire up in `app/services/enrichment.py`.
- **Feed collectors**: one synthetic demo feed and one real-but-safe reachability check against
  NVD are implemented as reference adapters; production feeds should be added following the same
  pattern in `app/services/feed_collectors.py`.
- **Rate limiting** is in-memory per API container; for multi-instance production deployments it
  should be backed by Redis instead.
- This has been validated by static compilation and logical review, not by running `docker compose
  up` against a live daemon in the environment this was built in (no container runtime available
  there). Please run the automated test suite and exercise the acceptance flow below on first use.

## Future Enhancements

- Live third-party enrichment integrations (VirusTotal, AbuseIPDB, Shodan, GreyNoise)
- Full TAXII 2.1 server for outbound collection sharing
- SSO / SAML / OIDC login options
- MITRE ATT&CK Navigator-style layer export
- Bulk CSV/STIX import UI with progress tracking

---

### Suggested first run checklist

```bash
git clone <repository-url>
cd threatintelx
cp .env.example .env
docker compose up --build

# in another terminal, once containers are healthy:
docker compose exec backend pytest -v
```

Then open the frontend, sign in with the admin credentials from `.env`, and confirm the dashboard
is populated with demo intelligence.
