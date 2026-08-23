# Infra

Owner: M1 (Redis/simulator setup) / M6 (final integration, Docker Compose, CI)

## Contents (to be added)
- `docker-compose.yml` — one-command local demo (Postgres + TimescaleDB, Redis, all services, HMI)
- `.env.template` — environment variable template
- `.github/workflows/` — GitHub Actions CI (lint, test, build per service)

## Rule
Fresh-machine `docker compose up` must bring up the complete seeded demo. This is a mandatory acceptance test owned by M1/M6.
