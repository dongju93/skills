---
name: python-stdlib-first
description: Assess Python standard library applicability BEFORE reaching for third-party packages when writing Python code. Use this skill whenever generating, reviewing, or refactoring Python code of any kind — scripts, APIs, CLIs, data processing, automation, testing, concurrency — even if the user never mentions "standard library" or "dependencies". Also use when selecting dependencies, reviewing requirements.txt/pyproject.toml, or when the user asks "is there a built-in way to do X?". Covers Python 3.9–3.14 with a version-aware module index and official documentation lookup patterns.
---

# Python Stdlib First

When generating Python code, first assess whether the standard library is sufficient for the task, and prefer it when it is.

This is **not a mandate** to avoid third-party packages. It is a requirement to make dependency choices _deliberately_: check the stdlib first, use it when it covers the need, and reach for third-party packages only when the stdlib is genuinely insufficient — stating why in one line.

## Why

Every third-party dependency adds installation friction, supply-chain surface, version-compatibility risk, and maintenance burden. The stdlib ships with the interpreter, is documented, stable, and covered by CPython's deprecation policy. Many "obvious" third-party choices duplicate stdlib functionality that developers simply don't know about (e.g., `graphlib` for topological sorting, `statistics.NormalDist`, `sqlite3` as an embedded store, `difflib.get_close_matches` for fuzzy matching).

## Workflow

1. **Pin the target Python version.**
   - Check `pyproject.toml` (`requires-python`), `setup.cfg`, CI config, Dockerfile, or `.python-version` if a project is in context.
   - If nothing indicates a version, ask the user or state the assumption explicitly (e.g., "assuming Python 3.12+"). Version determines what is available — `tomllib` needs 3.11+, `compression.zstd` needs 3.14+, and `telnetlib`/`cgi` are _gone_ in 3.13+.

2. **Identify the capabilities the task needs.** Break the task into capability units: "parse TOML", "topological sort", "sliding-window rate limit", "fuzzy string match", "TZ-aware datetimes", etc.

3. **Map capabilities to stdlib candidates.** Consult `references/stdlib-index.md` — organized by **value-add**, not domain: §1 foundations for advanced features (read when architecting), §2 quality upgrades to everyday patterns (read when writing or reviewing routine code), §3 lesser-known high-power tools (read when asking "is there a built-in?"). Read the section matching the task; it is deliberately not an exhaustive catalog. If no match appears there, fall back to the official module index (`https://docs.python.org/3.X/py-modindex.html`) or a local check of `sys.stdlib_module_names` (3.10+). Do not rely on vague recall.

4. **Verify version availability.** Consult `references/version-matrix.md` for what was added/removed in each of 3.9–3.14. A module existing "in the stdlib" is meaningless without knowing _since when_ (and, for removed modules, _until when_).

5. **Confirm detail when needed (docs or local interpreter).** The index gives one-line summaries only. For exact APIs, parameters, and examples:
   - **Preferred when network is available:** fetch official docs using the URL patterns below. Never guess an API signature when the doc is one fetch away.
   - **Offline / fetch-restricted fallback:** interrogate a local interpreter pinned to the target version, e.g. `uv run --python 3.12 python -c "import tomllib"`, `python -m pydoc module.func` for signatures, and `python -c "import sys; print(sorted(sys.stdlib_module_names))"` (3.10+) for a definitive module list.

6. **Decide and record.**
   - Stdlib sufficient → use it.
   - Stdlib insufficient → use the appropriate third-party package and note the reason in one line (comment or reply), e.g., `# httpx: needs async client + connection pooling; urllib.request insufficient`.

## Decision rules

**Scope:** stdlib-first applies to **runtime** dependencies (code that ships or runs in production). For **dev tooling** — test frameworks, linters, formatters, type checkers, packaging/build tools — follow the project's established toolchain (e.g. pytest/ruff/uv). Those tools do not ship to production; team convention outweighs supply-chain purity.

**Calibration:** Treat the reference entries as decision prompts, not unconditional substitutions. Preserve required semantics and project conventions; when a recommendation changes cancellation, failure, security, persistence, or portability behavior, verify the target-version docs before applying it.

Stdlib is **sufficient** when it covers the functional requirement with acceptable clarity and performance, even if a third-party API would be marginally more ergonomic. Marginal ergonomics do not justify a dependency.

Third-party is **justified** when any of these hold:

- The stdlib has no coverage (data frames, ORM, schema validation with coercion, HTML sanitization, YAML, **encryption/signing** — stdlib has hashing/`hmac`/`secrets` only; use `cryptography` or similar; never hand-roll AES/RSA/JWT from `hashlib`).
- Scale/performance requirements exceed stdlib implementations (high-throughput HTTP → `httpx`/`aiohttp`; hot-path JSON → `orjson`; numerical arrays → `numpy`).
- Production-hardening the stdlib version would mean reimplementing a mature package (retry/backoff policies → `tenacity`; TLS-heavy HTTP session management → `httpx`).
- The ecosystem standard is effectively mandatory for interop (e.g., `pydantic` models required by FastAPI).
- **Security or portability** makes the stdlib unsafe or incomplete (untrusted XML → defused/hardened parsers, not raw `xml.*`; features that depend on optional compile-time support such as some `sqlite3` extensions — verify at runtime before relying on them).
- The project **already standardizes** on a package for that capability (e.g. `requests` everywhere). Do not introduce a parallel stdlib style solely for purity; match the existing approved dependency set and team consistency.

