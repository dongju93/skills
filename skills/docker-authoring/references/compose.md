# Compose reference — advanced syntax for shared and variant configuration

Sourced from docs.docker.com (Compose file reference, Compose watch, include, merge) and docker/compose releases, current as of mid-2026.

## Modern Compose basics

- File name: `compose.yaml`. The top-level `version:` key is obsolete — omit it.
- Compose v2.22+ supports watch; v2.20.3+ supports include. Compose v5.x (2025-12+) delegates builds to Docker Bake (multi-platform builds work out of the box) and v5.3+ adds native pre-start init containers (`pre_start_init_containers`). Don't rely on v5-only fields unless the user confirms their version.

## Choosing the right mechanism

| Need                                       | Mechanism                                  |
| ------------------------------------------ | ------------------------------------------ |
| Shared config between services, one file   | YAML anchors + `x-*` extension fields      |
| Optional services within one environment   | `profiles`                                 |
| dev/prod (per-environment) differences     | multiple files: `compose.yaml` + overrides |
| Reuse another team's/project's whole stack | `include`                                  |
| Values that vary (tags, ports)             | `${VAR:-default}` interpolation            |
| Hot reload during development              | `develop.watch`                            |
| One service needs a specific CPU arch      | per-service `platform`                     |

## Anchors and x-\* extension fields

Top-level keys starting with `x-` are ignored by Compose — the standard place to define shared blocks, merged into services with `<<:`:

```yaml
x-app-base: &app-base
  restart: unless-stopped
  env_file: .env
  logging:
    driver: json-file
    options: { max-size: "10m", max-file: "3" }

services:
  api:
    <<: *app-base
    build: ./app
  worker:
    <<: *app-base
    build: ./app
    command: ["python", "worker.py"]
```

`<<:` is a _shallow_ merge: a key defined on the service replaces the anchor's value wholesale (a service-level `logging:` replaces the whole block, not just one option). Multiple anchors: `<<: [*base, *logging]` — earlier entries win on conflict.

## Profiles

Services with `profiles:` only start when that profile is activated; services without always start.

```yaml
services:
  pgadmin:
    image: dpage/pgadmin4:9
    profiles: [debug]
```

`docker compose --profile debug up`, or `COMPOSE_PROFILES=debug`. Good candidates: DB admin UIs, mail catchers, seed/migration jobs, observability sidecars. If an always-on service `depends_on` a profiled one, Compose errors unless the profile is active — keep dependencies within the same profile.

## Multiple files: merge/override pattern

For per-environment variants. Later files merge over earlier ones (scalars replace, maps merge, lists append):

- `compose.yaml` — base: services, images/builds, networks, healthchecks
- `compose.override.yaml` — dev conveniences, **loaded automatically** by plain `docker compose up`: published ports, bind mounts or watch, debug env
- `compose.prod.yaml` — prod: `restart: always`, `deploy.resources.limits`, replicas, no source mounts

```console
docker compose up                                        # base + override (dev)
docker compose -f compose.yaml -f compose.prod.yaml up -d  # prod (override NOT loaded)
```

Naming a file `compose.override.yaml` is what makes dev the zero-flag default — prefer this over one file with commented-out sections. To remove (not just change) a base value in an override, use `!reset`; to replace a whole merged list/map, use `!override`.

## include

Composes another project's compose file into yours as a building block — each included file resolves its own relative paths (which merge via `-f` gets wrong):

```yaml
include:
  - ../shared-infra/compose.yaml # e.g. declares db, redis
  - oci://docker.io/org/stack:latest # OCI artifact or Git URL also work
services:
  api:
    build: .
    depends_on: [db]
```

Conflicting redefinition of an included resource is an error; customize via a local override file listed in the same `path:` entry, or via global `compose.override.yaml`. `include` is recursive.

## Variable interpolation

`${VAR:-default}` (default if unset/empty), `${VAR-default}` (default if unset), `${VAR:?error message}` (require). Values come from the shell and `.env` in the project directory.

```yaml
services:
  api:
    image: myapp:${TAG:-dev}
    ports:
      - "${API_PORT:-8000}:8000"
```

Document every variable in `.env.example`; never commit real `.env`.

## Healthchecks and startup order

`depends_on` alone only orders creation. To wait for readiness, combine `condition: service_healthy` with a healthcheck on the dependency:

```yaml
services:
  api:
    depends_on:
      db:
        condition: service_healthy
      migrations:
        condition: service_completed_successfully
  db:
    image: postgres:16-alpine
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "pg_isready -U ${POSTGRES_USER:-app} -d ${POSTGRES_DB:-app}",
        ]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s
```

Common tests: postgres `pg_isready`, redis `redis-cli ping`, mysql `mysqladmin ping`, HTTP `curl -f http://localhost:8000/health` (curl/wget must exist in the image).

A healthcheck only changes the container's health status; Docker Compose does not restart a running container merely because it becomes unhealthy. A `restart:` policy applies after the container process exits. If recovery from a persistent unhealthy state is required, fix the application failure behavior or use an explicitly chosen supervisor/orchestrator rather than presenting healthcheck + `depends_on` as automatic recovery.

## develop.watch — hot reload

Preferred over plain bind mounts for dev: granular ignores, no host/container artifact clashes (e.g. native `node_modules`). Requires `build:` (not pre-built `image:`), a container user that can write the target (`COPY --chown`), and `stat`/`mkdir`/`rmdir` in the image. Run with `docker compose up --watch` (or `docker compose watch` for separate logs).

```yaml
services:
  web:
    build: .
    develop:
      watch:
        - action: sync # copy changed files in; for hot-reload frameworks
          path: ./src
          target: /app/src
          initial_sync: true
          ignore: [node_modules/]
        - action: rebuild # rebuild image + recreate container
          path: package.json
        - action: sync+restart # sync then restart container; for config files
          path: ./nginx.conf
          target: /etc/nginx/conf.d/default.conf
```

`ignore` patterns are relative to the rule's `path`; `.dockerignore` rules also apply. Pattern: sync source files, rebuild on dependency-manifest changes (`package.json`, `requirements.txt`).

## Per-service platform and resources

```yaml
services:
  legacy-tool:
    image: vendor/amd64-only-tool:2.1
    platform: linux/amd64 # only where required (e.g. on ARM hosts)
  api:
    deploy:
      resources:
        limits: { cpus: "1.0", memory: 512M }
        reservations: { memory: 256M }
```

Multi-platform _image builds_ go through `docker buildx build --platform linux/amd64,linux/arm64` (or `build.platforms` in compose with Bake).

## Also use where appropriate

- **Named volumes** for data outliving containers (`pgdata:/var/lib/postgresql/data`); bind mounts only for dev source/config.
- **Networks** to segment services that shouldn't reach each other (e.g. `frontend`/`backend`; db only on `backend`).
- **secrets:** mounts credential files at `/run/secrets/<name>` instead of env vars:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password]
secrets:
  db_password:
    file: ./secrets/db_password.txt
```
