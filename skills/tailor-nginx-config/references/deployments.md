# Deployment profiles

Model the request path from the public client to the application. The correct TLS, real-IP, redirect, health-check, and DNS configuration depends on every hop.

## On premises or a directly exposed VM

- Bind the application to loopback or a Unix socket when Nginx is on the same host.
- Let Nginx own ports 80 and 443 when it is the public edge. Permit only required inbound ports in the host and perimeter firewalls.
- Automate certificate issuance and renewal with the platform's chosen ACME client. Validate the renewal hook and graceful reload; do not stop at initial certificate issuance.
- Use systemd/package paths and include conventions already present on the host. Do not assume Debian's `sites-available` layout on every distribution.
- Preserve the host's log rotation, service user, SELinux/AppArmor policy, file ownership, and socket permissions.
- Log `$remote_addr` directly unless another trusted proxy actually precedes Nginx.

## Docker or Compose

- Use the service DNS name and container port, not `localhost`, when Nginx and the application are separate containers.
- Mount the complete configuration tree and required certificates read-only. Confirm that included paths exist inside the container.
- Test with the same image digest or tag used by deployment; directives and default behavior vary by version and build.
- Keep only Nginx public. Place application services on an internal network unless direct host exposure is intentional.
- Account for container DNS and upstream lifecycle. A name resolved only at Nginx startup may become stale when task IPs change. For re-resolution, set a `resolver` (Docker's embedded DNS is `127.0.0.11`) and use a variable in `proxy_pass` — noting that variables change `proxy_pass` URI handling — or rely on an orchestration-stable address.
- Add a meaningful health check and a graceful stop period. `depends_on` start order does not prove application readiness.
- Do not bake private keys into an image layer.

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
