# Standard Library Index (Python 3.9–3.14)

**Curated by value-add, not by domain.** A competent developer — or model — already reaches for `json`, `re`, `pathlib`, `collections`, and `argparse` unprompted, so those earn no entries here. Every entry below is a _delta_: something that changes the output compared to the habitual version.

Pick the section that matches the task:

| Task shape                                                              | Read                                    |
| ----------------------------------------------------------------------- | --------------------------------------- |
| Designing something advanced (service, framework, pipeline, plugin API) | §1                                      |
| Writing or reviewing everyday code (files, subprocess, logging, time)   | §2                                      |
| "Is there a built-in for X?" / replacing a dependency                   | §3 + the substitution table in SKILL.md |

One-line summaries only — fetch `https://docs.python.org/3.X/library/{module}.html` for exact APIs. Version tags like `(3.11+)` mean "added in that version"; untagged items exist across 3.9–3.14. If nothing here matches: the official module index `https://docs.python.org/3.X/py-modindex.html`, or locally `python -c "import sys; print(sorted(sys.stdlib_module_names))"` (3.10+).

---

## 1. Foundations — primitives to build advanced features on

Read when architecting. Load-bearing building blocks that replace a framework or a hand-rolled subsystem.

### 1.1 Structured concurrency and async correctness

- `asyncio.TaskGroup` (3.11+) — owned task lifetimes: one failure cancels siblings and surfaces as an `ExceptionGroup` (handle with `except*`). Also fixes the bare-`create_task` bug where an unreferenced task can be garbage-collected mid-flight. Default over `gather` for new code.
- `asyncio.timeout` (3.11+) — cancellation-correct deadlines as a context manager; supersedes `wait_for` wrapping.
- `contextvars` — request-scoped state that survives `await` (correlation IDs, auth context). `threading.local` silently breaks under async; this is what tracing and logging context ride on.
- `asyncio.to_thread` (3.9+) — the one-line bridge for blocking calls inside async code; a blocking call in a coroutine stalls the whole event loop.
- `queue.Queue` / `asyncio.Queue` — producer/consumer backbone: `task_done()`/`join()` for completion, `Queue.shutdown()` (3.13+) or sentinels for teardown.
- `concurrent.futures` — one `Executor` API across threads (I/O-bound), processes (CPU-bound), and subinterpreters (`InterpreterPoolExecutor`, 3.14+); `as_completed` streams results as they finish.
- `concurrent.interpreters` (3.14+) — isolated interpreters for CSP-style parallelism without multiprocessing's serialization overhead.
- `selectors` — readiness-based I/O multiplexing, the primitive event loops are built from — for when you need a custom loop, not before.

### 1.2 Resource lifecycle and graceful shutdown

- `contextlib.ExitStack` / `AsyncExitStack` — compose N resources acquired conditionally or in a loop; `pop_all()` transfers ownership. The pattern behind framework lifespans and connection pools.
- `@contextmanager` / `@asynccontextmanager` — package setup/teardown as a reusable object instead of copy-pasted try/finally.
- `weakref.finalize` — cleanup that reliably runs at GC or interpreter exit; strictly better than `__del__`. `WeakValueDictionary` for caches that don't block collection.
- `signal` + `atexit` — services trap `SIGTERM` to flush and close cleanly; handlers should set an event, not do work (they run in the main thread between bytecodes).

### 1.3 Plugin and extension machinery

- `importlib.metadata` — entry points are the stdlib plugin-discovery mechanism (how pytest and ruff find plugins): third parties register in their `pyproject.toml`, you call `entry_points(group="myapp.plugins")` (group filter 3.10+). No plugin framework needed.
- `importlib.resources` — `files(pkg) / "data.json"` reads data shipped inside a package and survives zip/wheel installs; `os.path.join(os.path.dirname(__file__), ...)` does not.
- `functools.singledispatch` / `singledispatchmethod` — type-driven dispatch that external code can extend with `@register`; replaces growing `isinstance` chains with open extension.
- `typing.Protocol` (+ `@runtime_checkable`) — structural interfaces without inheritance coupling; the right contract type for plugin APIs.
- `__init_subclass__` — self-registering subclasses (handler registries) without metaclass machinery.
- `@warnings.deprecated` (3.13+, PEP 702) — deprecate APIs with one decorator: runtime warning + type-checker signal together.

