# Infra

Owner: M1 (Redis/simulator setup) / M6 (final integration, Docker Compose, CI)

## Status: Docker Compose written (23 Aug 2026) — not yet run

`docker-compose.yml` lives at the **repo root** (not in this folder) so `docker compose up` works naturally from the project root. This folder is for anything else infra-related later (CI configs, deployment notes).

### What's in the compose file
- `timescaledb` — Postgres + TimescaleDB extension, with a persistent named volume
- `redis` — for M1/M2 stream publishing once those services exist
- `migrate` — one-shot job that runs `prisma migrate deploy`, then exits; `control-api` waits for it to succeed before starting
- `control-api` — built from `services/control-api/Dockerfile` (multi-stage: full devDependencies to build, slim production image to run)
- `operator-hmi` — built from `apps/operator-hmi/Dockerfile`, served via nginx with SPA fallback routing
- M1-M5 service blocks are commented out at the bottom — uncomment and fill in as each member's module gets a Dockerfile

### Setup
```bash
cp .env.example .env      # fill in POSTGRES_PASSWORD and JWT_SECRET at minimum
docker compose up --build
```
HMI: `http://localhost:5173` · Control API: `http://localhost:4000` · Postgres: `localhost:5432`

### ⚠️ Verification status — read before trusting this blindly
- **YAML syntax**: actually parsed with `pyyaml`, confirmed valid, 5 services detected. This is the only thing that could be checked in the sandbox this was built in — **no Docker daemon was available there**, so the compose file has never actually been run, and neither Dockerfile has ever actually been built.
- **First thing to do**: once Docker Desktop is working, run `docker compose up --build` and watch for errors — especially around the `migrate` service (Prisma CLI needs network access to fetch its query engine on first build, same issue noted in the control-api README) and the nginx SPA routing.
- **Known assumption to double-check**: Docker Compose v2.20+ is required for `condition: service_completed_successfully` (used so `control-api` waits for migrations). Check with `docker compose version` — recent Docker Desktop installs should be fine, but flag it if `docker compose up` complains about that condition syntax.