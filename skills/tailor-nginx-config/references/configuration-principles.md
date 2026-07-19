# Configuration principles

Use this reference to prevent syntactically valid but behaviorally incorrect configurations.

## Respect directive context and packaging

Identify where the generated file is included:

- a complete `nginx.conf` may contain top-level `events` and `http` blocks;
- a file included from `http` may contain `map`, `upstream`, shared zones, and `server` blocks;
- a file included from a `server` may contain locations and server-context directives but not `http`-only declarations;
- an ingress-controller resource is not a standalone Nginx configuration.

Use `nginx -T` to see the merged configuration and detect duplicate or shadowed declarations.

## Model location and upstream URI behavior

For each route, write down a public request and the exact upstream URI it should become. Then choose the `location`, optional rewrite, and `proxy_pass` form.

- `proxy_pass http://app;` without a URI preserves the normalized request URI.
- `proxy_pass http://app/;` inside `location /api/` replaces the matching `/api/` prefix with `/`.
- Exact, prefix, and regex location selection can change which policy applies. Prefer explicit prefix locations and `^~` only when preventing later regex selection is intentional.
- Keep `alias` directory slashes aligned with the location. Test missing files and traversal-like paths.

Official references: [Proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass) and [HTTP core location processing](https://nginx.org/en/docs/http/ngx_http_core_module.html#location).

## Establish a forwarded-header trust boundary

At the public edge, replace spoofable forwarding headers with authoritative values. Behind another trusted proxy, preserve the authoritative public values rather than overwriting them with the internal hop.

A direct-edge baseline is:

```nginx
proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $remote_addr;
proxy_set_header X-Forwarded-Proto $scheme;
```

Replacing `X-Forwarded-For` at the public edge prevents a client-supplied chain from becoming trusted downstream. Do not substitute `$proxy_add_x_forwarded_for` unless a preceding trusted-proxy chain has been normalized and preserving that chain is an explicit requirement.

Do not use this baseline unchanged behind every load balancer. For example, `$scheme` can be `http` between an ALB and Nginx even though the public request was HTTPS. Preserve or map the trusted incoming scheme in that topology.

Use the real-IP module only when Nginx must replace `$remote_addr`. List only trusted proxy addresses or CIDRs with `set_real_ip_from`; then select `real_ip_header` and `real_ip_recursive` according to the actual chain. Verify module availability.

Official references: [Real-IP module](https://nginx.org/en/docs/http/ngx_http_realip_module.html) and [AWS ALB forwarded headers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html).

## Keep headers policy-aware

- Add `X-Content-Type-Options: nosniff` when response content types are controlled correctly.
- Choose `Referrer-Policy` from product requirements.
- Choose framing policy through CSP `frame-ancestors` or `X-Frame-Options` with awareness of intended embedding.
- Generate CSP from actual script, style, image, connection, frame, and worker sources. Prefer nonces or hashes when the application supports them; do not invent `'unsafe-inline'` as a universal fix.
- Emit HSTS only on HTTPS responses when the operator commits to continued HTTPS. Add `includeSubDomains` and `preload` only after separate readiness checks.
- Coordinate CORS in one layer. Nginx should not duplicate or conflict with framework CORS behavior.
- Remember that `add_header` inheritance changes when a child context declares its own header. Use `always` when the header must appear on error responses and confirm behavior on the deployed Nginx version.

Do not emit the obsolete `X-XSS-Protection: 1; mode=block` header.

Official Nginx reference: [Headers module](https://nginx.org/en/docs/http/ngx_http_headers_module.html).

## Start complete files from a working baseline

When the deliverable is a complete `nginx.conf`, minimalism removes unproven tuning — not the directives a working server requires. Snippets included into an existing tree inherit these from the parent file; verify with `nginx -T` instead of re-declaring them.

```nginx
worker_processes auto;

events {
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile      on;
    tcp_nopush    on;

    server_tokens off;

    # server blocks or conf.d includes per the deployment's packaging
}
```

- Omitting `include mime.types;` makes every response fall back to `default_type`, which silently breaks content types and the `nosniff` guidance elsewhere in this skill.
- `tcp_nopush` acts only while `sendfile` is on; pair them. Leave `tcp_nodelay` at its default of `on`.
- `server_tokens off` removes the version from the `Server` header and error pages; it is baseline hardening, not tuning.
- Keep the `keepalive_timeout` default unless a fronting load balancer's idle timeout requires Nginx's to be longer (see the ALB deployment profile).
- Enable gzip at `http` level when the workload serves compressible text-like payloads:

  ```nginx
  gzip on;
  gzip_vary on;
  gzip_min_length 1024;
  gzip_types text/css application/javascript application/json image/svg+xml text/plain application/xml;
  ```

  `text/html` is always compressed and must not be listed. Keep `gzip_comp_level` at its default unless CPU-versus-bytes measurements justify raising it. Do not compress responses that reflect secrets beside attacker-influenced content (BREACH), and keep compression off SSE/streaming locations where it delays small frames. Brotli and zstd require optional modules — confirm with `nginx -V` before emitting their directives.

- Deliberately omitted, not forgotten: `use epoll` (Nginx selects the optimal event method per platform automatically), `multi_accept` (not generally recommended), `open_file_cache`, buffer-size tables, and cipher strings. Add these only from the evidence-driven sections below.

## Tune from constraints

- Start with `worker_processes auto` only when producing a complete configuration and the deployment has not intentionally constrained workers elsewhere.
- Derive connection capacity from worker limits, file descriptors, upstream connections, keepalive, and long-lived streams. `worker_connections` is not a throughput promise.
- Leave proxy buffering enabled for ordinary responses; tune buffers only after observing headers, response sizes, memory, and temporary-file I/O.
- Choose timeouts for connection establishment, inter-read gaps, inter-write gaps, and client behavior separately. `proxy_read_timeout` measures the gap between reads, not total request duration.
- Set per-route request-body limits. Raising a global limit increases exposure and temporary-storage demand.
- Enable compression per the baseline section above; avoid double compression when a CDN, the application, or precompressed assets already provide it.
- Define log formats with request ID, status, timings, upstream address/status/time, bytes, host, method, and URI as operationally needed. Exclude credentials, tokens, sensitive query strings, and unnecessary personal data.

## Treat rate limiting as product policy

Define zones at `http` level and enforcement at the narrowest correct `server` or `location`.

- Choose the key only after client-IP restoration is trustworthy.
- Use separate policies for login, password reset, expensive search, uploads, and general APIs.
- Understand `burst`, delay, and `nodelay`; they change latency and rejection behavior.
- Prefer `limit_req_status 429` when the public API contract treats rejection as rate limiting.
- Start with `limit_req_dry_run on` when real traffic has not established a safe threshold.
- Coordinate limits with CDN, WAF, ALB, application, and downstream quotas.

Official reference: [Request limiting module](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html).

## Make TLS deployment-owned and current

- Determine the TLS owner before writing certificate directives.
- Use the current organizational or platform TLS policy instead of copying a static cipher string from an old example.
- Prefer TLS 1.2 and 1.3 when client requirements allow, but verify the deployed OpenSSL/Nginx build and compliance needs.
- Automate issuance, renewal, permissions, and graceful reload. Validate a renewal rehearsal.
- Protect the origin when TLS terminates at an upstream load balancer or CDN; encryption without origin access control does not prevent bypass.
- Add OCSP, session, HTTP/2, and HTTP/3 settings only when supported by the deployed build and topology.

## Preserve version and module compatibility

Inspect `nginx -V` rather than assuming the latest documentation matches the target. Examples of drift include HTTP/2 listen syntax, newer header inheritance directives, changing proxy HTTP-version defaults, commercial-only directives, and optional real-IP/thread/compression modules.

Prefer widely compatible explicit behavior when it is harmless, such as `proxy_http_version 1.1` for WebSocket-capable proxy locations. Never emit a directive solely because it appears in current documentation if the target image lacks it.

Use the [Nginx directive index](https://nginx.org/en/docs/dirindex.html) and the deployed version's documentation during final verification.