### 1.4 Introspection and runtime instrumentation

- `inspect.signature` — the foundation for DI containers, CLI generators, and validating decorators; `inspect.iscoroutinefunction` before awaiting user callbacks.
- `ast` — parse/analyze/transform Python source; `ast.literal_eval` for literal config (never `eval`).
- `annotationlib` (3.14+) — the only correct way to read annotations under deferred evaluation (PEP 649); raw `__annotations__` access breaks on forward references.
- `sys.monitoring` (3.12+) — low-overhead per-event instrumentation for coverage/profiling/tracing tools, without `sys.settrace`'s cost.

### 1.5 Binary data and zero-copy

- `memoryview` — slice buffers without copying (a slice is a view, not a copy); the difference between O(n) and O(n²) when carving network frames. `.cast()` reinterprets layout.
- `struct` — declarative binary pack/unpack for protocols and file formats; `Struct` objects precompile the format string.
- `mmap` — random access into huge files without reading them; share pages between processes.
- `array` — compact typed numeric storage where `numpy` would be a dependency for nothing.
- `multiprocessing.shared_memory` — zero-copy data sharing across processes.

### 1.6 sqlite3 as an application backbone

- Beyond CRUD: WAL mode (`PRAGMA journal_mode=WAL`) for concurrent readers, `backup()` for hot copies, `create_function(deterministic=True)` for UDFs, FTS5 full-text search, JSON functions, `executemany`, row factories. Frequently sufficient where "we need redis / a real DB" is assumed. **Caveat:** compiled features (FTS5, JSON1, loadable extensions) vary by build — check `PRAGMA compile_options` at runtime.
- `dbm.sqlite3` (3.13+) / `shelve` — a persistent key-value store in two lines when even SQL is too much.

### 1.7 Injection-safe text assembly

- `string.templatelib` (3.14+, PEP 750 t-strings) — `t"SELECT … {user_input}"` yields a `Template` whose _consumer_ controls escaping; the foundation for building safe SQL/HTML/shell APIs.
- `string.Template` — for **user-supplied** templates: `$name`-only substitution. Never feed user templates to `.format()` — `"{0.__class__}"`-style field access traverses attributes and leaks internals.

### 1.8 Observability and production diagnostics

- `logging` architecture — `QueueHandler`/`QueueListener` make logging non-blocking (essential under async); `dictConfig` for declarative setup; filters/`LoggerAdapter` inject request context (pair with `contextvars`).
- `faulthandler` — `enable()` at service start prints tracebacks on segfault/deadlock; `dump_traceback_later()` doubles as a hang watchdog.
- `tracemalloc` — snapshot diffs attribute memory growth to file:line; the answer to "where is the leak" without a profiler dependency.
- `traceback.TracebackException` — captures exception data without holding frames, for rendering later or elsewhere (error reporters).

---

## 2. Everyday patterns, written completely

Code that gets written constantly; each entry is the delta between "works on my machine" and correct. Format: habit → upgrade.

### 2.1 Files and paths

- `open(p)` → `open(p, encoding="utf-8")` — the default encoding is platform-dependent (Windows ≠ UTF-8) until UTF-8 becomes the default (PEP 686, accepted for 3.15).
- CSV file handles → `open(p, newline="")` — required by the `csv` docs; omitting it corrupts rows on Windows.
- "Write then rename" → write a temp file **in the same directory**, then `os.replace(tmp, dst)` — atomic on the same filesystem; readers never observe partial writes.
- `NamedTemporaryFile()` on Windows cannot be reopened while open — `delete_on_close=False` (3.12+) or use `TemporaryDirectory`.
- Shelling out to `which` → `shutil.which("exe")`.
- Manual recursive walks → `Path.walk()` (3.12+) or `os.scandir` (`DirEntry` caches stat results — much faster than `listdir` + `stat`).

### 2.2 Text

- `s.strip(".txt")` → `s.removesuffix(".txt")` (3.9+) — `strip` removes a **character set**, a classic silent bug.
- Caseless comparison → `s.casefold()`, not `.lower()` (handles ß→ss and friends).
- Comparing or deduping user text → `unicodedata.normalize("NFC", s)` first; visually identical strings can differ by code points.

