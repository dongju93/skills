# Docker operations and diagnosis reference

Use this reference for live Docker troubleshooting, environment audits, capacity issues, build infrastructure, and security recommendations. Prefer the smallest set of read-only commands that can confirm or reject a hypothesis.

## Establish current capabilities

Do not turn one machine's inventory into reusable truth. Check the environment involved in the request:

```console
docker version
docker context show
docker info
docker compose version
docker buildx version
docker buildx ls
```

Use only the relevant commands. `docker info` can be verbose and may expose registry names or labels, so summarize only task-relevant fields. Identify the client OS and daemon/backend location before suggesting host-level commands: Linux daemon logs, macOS Docker Desktop VM diagnostics, Windows/WSL event sources, and remote contexts are not interchangeable. Never give `journalctl`, `dmesg`, macOS Console, or Windows Event Viewer steps without establishing that platform. Verify optional features and plugins directly before recommending their commands. Treat release dates, subscription tiers, hosted services, and catalog availability as time-sensitive.

## Container failure triage

Start with container state and a bounded log sample:

```console
docker ps -a --no-trunc
docker inspect <container>
docker logs --tail 200 <container>
```

Read `.State.Status`, `.State.ExitCode`, `.State.OOMKilled`, `.State.Error`, health output, restart count, timestamps, and configured resource limits together.

### Exit 137

Exit 137 means the process ended from `SIGKILL`; it is not proof of OOM by itself. Corroborate an OOM diagnosis with `State.OOMKilled`, memory-limit/usage evidence, daemon or host events, and the timing/content of logs. `HostConfig.Memory: 0` means no container-specific hard limit; it does not rule out host or Docker Desktop VM memory pressure. Also consider manual `docker kill`, a `docker stop` grace-period timeout, forced shutdown, Docker Desktop/daemon restart, or an external supervisor. Use bounded `docker events` around the exit time when event history is still available, then choose any host-level evidence source according to the established platform/backend.

For a running workload, use a short observation rather than indefinite monitoring:

```console
docker stats --no-stream
docker inspect --format '{{json .State}}' <container>
```

If memory pressure is confirmed, distinguish:

- an undersized container limit;
- an undersized Docker Desktop VM/host allocation;
- expected workload growth;
- an application leak or unbounded cache;
- multiple stacks competing for the same host.

Do not recommend increasing memory as the only fix when usage grows without bound. Do not change limits or Docker Desktop settings without authorization.

## Health, startup, and restart behavior

A healthcheck reports status. It does not restart an unhealthy container by itself. Use:

- healthchecks for readiness/liveness signals;
- `depends_on.condition: service_healthy` for dependency startup ordering;
- restart policies for recovery after the container process exits;
- application-level retry/backoff for transient dependencies.

Inspect healthcheck output before rewriting timing values. A missing tool inside a minimal image (`curl`, `wget`, or a database client) can make the check fail even when the service is healthy; prefer a check supported by the runtime image or an application-native probe.

## Disk and image usage

Measure first:

```console
docker system df -v
docker image ls
docker container ls -a --size
docker volume ls
docker buildx du
```

Identify whether usage comes from active images, stopped containers, BuildKit cache, or volumes. Avoid claiming the sum of displayed image sizes equals real disk use because layers may be shared.

Cleanup is destructive. Preview and explain scope before requesting approval:

- `docker builder prune` removes unused build cache.
- `docker image prune` removes dangling images; `-a` broadens this to all images unused by containers.
- `docker container prune` removes stopped containers.
- `docker system prune` combines several cleanup categories.
- volume pruning can delete persistent application data and requires explicit, specific approval.

Do not suggest moving image layers to volumes; volumes store runtime data, not registry image layers. Optimize large custom images with multi-stage builds, a tighter build context, and layer inspection. For large third-party images, first verify whether a smaller supported tag exists.

## Buildx and multi-platform builds

Inspect the selected builder and supported platforms before changing it:

```console
docker buildx ls
docker buildx inspect
docker buildx du
```

A stopped custom builder is not inherently a defect if another selected builder serves current builds. Do not start, remove, or switch builders merely to make an audit look healthy. For multi-platform output, choose `--load`, `--push`, or an OCI output deliberately; a multi-platform result cannot generally be loaded into the classic local image store as one manifest list.

Use cache import/export in CI only when the registry or cache backend is configured. Verify credentials and destination before any push.

## Logging and observability

Start with existing evidence (`docker logs`, Compose logs, health history, restart count, and daemon events). Add centralized logging only when workload scale, retention, or cross-service correlation justifies its operational cost.

Configure log rotation for local JSON logs to prevent unbounded host growth. Do not confuse Docker CLI output formatting with daemon logging-driver configuration. Keep application logs on stdout/stderr unless the application has a documented external logging requirement.

## Network and secret review

Use `docker network inspect` and Compose configuration to confirm actual attachment and published ports. Docker bridge networks provide segmentation and service discovery, not Kubernetes-style network policy. Avoid claiming policy enforcement unless an enforcing component is present.

Check for:

- databases or admin UIs published to all host interfaces unnecessarily;
- services attached to both public-facing and data networks without need;
- secrets embedded in images, Compose files, command arguments, or committed `.env` files;
- writable host mounts and Docker socket mounts;
- excessive Linux capabilities or privileged mode.

Compose secrets improve file-based delivery but local Compose secret files still require host filesystem protection. Do not present them as equivalent to an external secret manager.

## Image security and hardening

Prefer Official Images, Verified Publisher images, or an organization's vetted registry. Before recommending Docker Hardened Images, distroless, Alpine, or another minimal base:

1. Verify a compatible image/tag and architecture exist.
2. Check libc, package-manager, shell, certificate, debugging, and native-extension requirements.
3. Explain whether the change is a base-image rebuild or a vendor-supported drop-in replacement.
4. Rebuild and test the application; do not rewrite third-party vendor images speculatively.

Run scanners or policy tools only when installed or explicitly requested. Report the scanner, database timestamp if available, image digest, severity policy, and limitations. A scan result does not prove an image is signed; a signature does not prove it is vulnerability-free. Verify SBOMs, provenance attestations, and signatures independently when they matter.

## Recommendation format

Lead with confirmed findings. For each recommendation, state:

1. evidence;
2. impact;
3. smallest safe action;
4. validation or rollback;
5. whether approval or downtime is required.

Separate urgent stability/security issues from cost or convenience improvements. Avoid prescribing a monitoring stack, hosted build service, migration agent, or subscription product unless the user's scale and constraints justify it.
