---
name: docker-authoring
description: Author, review, troubleshoot, and optimize Docker workloads using production-grade Dockerfiles, Compose configuration, BuildKit/Buildx, runtime diagnostics, resource analysis, and security controls. Use when the user asks to containerize an application; write, review, or fix a Dockerfile or compose/docker-compose file; set up a multi-service environment; diagnose container exits, OOM symptoms, startup failures, image or disk bloat, networking, logs, or build problems; assess Docker security or image hardening; or otherwise asks about Docker, containers, images, Compose, Buildx, Docker Desktop, or Docker Engine.
---

# Docker Authoring and Operations

Produce or assess Docker workloads that are correct, cache-efficient, secure, observable, and easy to maintain. Distinguish authoring from diagnosis: if the user asks only for a cause, review, or recommendation, inspect and report without editing files or changing Docker state.

For authoring requests, create files directly in the project directory or wherever the user specifies. If multiple services require separate Dockerfiles, use one subfolder per service.

## Reference files — read before acting

Read every reference relevant to the request before producing files or recommendations:

- `references/dockerfile.md` — read whenever writing or reviewing a Dockerfile: syntax directive, base image pinning, multi-stage, cache/bind/secret mounts, heredocs, non-root, exec form, multi-platform ARGs, .dockerignore.
- `references/compose.md` — read whenever writing or reviewing compose files: a mechanism-selection table plus anchors/x-\*, profiles, override files (`!reset`/`!override`), include, interpolation, healthchecks + depends_on conditions, develop.watch, per-service platform, secrets, version caveats (v2.20+/v5).
- `references/operations.md` — read for runtime/build diagnosis, exit codes, Docker Desktop resources, image or disk usage, Buildx, logging, networks, scanning, hardening, or environment audits.

## Workflow

1. **Classify the request.** Choose authoring, review, troubleshooting, optimization, security assessment, or a combination. Preserve the requested scope and avoid edits during diagnosis-only work.
2. **Inspect the real context.** Read manifests and existing Docker files instead of guessing the stack. For live-environment questions, gather only relevant non-mutating facts such as Docker/Compose/Buildx versions, the active context, container state, and disk usage. Treat inventories as snapshots, not permanent facts.
3. **Read the relevant references.** Use the files listed above. Verify version-gated capabilities against the installed CLI before recommending them; do not rely on remembered release timelines or assume optional plugins, subscriptions, registries, builders, or hardened-image variants are available.
4. **Execute the matching branch** below.
5. **Validate in proportion to the change.** Validate generated configuration and builds when feasible. For diagnosis, corroborate the suspected cause with inspect/log/build output and clearly separate confirmed facts from hypotheses.
6. **Deliver a concise result** in the user's language. Lead with the outcome or root cause, include only the commands or next actions that matter, and identify any unverified assumption.

## Authoring branch

1. **Write the Dockerfile(s).** Use `# syntax=docker/dockerfile:1`, a pinned base-image version tag, dependency installation before source copy, multiple stages when build/install tooling is unnecessary at runtime, a non-root runtime user, exec-form ENTRYPOINT/CMD, and no secrets in layers.
2. **Write Compose configuration.** Select mechanisms from `references/compose.md`: anchors/x-\* for shared config, profiles for optional services, override files for environment differences, watch for development sync, and healthchecks plus conditional `depends_on` for readiness ordering. Omit the obsolete `version:` key.
3. **Add `.dockerignore`.** Add `.env.example` when environment variables are involved, documenting every variable without real secrets.
4. **Validate every generated file.** Prefer `docker compose config` for Compose semantics and interpolation. Also run a relevant build or focused smoke test when feasible. If validation cannot run, state the exact boundary.

## Troubleshooting and audit branch

1. **Establish the failure domain.** Separate build, image, container process, health/readiness, Compose orchestration, network, storage, host-resource, and registry problems before prescribing a fix.
2. **Use evidence, not exit-code folklore.** For exit 137, check container state, `OOMKilled`, configured limits, daemon/host evidence, and logs. Report OOM only when corroborated; SIGKILL and manual termination can produce the same exit code.
3. **Diagnose resource pressure safely.** Inspect usage before proposing cleanup. Show what is reclaimable and what will be deleted. Never run prune, remove volumes, stop stacks, start builders, or change Docker Desktop settings without explicit authorization.
4. **Separate readiness from recovery.** Use healthchecks to report readiness and conditional dependencies to order startup. Use an appropriate restart policy for process recovery; an unhealthy status alone does not restart a container.
5. **Assess security concretely.** Check runtime user, capabilities, writable mounts, secret handling, network exposure, base-image provenance, scan results, and attestations. Recommend Docker Hardened Images or another minimal base only after verifying a compatible image exists and explaining migration constraints; never imply a vendor image has a drop-in hardened equivalent without evidence.
6. **Prioritize findings.** Rank confirmed stability, data-loss, exposure, and supply-chain risks ahead of optional optimization. Keep environment-specific counts, versions, project names, and dates out of reusable guidance.

## Quality bar

Before delivering, check the result against this list — these are the mistakes that make generated Docker files disappointing in practice:

- Would editing one line of source code invalidate the dependency-install layer? (If yes, reorder COPYs; consider cache mounts.)
- Does the runtime image contain compilers, dev dependencies, or source it doesn't need? (If yes, multi-stage.)
- Does anything run as root at runtime without a stated reason? Do any secrets end up in a layer?
- Is any config block copy-pasted between services that an anchor/x-\* block should own?
- Are dev-only and prod-only settings tangled in one file that profiles or override files should separate?
- Will the app race its database at startup? (healthcheck + depends_on condition)
- Is every YAML file validated and every env var documented in `.env.example`?
- Are runtime conclusions supported by current inspect/log/build evidence rather than a stale inventory or exit code alone?
- Are version-specific features verified against the installed Docker, Compose, Buildx, and plugin versions?
- Does every cleanup or state-changing command disclose impact and wait for authorization?
- Are healthchecks, restart policies, resource limits, and observability treated as distinct controls?