### 2.3 Time and datetime

- `datetime.utcnow()` (deprecated 3.12, returns **naive**) → `datetime.now(UTC)` (`UTC` alias 3.11+, else `timezone.utc`).
- Durations via `time.time()` → `time.perf_counter()`; deadlines/timeouts → `time.monotonic()`. Wall clock jumps (NTP, DST) — use it only for timestamps.
- Local-time arithmetic across DST → do arithmetic in UTC, render via `zoneinfo` (mind `fold` for ambiguous times).

### 2.4 Subprocess

- Canonical call: `subprocess.run(argv_list, check=True, capture_output=True, text=True, timeout=N)`. On failure `CalledProcessError.stderr` holds the actual error — log it, not just the exit code.
- String command + `shell=True` → list argv. If a shell is truly unavoidable, build the string with `shlex.quote`/`shlex.join`.

### 2.5 Logging

- Module top: `logger = logging.getLogger(__name__)`; configure (`basicConfig`/`dictConfig`) **only** in the entry point — libraries never configure.
- `logger.info(f"x={x}")` → `logger.info("x=%s", x)` — lazy formatting skips the work when the level is off.
- Inside `except`: `logger.exception("context")` — captures the traceback automatically.

### 2.6 Errors, exits, and CLI behavior

- Re-raising as a new type → `raise AppError(...) from e` (keep the cause) or `from None` (deliberately suppress it).
- `try/except/pass` → `contextlib.suppress(FileNotFoundError)` — scoped and self-documenting.
- Around `TaskGroup` (3.11+) → `except*` — failures arrive as `ExceptionGroup`, a bare `except ValueError` won't match.
- CLI entry: `sys.exit(main())` with `main() -> int`; `KeyboardInterrupt` → exit 130; catch `BrokenPipeError` so `mycli | head` doesn't stack-trace.
- Boolean flags → `argparse.BooleanOptionalAction` (3.9+) gives `--flag/--no-flag` pairs for free; prompt for secrets with `getpass.getpass` (no echo).

### 2.7 Iteration and collections

- Parallel iteration where lengths must match → `zip(a, b, strict=True)` (3.10+) — silent truncation is a data-loss bug.
- Hand-rolled chunking loop → `itertools.batched(it, n)` (3.12+); `zip(xs, xs[1:])` → `itertools.pairwise` (3.10+, works on lazy iterators too).
- `itertools.groupby` requires sorted input — sort by the same key first or groups fragment.
- `sorted(xs, key=lambda x: x[1])` → `key=operator.itemgetter(1)` / `attrgetter("name")` for plain field access.
- `functools.lru_cache` on a **method** pins every `self` forever — use `functools.cached_property`, or cache a module-level function keyed by arguments.

### 2.8 Data modeling defaults

- `@dataclass` → choose `@dataclass(slots=True, frozen=True, kw_only=True)` (3.10+) deliberately: slots = smaller + faster attribute access, frozen = hashable value object, kw_only = readable call sites. Mutable defaults via `field(default_factory=list)`.
- Non-destructive updates → `dataclasses.replace(obj, x=1)`; generic `copy.replace()` protocol (3.13+).
- String constants that serialize to JSON/DB → `enum.StrEnum` (3.11+); bit flags → `enum.Flag`.
- Exposing internal dicts read-only → `types.MappingProxyType(d)`.
- Overriding a base method → mark it `@typing.override` (3.12+) so renames fail the type check instead of silently forking behavior.

### 2.9 Randomness, hashing, and security hygiene

- Tokens/keys/OTPs → `secrets.token_urlsafe()/token_hex()/choice()` — `random` is predictable by design. Reproducible runs → a seeded `random.Random(seed)` instance, not the global `random.seed`.
- Comparing secrets → `hmac.compare_digest` (timing-safe), never `==`.
- Hashing a file → `hashlib.file_digest(f, "sha256")` (3.11+). Non-security fingerprints → `md5(data, usedforsecurity=False)` (3.9+, FIPS-safe).
- TLS → start from `ssl.create_default_context()` (verification on by default); never hand-assemble an `SSLContext`.
- Untrusted tar archives → `extractall(filter="data")` (3.12+; the default only from 3.14). Untrusted XML → hardened third-party parser; stdlib `xml.*` is not XXE-safe. Untrusted pickles → never.
- Parsing "Python-ish" config values → `ast.literal_eval`, never `eval`.

