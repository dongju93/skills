# Service profiles

Combine all profiles used by the application. Apply special behavior to the narrowest correct location.

## Static sites and application assets

- Use `root` when the URI is naturally appended to a directory; use `alias` when the location prefix maps to a different filesystem prefix. Match trailing slashes on both sides.
- Use `try_files` for actual routing behavior: `=404` for ordinary files, or the application entry point only for a true client-routed SPA.
- Enable `sendfile` when the operating system and storage make it appropriate. Do not add AIO, `directio`, or thread-pool tuning without file sizes, storage behavior, and module support.
- Apply `immutable` only to content-addressed filenames. Keep HTML and mutable manifests short-lived or revalidated.
- Preserve correct MIME types and `nosniff`. Avoid a broad extension regex that captures dynamic framework routes.
- Precompressed assets require matching build artifacts and module support; do not enable them merely because compression sounds faster.

## Public and protected file serving

- Support byte ranges and conditional requests for large downloads unless the product explicitly forbids them.
- Set `Content-Disposition` and content type from a trusted mapping, not unsanitized query parameters.
- For user uploads, prevent interpretation as scripts or HTML where that would create same-origin active content risk. Consider a separate download origin.
- For authorization-controlled files, let the application authorize and return `X-Accel-Redirect` to an `internal` Nginx location. Keep the internal filesystem mapping unreachable directly.
- Choose rate limits and bandwidth controls from product requirements; do not punish all clients globally for large-file traffic.

Official Nginx reference: [HTTP core module (`root`, `alias`, `internal`, `sendfile`, `try_files`)](https://nginx.org/en/docs/http/ngx_http_core_module.html).

## API gateway and ordinary reverse proxy

- Define an explicit route table. Verify how exact matches, longest prefixes, regex locations, rewrites, and `proxy_pass` URI replacement combine.
- Preserve the original method and body. Avoid rewrites implemented with `if` when a direct location or named location is sufficient.
- Pass the authoritative host, scheme, client chain, and request ID. Hide internal upstream details only when doing so does not erase useful protocol semantics.
- Keep response buffering enabled for ordinary APIs unless latency or memory evidence says otherwise; it isolates upstreams from slow clients.
- Do not cache authenticated, personalized, mutation, `Set-Cookie`, or ambiguous `Vary` responses. If caching public GET/HEAD responses, define the complete cache key, bypass rules, TTL ownership, stale policy, and invalidation behavior.
- Apply per-route body limits and timeouts. A login request, JSON API call, report export, and upload should not inherit one arbitrary maximum.
- Use a 429 response for intentional request-rate rejection when that matches the API contract. Start with `limit_req_dry_run on` when thresholds are unproven.
- Key limits on the restored client IP only after establishing the real-IP trust chain. Recognize that IP-only limits aggregate NAT users and can be distributed across IPv6 addresses.

Official Nginx references: [Proxy module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) and [Request limiting](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html).

## Uploads and streamed request bodies

- Set `client_max_body_size` to the product limit, with route-specific overrides where appropriate.
- Keep request buffering on when protecting the upstream from slow clients and temporary disk use is acceptable.
- Disable `proxy_request_buffering` only when the upstream truly consumes a stream, request size is still bounded, timeouts are controlled, and retry/failover behavior is understood.
- Align temporary storage capacity, permissions, and container writable paths with the largest expected concurrent uploads.
- Test just below and above the limit and verify that Nginx and the application return the intended status and body.

## WebSocket

Define the connection mapping at `http` level when ordinary HTTP and WebSocket share the server:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

On the WebSocket location, explicitly pass the upgrade headers and retain `proxy_http_version 1.1` for compatibility:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

- Choose `proxy_read_timeout` from the heartbeat interval and acceptable failure-detection time. Prefer application ping frames over an effectively infinite timeout.
- Disable proxy caching. Disable response buffering if the surrounding location would otherwise enable behavior unsuitable for the tunnel.
- Test a real 101 upgrade and bidirectional messages through every edge hop.

Official Nginx reference: [WebSocket proxying](https://nginx.org/en/docs/http/websocket.html).

## SSE, long polling, and HTTP streaming

- Disable response buffering on the streaming location: `proxy_buffering off;`.
- Disable proxy caching and avoid transformations that batch or compress tiny event frames unless latency tests prove them safe.
- Set `proxy_read_timeout` longer than the application's heartbeat gap, not arbitrarily forever.
- Preserve end-to-end streaming through CDNs and load balancers. Nginx alone cannot prevent another hop from buffering.
- Do not cargo-cult `chunked_transfer_encoding off`; use it only for a known incompatible HTTP/1.1 client or intermediary.
- Verify time to first event and delivery cadence, not only the final response.

Nginx can also honor `X-Accel-Buffering: no` from the upstream. See [proxy buffering](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering).

## Next.js and other streamed SSR

- Follow the SSE/streaming buffering rules for streamed HTML or React Server Component responses.
- Preserve application `Cache-Control` and `Vary` headers. Do not cache personalized shells or mix deployment versions.
- Test first-byte delivery and client navigation through the complete production path.

## gRPC

- Use `grpc_pass` or `grpcs://` for the upstream and ensure the deployed build includes the HTTP/2 and gRPC modules.
- Configure the client-facing HTTP/2 syntax supported by the deployed Nginx version; do not copy version-specific `listen ... http2` syntax blindly.
- Set gRPC connect, read, and send timeouts from actual RPC lifetimes and streaming behavior.
- Preserve trailers and test with a real gRPC client. Do not validate only with an HTTP/1 curl request.
- Keep retry behavior safe for the RPC's idempotency and ensure no response has already reached the client.

Official Nginx reference: [gRPC module](https://nginx.org/en/docs/http/ngx_http_grpc_module.html).

## Load balancing

- Select round robin, `least_conn`, hashing, weights, backup behavior, and keepalive from the workload and application state model.
- Prefer stateless applications. Use sticky routing only when the application genuinely requires affinity and understand its failure behavior.
- Coordinate application health, passive Nginx failure detection, and external load-balancer health checks. Open-source Nginx capabilities differ from Nginx Plus active health checks.
- Avoid replaying non-idempotent requests after an upstream may have processed them.
- For multiple Next.js instances, Django local-memory sessions/caches, or in-process Spring state, solve consistency at the application/storage layer rather than hiding it with accidental affinity.
