# Deployment profiles

Model the request path from the public client to the application. The correct TLS, real-IP, redirect, health-check, and DNS configuration depends on every hop.

## On premises or a directly exposed VM

- Bind the application to loopback or a Unix socket when Nginx is on the same host.
- Let Nginx own ports 80 and 443 when it is the public edge. Permit only required inbound ports in the host and perimeter firewalls.
- Automate certificate issuance and renewal with the platform's chosen ACME client. Validate the renewal hook and graceful reload; do not stop at initial certificate issuance.
- Use systemd/package paths and include conventions already present on the host. Do not assume Debian's `sites-available` layout on every distribution.
- Preserve the host's log rotation, service user, SELinux/AppArmor policy, file ownership, and socket permissions.
- Log `$remote_addr` directly unless another trusted proxy actually precedes Nginx.

## Container engine or Compose deployment

- Identify the actual engine or platform before emitting configuration. Ask the user when repository artifacts do not distinguish Docker Engine, Podman, or another runtime. Also identify the Compose provider or orchestrator, rootless or rootful operation, whether services share a pod or network namespace, and the network driver.
- Do not infer Docker from a `Dockerfile`, `Containerfile`, Docker-compatible image, Compose YAML, or a `docker`-compatible CLI. These artifacts can be used by more than one engine, and `podman compose` delegates to an external Compose provider.
- Use the runtime's service or network alias and container port when Nginx and the application are separate containers on the same DNS-enabled network. Use `localhost` only when inspection confirms that both processes share a network namespace.
- Mount the complete configuration tree and required certificates read-only. Confirm that included paths exist inside the container.
- Test with the same image digest or tag used by deployment; directives and default behavior vary by version and build.
- Keep only Nginx public. Place application services on an internal network unless direct host exposure is intentional.
- Account for container DNS and upstream lifecycle. A name resolved only at Nginx startup may become stale when task IPs change. For re-resolution, use a runtime-supported Nginx pattern and an observed resolver address, or rely on an orchestration-stable address. If a variable is used in `proxy_pass`, account for its changed URI handling.
- Derive platform-specific values instead of substituting Docker defaults:
  - **Docker Engine:** on a user-defined network, service discovery uses Docker's embedded DNS at `127.0.0.11`. Confirm the attached network and inspect `/etc/resolv.conf` inside the deployed Nginx container before setting `resolver 127.0.0.11`.
  - **Podman:** confirm the network backend and whether DNS is enabled with `podman network inspect`; Netavark networks normally use `aardvark-dns` for container names and aliases. Read the resolver from the deployed container's `/etc/resolv.conf`; do not copy Docker's `127.0.0.11`, because Podman resolver details vary with rootless/rootful networking, the selected network, and `podman machine`.
  - **Other engines or orchestrators:** inspect their service discovery, DNS, namespace, mount, and published-port behavior and use only documented or observed values.
- Match operational settings to the selected engine. Use its actual CLI for inspection and validation, its network and service names, and its bind-mount security semantics. For Podman on SELinux hosts, decide whether a bind mount needs `:z` or `:Z`; for rootless operation, verify UID/GID mapping and permission to publish the requested host ports rather than copying Docker-oriented values.
- Add a meaningful health check and a graceful stop period. `depends_on` start order does not prove application readiness.
- Do not bake private keys into an image layer.

Official references: [Docker networking and embedded DNS](https://docs.docker.com/engine/network/), [Podman network DNS](https://docs.podman.io/en/stable/markdown/podman-network.1.html), [Podman Compose providers](https://docs.podman.io/en/stable/markdown/podman-compose.1.html), and [Podman run and bind-mount options](https://docs.podman.io/en/stable/markdown/podman-run.1.html).

## AWS EC2 directly exposed

- Decide whether the instance has a stable public address and how DNS changes during replacement. Prefer a repeatable deployment rather than hand-edited host state.
- Restrict the instance security group to required client sources and ports. Keep the application port private to the instance or VPC.
- Terminate TLS at Nginx with an appropriate certificate automation path when no integrated AWS edge service owns TLS.
- Preserve EC2 replacement, log shipping, certificate state, and rollback behavior in the deployment design.
- Do not configure ALB-specific real-IP trust when no ALB exists.

## AWS EC2 behind an Application Load Balancer

- Usually terminate public TLS at the ALB with its managed certificate and security policy. Decide explicitly whether the ALB-to-Nginx hop is HTTP or re-encrypted HTTPS.
- Allow the instance security group to receive the listener and health-check traffic only from the ALB security group. Avoid making the instance an alternate public edge.
- Configure a cheap health endpoint and ensure the Nginx virtual host accepts the ALB health-check Host behavior when necessary without opening the application to arbitrary hosts.
- Treat ALB `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Port` as authoritative only because the network boundary prevents untrusted direct access. Understand the configured XFF processing mode. When Nginx needs the original client IP, use ALB's default `append` mode with a correctly bounded real-IP trust chain; `preserve` can retain attacker-supplied content and `remove` does not provide the client chain to Nginx.
- If Nginx restores the client IP, trust only the ALB/VPC proxy addresses that can reach it and use recursive processing deliberately. Never use `set_real_ip_from 0.0.0.0/0`.
- Forward the public scheme from the ALB rather than overwriting it with Nginx's internal `$scheme`; otherwise applications can generate HTTP URLs or redirect loops.
- Align Nginx keepalive, read timeouts, WebSocket/SSE behavior, deregistration delay, and application shutdown with ALB limits and draining.
- Decide whether HSTS and other public response headers are owned by Nginx or another edge layer. Emit each once.

Official AWS references: [ALB forwarded headers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html), [ALB security groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-update-security-groups.html), and [Elastic Load Balancing infrastructure security](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/infrastructure-security.html).

## Kubernetes or another orchestrator

- First determine whether the user means standalone Nginx, an Nginx Ingress Controller, or Gateway API. Their schemas and directive surfaces are not interchangeable.
- Prefer the controller's supported resources and annotations over mounting an ad hoc `nginx.conf` into a managed controller.
- Model the external load balancer, ingress/gateway, service, and pod as separate hops. Configure forwarded headers and source IP preservation at the correct boundary.
- Use service discovery and readiness semantics supplied by the orchestrator. Coordinate termination grace periods with upstream draining.
- Verify controller-specific annotation risk and policy before allowing snippet injection.

## TLS ownership matrix

| Public edge                | Typical TLS owner                              | Nginx implication                                                                |
| -------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------- |
| Nginx on host/VM           | Nginx                                          | Configure certificate paths, HTTP redirect, renewal, and reload.                 |
| ALB before Nginx           | ALB, optionally TLS again to Nginx             | Preserve the original public scheme and restrict direct origin access.           |
| CDN before Nginx           | CDN plus an authenticated/encrypted origin hop | Trust only documented CDN origins; prevent origin bypass.                        |
| Kubernetes ingress/gateway | Controller or external LB                      | Configure TLS in the controller's resource model, not an unrelated server block. |

Do not assume that TLS termination alone establishes trustworthy forwarded headers. Network access control and header replacement must enforce the trust boundary.