### 2.10 Test doubles (runtime side)

- Env-dependent code → `unittest.mock.patch.dict(os.environ, {...})`; interfaces → `patch(..., autospec=True)` so drifted signatures fail loudly; async collaborators → `AsyncMock`. (The test _runner_ is a dev-tooling choice — follow the project.)

---

## 3. Hidden power tools

Single capabilities that replace a dependency or a page of hand-rolled code.

### Algorithms and data

- `graphlib.TopologicalSorter` (3.9+) — dependency ordering + cycle detection; `prepare()/get_ready()/done()` drives **parallel** scheduling of a dependency graph, `static_order()` for the simple case.
- `heapq.merge(*sorted_iters, key=)` — k-way merge of sorted streams in constant memory; `nlargest(k, xs, key=)` beats a full sort for small k.
- `bisect` (+ `key=` 3.10+) — O(log n) lookups in sorted data; threshold tables (grade cutoffs, tiers) without an if-ladder; `insort` for bounded leaderboards.
- `collections.ChainMap` — layered lookup for CLI args > env > defaults without merging dicts (writes go to the first layer only).
- `collections.deque(maxlen=n)` — O(1) ring buffer for "last n events".
- `difflib` — `get_close_matches()` for "did you mean…" and fuzzy key matching; `unified_diff()` for readable expected-vs-actual in error messages; `SequenceMatcher.ratio()` for similarity scores.

### Numbers and statistics

- `statistics.NormalDist` — z-scores, CDF, confidence intervals, distribution overlap — no scipy for basic inference. Also `quantiles`, `correlation`, `linear_regression` (3.10+), `fmean(weights=)` (3.11+).
- `math.isclose` — the correct float comparison (never `==`); `math.sumprod` (3.12+) for precise dot products.
- `fractions.Fraction` — exact ratio arithmetic; `.limit_denominator()` turns 0.333… back into 1/3. `decimal` — money.

### Files, archives, text

- `zipfile.Path` — pathlib-style reads **inside** an archive, no extraction.
- `fileinput` — stream many files as one; `inplace=True` gives sed-style in-place editing.
- `textwrap` — `dedent` (clean triple-quoted strings), `shorten` (truncate on word boundaries), `fill`.
- `reprlib.repr` — bounded repr of huge structures for log lines; `@recursive_repr` for self-referential objects.
- Accent stripping — `unicodedata.normalize("NFKD", s)` then drop combining characters; no `unidecode` needed for the basic case.

### Network, IDs, protocols

- `ipaddress` — `addr in network`, subnet/supernet math, `is_private`/`is_global` — replaces hand-rolled CIDR string logic.
- `uuid.uuid7()` (3.14+) — time-ordered, index-friendly IDs; replaces the `uuid6`/`uuid7` PyPI packages.
- `email.message.EmailMessage` — modern MIME building (attachments included) without the legacy `email.mime.*` class dance; pairs with `smtplib`.
- `http.server.ThreadingHTTPServer` + a small handler — a stub HTTP API for tests in ~15 lines, no framework (dev use only, never production).
- `socketserver.ThreadingTCPServer` — a threaded TCP service from just a handler class.

### Debugging and the `python -m` toolbox

- `breakpoint()` — respects `PYTHONBREAKPOINT` (`=0` disables; or point it at another debugger). `pdb` attaches to a **running process**: `python -m pdb -p PID` (3.14+).
- `ctypes` — call an existing C shared library without compiling anything — check before `cffi` or writing an extension (C API: `https://docs.python.org/3.X/c-api/index.html`).
- One-liners: `python -m http.server` (static files), `-m json.tool` (pretty-print; color 3.14), `-m zipfile` / `-m tarfile` (create/extract), `-m timeit` (micro-bench), `-m calendar`, `-m uuid` (3.12+), `-m sqlite3` (3.12+ interactive shell), `-m asyncio ps PID` / `pstree` (3.14+ live task dump), `-m pydoc -b` (browsable local docs).
