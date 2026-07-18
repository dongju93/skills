# Application profiles

Use the detected framework and production server as constraints, not as a reason to paste a framework-branded template.

## FastAPI and other ASGI applications

- Proxy to the production ASGI process or its Unix socket, not a development reloader.
- Make the Nginx-to-ASGI network boundary explicit. Configure Uvicorn/FastAPI to trust forwarded headers only from Nginx or the actual trusted proxy chain; do not use a wildcard trust setting when the application port is externally reachable.
- Decide whether Nginx preserves or strips a path prefix. If the public API is `/api` but the application serves `/`, align the `location`, `proxy_pass` trailing slash, and FastAPI `root_path`. Verify OpenAPI `servers`, docs assets, redirects, and callback URLs.
- Preserve WebSocket upgrade headers for WebSocket routes. Disable proxy buffering for SSE or `StreamingResponse` routes whose first-byte latency matters.
- Set upload limits at both Nginx and the application. If the ASGI handler must stream the request body, decide whether `proxy_request_buffering off` is acceptable; it shifts slow-client exposure toward the upstream.
- Use a readiness endpoint that does not perform expensive work and keep administrative documentation endpoints public only when intended.

Official framework reference: [FastAPI — Behind a Proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).

## Next.js

First distinguish these deployment modes:

- **`next start` or standalone server:** proxy dynamic pages, Server Components, Route Handlers, image optimization, Server Actions, ISR, and internal asset routes to Next.js.
- **Static export:** serve the exported directory as static files and use `try_files`; do not proxy nonexistent server features.
- **Managed platform:** do not insert standalone Nginx unless the requested topology actually includes it.

For a self-hosted server:

- Put a reverse proxy in front of the Node process, but preserve Next.js response headers.
- Do not add extension-wide caching that overrides dynamic, personalized, ISR, image-optimization, or `Vary` semantics. Next.js already marks hashed immutable assets appropriately.
- Keep streaming end to end. Disable Nginx response buffering on routes that use React/Next.js streaming, or honor the application's `X-Accel-Buffering: no` response.
- Proxy `/_next/` to the application unless the exact build artifacts are deliberately copied into an Nginx-visible, deployment-consistent volume. Prevent rolling deployments from serving HTML and assets from different build IDs.
- Treat multi-instance cache coordination, Server Action encryption keys, deployment IDs, and tag invalidation as application/deployment concerns; Nginx load balancing alone does not solve them.
- Preserve the original host and scheme so redirects, authentication callbacks, and absolute URLs remain correct.

Official framework reference: [Next.js — Self-Hosting](https://nextjs.org/docs/app/guides/self-hosting).

## Django

- Proxy to a production WSGI or ASGI server; never use `manage.py runserver` in production.
- Validate the public host at Nginx and configure Django `ALLOWED_HOSTS`. Use a non-proxying default server for unknown hosts.
- Set Django `SECURE_PROXY_SSL_HEADER` only when the trusted edge strips client-supplied copies and supplies the authoritative header. Align secure cookies, CSRF trusted origins, and HTTPS redirects with the actual TLS termination point to avoid redirect loops.
- Serve collected static files from `STATIC_ROOT` when Nginx owns static delivery. Use an exact URI-to-filesystem mapping and long immutable caching only for fingerprinted files.
- Treat `MEDIA_ROOT` as untrusted user content. Keep it outside executable/application paths, return safe content types where needed, and never pass it to an interpreter.
- Consider application-authorized downloads via `X-Accel-Redirect` and an `internal` location instead of reading large protected files through Django.
- Match Nginx upload size and timeout behavior with Django and the application server.
- Run Django's deployment checks when application scope permits.

Official framework reference: [Django — Deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

## Spring Boot and JVM HTTP services

- Proxy to the embedded server or application container on its private address. Preserve host, scheme, and client information across a trusted boundary.
- Select `server.forward-headers-strategy` based on the server stack and deployment. Use the native strategy when the container handles the deployed forwarded headers correctly; use the framework strategy when Spring's transformer/filter behavior is required.
- Ensure the edge removes untrusted forwarded headers before adding authoritative values. Forwarded-header support without a trusted edge permits spoofing.
- Align Nginx route prefixes with `server.servlet.context-path`, WebFlux base paths, redirects, and generated links.
- Keep Actuator endpoints private by default. Expose a narrow health endpoint for a load balancer only when its response is safe and inexpensive.
- Match multipart limits and timeouts in Nginx, Spring, and the embedded server. For WebFlux or streaming MVC responses, apply the streaming service profile rather than ordinary buffering defaults.
- Treat graceful shutdown and the load balancer's deregistration delay as one drain sequence.

Official framework references: [Spring Boot — Running Behind a Front-end Proxy](https://docs.spring.io/spring-boot/3.3/how-to/webserver.html#howto.webserver.use-behind-a-proxy-server) and [Spring Framework — Forwarded headers](https://docs.spring.io/spring-framework/reference/web/webmvc/filters.html#filters-forwarded-headers).

## Generic upstream

When the framework is unknown, derive behavior from the actual process and routes:

- determine HTTP version, keepalive support, redirects, path-base expectations, body limits, and streaming behavior;
- probe a health route and inspect response headers;
- avoid framework-specific cache, static-file, or forwarded-header assumptions;
- use conservative proxy defaults and record what remains unverified.
