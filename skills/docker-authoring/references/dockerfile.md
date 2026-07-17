# Dockerfile reference — current best practices

Sourced from docs.docker.com (build best practices, Dockerfile reference, build secrets), current as of mid-2026.

## Syntax directive

Start every Dockerfile with the syntax directive so BuildKit uses the latest stable Dockerfile frontend (heredocs, mounts, and newer flags depend on it):

```dockerfile
# syntax=docker/dockerfile:1
```

## Base image selection

- Use Docker Official Images / Verified Publisher images as the base.
- Pin a specific version tag (`python:3.12-slim`, `node:22-alpine`) — never `latest`. Tags are mutable, so for supply-chain integrity in production, pin the digest too:

```dockerfile
FROM alpine:3.21@sha256:a8560b36e8b8210634f77d9f7f9efd7ffa463e380b75e2e74aff4511df3ef88c
```

Digest pinning trades away automatic security patches — mention the tradeoff when you use it. Use two base image types: a full one for building/testing, a slim one for the runtime stage.

## Multi-stage builds

Split build and runtime into stages; the final image contains only what the app needs to run. BuildKit builds only the stages the target depends on, and independent stages build in parallel.

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.23 AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /bin/app ./cmd/app

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /bin/app /app
ENTRYPOINT ["/app"]
```

When multiple images share setup, create a reusable common stage and base the others on it (built once, cached for all).

## Layer caching

Order instructions least-changing → most-changing. Copy dependency manifests and install *before* copying source:

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
```

**Cache mounts** persist package-manager caches across builds:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

**Bind mounts** beat COPY for files needed only during a RUN (no extra layer):

```dockerfile
RUN --mount=type=bind,source=requirements.txt,target=/tmp/requirements.txt \
    pip install --requirement /tmp/requirements.txt
```

## RUN patterns

- Always combine `apt-get update && apt-get install` in one RUN (separate RUNs cause stale-cache installs). Use `--no-install-recommends` and clean up in the same layer: `&& rm -rf /var/lib/apt/lists/*`.
- Sort multi-line package lists alphabetically; one package per line.
- Heredocs for multi-command steps — cleaner than `&&` chains:

```dockerfile
RUN <<EOF
apt-get update
apt-get install -y --no-install-recommends curl git
rm -rf /var/lib/apt/lists/*
EOF
```

- Pipes: `/bin/sh -c` only checks the last command's exit code. Prepend `set -o pipefail &&` (or use exec-form bash) when a pipe must fail fast.

## Secrets

Never bake secrets into layers — no `ENV API_KEY=...`, no `COPY .env`. Even values unset later persist in earlier layers. For build-time secrets use a secret mount; the file exists only during that RUN and never enters any layer:

```dockerfile
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) npm ci
```

Build with `docker build --secret id=npm_token,src=.npmrc-token .`

## Runtime correctness

- **Non-root user**: create and switch in the runtime stage; use `COPY --chown=app:app` so the user owns its files (also required for Compose watch to sync).

```dockerfile
RUN useradd -ms /bin/sh -u 1001 app
USER app
COPY --chown=app:app . /app
```

- **Exec form** for ENTRYPOINT/CMD (`CMD ["uvicorn", "app:app"]`) — shell form wraps the process in `sh -c`, breaking signal delivery and graceful shutdown.
- **ENTRYPOINT + CMD split**: ENTRYPOINT for the fixed command, CMD for default overridable args.
- `EXPOSE` the conventional port for the service. Add a `HEALTHCHECK` for long-running services (or define it in compose).
- One concern per container — separate app, db, cache into their own services rather than one fat image.

## COPY vs ADD

Prefer COPY. ADD only for its specific powers (remote HTTPS/Git URLs, auto tar extraction). Useful COPY flags: `--chown`, `--exclude=pattern` (repeatable), `--link` (layer reuse when rebasing onto updated base images).

## Multi-platform awareness

BuildKit provides `TARGETPLATFORM`/`TARGETARCH`/`TARGETOS` as automatic ARGs. Use them instead of hardcoding an arch:

```dockerfile
ARG TARGETARCH
RUN curl -fsSL "https://example.com/tool-linux-${TARGETARCH}" -o /usr/local/bin/tool
```

For cross-compiling languages (Go, Rust), run the builder stage on the native build platform:

```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.23 AS builder
ARG TARGETOS TARGETARCH
RUN GOOS=$TARGETOS GOARCH=$TARGETARCH go build -o /bin/app .
```

## .dockerignore

Always create one. Minimum: `.git`, dependency dirs installed in-image (`node_modules/`, `.venv/`), build output, `.env` and secret files, editor/OS junk, `*.md` where irrelevant. A missing .dockerignore bloats build context, breaks caching, and can leak secrets into layers. Note that Compose watch also respects `.dockerignore` rules.