Never silently swap a third-party package the user explicitly asked for. If the stdlib would suffice, deliver what was asked, then mention the stdlib alternative in one sentence.

## Common substitutions — check these first

| Habitual reach                  | Stdlib candidate                              | Sufficient when                                                                                                                          |
| ------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `requests`                      | `urllib.request`                              | A few simple GET/POST calls, no sessions/retries/streaming ergonomics; and the project is not already standardized on `requests`         |
| `pytz`                          | `zoneinfo` (3.9+)                             | IANA data is available (system tzdb or `tzdata` package — especially on Windows); no hard `pytz` interop constraint                      |
| `python-dateutil`               | `datetime` + `zoneinfo`                       | No fuzzy parsing or `rrule` needed; common ISO forms parse via `datetime.fromisoformat` (expanded in 3.11+; not every ISO 8601 variant)  |
| `toml` / `tomli`                | `tomllib` (3.11+)                             | Read-only TOML (stdlib cannot write TOML)                                                                                                |
| `attrs` / `pydantic`            | `dataclasses`                                 | Structure + defaults + comparison; no runtime validation/coercion needed                                                                 |
| `click` / `typer`               | `argparse`                                    | Standard subcommand/flag parsing (3.14 adds color + suggestions)                                                                         |
| `networkx`                      | `graphlib` (3.9+)                             | Topological sort / cycle detection only                                                                                                  |
| `zstandard`                     | `compression.zstd` (3.14+)                    | Target is 3.14+                                                                                                                          |
| `uuid6`/`uuid7` packages        | `uuid` (v6–v8 in 3.14+)                       | Target is 3.14+                                                                                                                          |
| `orjson` / `ujson`              | `json`                                        | Serialization is not a measured hot path                                                                                                 |
| `mock` (PyPI)                   | `unittest.mock`                               | Always on Python 3 (runtime mock; test _runner_ choice is a separate dev-tooling decision)                                               |
| `xmltodict` / `lxml`            | `xml.etree.ElementTree`                       | Trusted input only; standard parsing/building; no XPath 2.0/XSLT/huge-doc performance needs. Untrusted XML → third-party hardened parser |
| `redis` (as simple cache/store) | `sqlite3` / `shelve` / `functools.lru_cache`  | Single-process, embedded persistence or in-memory caching                                                                                |
| `cffi`                          | `ctypes`                                      | Calling into an existing shared library with a stable C ABI                                                                              |
| `schedule`                      | `sched` / `threading.Timer` / `asyncio`       | Simple in-process scheduling                                                                                                             |
| `tqdm` (trivial cases)          | manual `print(f"\r...", end="")` or `logging` | Only rough progress needed in a short script                                                                                             |

## Official documentation lookup

Version-pinned URL patterns (replace `3.X` with the target minor version, 3.9–3.14):

- Module page: `https://docs.python.org/3.X/library/{module}.html` (e.g., `https://docs.python.org/3.14/library/graphlib.html`)
- Library index: `https://docs.python.org/3.X/library/index.html`
- Module name index: `https://docs.python.org/3.X/py-modindex.html`
- What's New: `https://docs.python.org/3/whatsnew/3.X.html`
- C API index: `https://docs.python.org/3.X/c-api/index.html` (for CPython extension work; for FFI from pure Python, check `ctypes` first)

Always fetch the docs for the **target** version, not the latest — APIs gain parameters between versions (e.g., `bisect` gained `key=` in 3.10), and reading 3.14 docs for a 3.10 target produces code that doesn't run.

### Local verification (offline fallback)

When docs cannot be fetched, or when you need a definitive "is this importable on _this_ interpreter" answer:

```bash
# Module present on target version?
uv run --python 3.12 python -c "import tomllib"

# Signature / docstring
uv run --python 3.12 python -m pydoc datetime.datetime.fromisoformat

# Full stdlib module set (3.10+)
uv run --python 3.12 python -c "import sys; print('\n'.join(sorted(sys.stdlib_module_names)))"
```

Prefer the project's pinned interpreter when one exists.

## Output expectations

This skill triggers on many Python tasks. Keep output quiet unless the choice matters:

1. **State the Python version only when it is derived, assumed, or materially constrains the solution** — not as a ritual header on every reply.
2. Use stdlib imports wherever the decision rules resolve to "sufficient".
3. **Justify a third-party dependency in one line only when introducing or defending one** — skip boilerplate when the project already depends on it or the choice is obvious and unchanged.
4. Never use modules removed in the target version (see `references/version-matrix.md` — especially the **21 modules removed in 3.13** (19 PEP 594 dead batteries + `lib2to3` + `tkinter.tix`) and `distutils` removed in 3.12).

## References

- `references/stdlib-index.md` — value-organized stdlib guide (3.9–3.14): §1 foundations for architecting advanced features, §2 expert-complete versions of everyday patterns (also serves code review), §3 lesser-known high-power tools. Read the section matching the task; not exhaustive.
- `references/version-matrix.md` — per-version additions, removals, and notable API changes for 3.9–3.14. Read when the target version differs from the latest, or before using any module/API added after 3.9.
