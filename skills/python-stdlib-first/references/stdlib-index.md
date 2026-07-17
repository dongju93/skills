# Standard Library Index (Python 3.10–3.14)

**Curated by value-add, not by domain.** A competent developer — or model — already reaches for `json`, `re`, `pathlib`, `collections`, and `argparse` unprompted, so those earn no entries here. Every entry below is a _delta_: something that changes the output compared to the habitual version.

Pick the section that matches the task:

| Task shape                                                              | Read                                    |
| ----------------------------------------------------------------------- | --------------------------------------- |
| Designing something advanced (service, framework, pipeline, plugin API) | §1                                      |
| Writing or reviewing everyday code (files, subprocess, logging, time)   | §2                                      |
| "Is there a built-in for X?" / replacing a dependency                   | §3 + the substitution table in SKILL.md |

One-line summaries only — fetch `https://docs.python.org/3.X/library/{module}.html` for exact APIs. Version tags like `(3.11+)` mean "added in that version"; untagged items exist across 3.10–3.14 (3.10 is the supported floor, so features present in it carry no tag). If nothing here matches: the official module index `https://docs.python.org/3.X/py-modindex.html`, or locally `python -c "import sys; print(sorted(sys.stdlib_module_names))"`.

---

## 1. Foundations — primitives to build advanced features on

Read when architecting. Load-bearing building blocks that replace a framework or a hand-rolled subsystem.

### 1.1 Structured concurrency and async correctness

- `asyncio.TaskGroup` (3.11+) — owned task lifetimes: the first non-cancellation failure cancels siblings and non-cancellation failures surface as an `ExceptionGroup` (handle with `except*`). Prefer it for related tasks with shared lifetime and fail-together semantics; keep `gather` when ordered aggregate results or independent-failure semantics are intentional. For detached `create_task` work, retain a strong reference — the event loop keeps only weak references.
- `asyncio.timeout` (3.11+) — cancellation-correct deadlines around a block of awaits; `wait_for` remains appropriate when the timeout belongs to one awaitable.
- `contextvars` — request-scoped state that survives `await` (correlation IDs, auth context). Coroutines on one event-loop thread share `threading.local`; use `contextvars` when state must follow each task independently.
- `asyncio.to_thread` — the one-line bridge for blocking calls inside async code; a blocking call in a coroutine stalls the whole event loop.
- `queue.Queue` / `asyncio.Queue` — producer/consumer backbone: `task_done()`/`join()` for completion, `Queue.shutdown()` (3.13+) or sentinels for teardown.
- `concurrent.futures` — one `Executor` API across threads (I/O-bound), processes (CPU-bound), and subinterpreters (`InterpreterPoolExecutor`, 3.14+); `as_completed` streams results as they finish.
- `concurrent.interpreters` (3.14+) — isolated interpreters for true multicore parallelism in one process. Mutable state is not shared; design data transfer explicitly and verify third-party extension compatibility.
- `selectors` — readiness-based I/O multiplexing, the primitive event loops are built from — for when you need a custom loop, not before.

### 1.2 Resource lifecycle and graceful shutdown

- `contextlib.ExitStack` / `AsyncExitStack` — compose N resources acquired conditionally or in a loop; `pop_all()` transfers ownership. The pattern behind framework lifespans and connection pools.
- `@contextmanager` / `@asynccontextmanager` — package setup/teardown as a reusable object instead of copy-pasted try/finally.
- `weakref.finalize` — decouple cleanup from `__del__`; it runs when the object is collected or, while still alive with `atexit=True`, at normal interpreter exit. Prefer explicit `close()`/context managers when cleanup timing matters. `WeakValueDictionary` builds caches that do not keep values alive.
- `signal` + `atexit` — services trap `SIGTERM` to flush and close cleanly; handlers should set an event, not do work (they run in the main thread between bytecodes).

### 1.3 Plugin and extension machinery

- `importlib.metadata` — entry points are the stdlib plugin-discovery mechanism used by pytest and many plugin hosts: third parties register in their `pyproject.toml`, you call `entry_points(group="myapp.plugins")`. No plugin framework needed.
- `importlib.resources` — `files(pkg) / "data.json"` reads data shipped inside a package and survives zip/wheel installs; `os.path.join(os.path.dirname(__file__), ...)` does not.
- `functools.singledispatch` / `singledispatchmethod` — type-driven dispatch that external code can extend with `@register`; replaces growing `isinstance` chains with open extension.
- `typing.Protocol` (+ `@runtime_checkable`) — structural interfaces without inheritance coupling; the right contract type for plugin APIs.
- `__init_subclass__` — self-registering subclasses (handler registries) without metaclass machinery.
- `@warnings.deprecated` (3.13+, PEP 702) — deprecate APIs with one decorator: runtime warning + type-checker signal together.

### 1.4 Introspection and runtime instrumentation

- `inspect.signature` — the foundation for DI containers, CLI generators, and validating decorators; `inspect.iscoroutinefunction` before awaiting user callbacks.
- `ast` — parse/analyze/transform Python source; `ast.literal_eval` handles trusted, bounded literal data without code execution, but is not safe against resource-exhaustion input (see §2.9).
- `annotationlib` (3.14+) — use `get_annotations()` for low-level deferred-annotation introspection and selectable value/forward-reference/string formats; use `typing.get_type_hints()` when resolved, inherited type hints are wanted. Avoid raw `__annotations__` in cross-version tooling, and remember that evaluating annotations can execute code.
- `sys.monitoring` (3.12+) — low-overhead per-event instrumentation for coverage/profiling/tracing tools, without `sys.settrace`'s cost.

### 1.5 Binary data and zero-copy

- `memoryview` — slice buffers without copying (a slice is a view, not a copy); the difference between O(n) and O(n²) when carving network frames. `.cast()` reinterprets layout.
- `struct` — declarative binary pack/unpack for protocols and file formats; `Struct` objects precompile the format string.
- `mmap` — random access into huge files without reading them; share pages between processes.
- `array` — compact typed numeric storage when the requirement is storage and buffer interoperability rather than NumPy's vectorized computation.
- `multiprocessing.shared_memory` — zero-copy data sharing across processes.

### 1.6 sqlite3 as an application backbone

- Beyond CRUD: WAL mode (`PRAGMA journal_mode=WAL`) for concurrent readers, `backup()` for hot copies, `create_function(deterministic=True)` for UDFs, FTS5 full-text search, JSON functions, `executemany`, row factories. Frequently sufficient when an embedded deployment and its write-concurrency limits fit. **Caveat:** compiled features (FTS5, JSON1, loadable extensions) vary by build — check `PRAGMA compile_options` at runtime.
- `dbm.sqlite3` (3.13+) / `shelve` — a persistent key-value store in two lines when even SQL is too much.

### 1.7 Injection-safe text assembly

- `string.templatelib` (3.14+, PEP 750 t-strings) — `t"SELECT … {user_input}"` preserves static and interpolated parts for a consumer to process. The `Template` does not escape values by itself; the consumer must apply context-specific parameterization or escaping for SQL/HTML/shell use.
- `string.Template` — for **user-supplied** templates: `$name`-only substitution. Never feed user templates to `.format()` — `"{0.__class__}"`-style field access traverses attributes and leaks internals.

### 1.8 Observability and production diagnostics

- `logging` architecture — `QueueHandler`/`QueueListener` move slow handler work off an event-loop or request thread when logging I/O can block; `dictConfig` for declarative setup; filters/`LoggerAdapter` inject request context (pair with `contextvars`).
- `faulthandler` — `enable()` installs traceback handlers for fatal signals; `dump_traceback_later()` uses a watchdog thread to capture hangs or suspected deadlocks after a timeout.
- `tracemalloc` — snapshot diffs attribute memory growth to file:line; the answer to "where is the leak" without a profiler dependency.
- `traceback.TracebackException` — captures exception data without holding frames, for rendering later or elsewhere (error reporters).

---

## 2. Everyday patterns, written completely

Code that gets written constantly; each entry is the delta between "works on my machine" and correct. Format: habit → upgrade.

### 2.1 Files and paths

- Application-owned UTF-8 text → `open(p, encoding="utf-8")`; external formats → use their specified encoding. Relying on the platform default is non-portable before UTF-8 mode becomes the default (PEP 686, Python 3.15).
- CSV file handles → `open(p, newline="")` — required by the `csv` docs; omitting it corrupts rows on Windows.
- "Write then rename" → write a temp file **in the same directory**, then `os.replace(tmp, dst)` — if the replace succeeds, visibility is atomic on the same filesystem. This does not guarantee crash durability; flush and `fsync` when durability is required.
- Reopening a live `NamedTemporaryFile` always works on POSIX; on Windows use `delete=False`, share delete access, or set `delete_on_close=False` (3.12+) and close additional handles before context exit.
- Shelling out to `which` → `shutil.which("exe")`.
- Manual recursive walks → `Path.walk()` (3.12+) or `os.scandir` (`DirEntry` caches stat results — much faster than `listdir` + `stat`).

### 2.2 Text

- `s.strip(".txt")` → `s.removesuffix(".txt")` — `strip` removes a **character set**, a classic silent bug.
- Caseless comparison → `s.casefold()`, not `.lower()` (handles ß→ss and friends).
- Comparing or deduping user text → `unicodedata.normalize("NFC", s)` first; visually identical strings can differ by code points.

### 2.3 Time and datetime

- `datetime.utcnow()` (deprecated 3.12, returns **naive**) → `datetime.now(UTC)` (`UTC` alias 3.11+, else `timezone.utc`).
- Durations via `time.time()` → `time.perf_counter()`; deadlines/timeouts → `time.monotonic()`. Wall clock jumps (NTP, DST) — use it only for timestamps.
- Local-time arithmetic across DST → do arithmetic in UTC, render via `zoneinfo` (mind `fold` for ambiguous times).

### 2.4 Subprocess

- Robust baseline for bounded, non-interactive text commands: `subprocess.run(argv_list, check=True, capture_output=True, text=True, timeout=N)`. Choose streaming, binary mode, or `Popen` when the command's I/O contract requires it. On failure `CalledProcessError.stderr` holds captured stderr — report it, not just the exit code.
- String command + `shell=True` → list argv with `shell=False`. If a shell is truly unavoidable, keep the command structure fixed and quote dynamic tokens for that specific shell; `shlex.quote`/`shlex.join` target Unix shells and are not a Windows-shell sanitizer.

### 2.5 Logging

- Module top: `logger = logging.getLogger(__name__)`; let the application entry point own root handlers and levels. Libraries should not configure global logging, though they may attach a `NullHandler` when appropriate.
- `logger.info(f"x={x}")` → `logger.info("x=%s", x)` — lazy formatting skips the work when the level is off.
- Inside `except`: `logger.exception("context")` — captures the traceback automatically.

### 2.6 Errors, exits, and CLI behavior

- Re-raising as a new type → `raise AppError(...) from e` (keep the cause) or `from None` (deliberately suppress it).
- `try/except/pass` → `contextlib.suppress(FileNotFoundError)` — scoped and self-documenting.
- Around `TaskGroup` (3.11+) → `except*` — failures arrive as `ExceptionGroup`, a bare `except ValueError` won't match.
- CLI entry: `sys.exit(main())` with `main() -> int`; if handling `KeyboardInterrupt`, exit 130; handle `BrokenPipeError` deliberately so `mycli | head` does not emit a traceback.
- Boolean flags → `argparse.BooleanOptionalAction` gives `--flag/--no-flag` pairs for free; prompt for secrets with `getpass.getpass` (no echo).

### 2.7 Iteration and collections

- Parallel iteration where lengths must match → `zip(a, b, strict=True)` — silent truncation is a data-loss bug.
- Hand-rolled chunking loop → `itertools.batched(it, n)` (3.12+); `zip(xs, xs[1:])` → `itertools.pairwise` (works on lazy iterators too).
- `itertools.groupby` groups adjacent equal keys; sort by the same key first only when one consolidated group per key is required.
- `sorted(xs, key=lambda x: x[1])` → `key=operator.itemgetter(1)` / `attrgetter("name")` for plain field access.
- `functools.lru_cache` on a **method** includes `self` in the cache key and keeps cached instances alive until eviction or `cache_clear()`. Use `cached_property` for an argument-free per-instance computation, or cache a module-level function keyed by immutable data.

### 2.8 Data modeling defaults

- Choose dataclass options independently: `slots=True` when dynamic attributes and ordinary weak references are unnecessary (`weakref_slot=True` adds weak-reference support); `frozen=True` prevents normal assignment but does not make nested values immutable, and generated hashes still require hashable compared fields; `kw_only=True` when call-site clarity outweighs positional ergonomics. Mutable defaults use `field(default_factory=list)`.
- Non-destructive updates → `dataclasses.replace(obj, x=1)`; generic `copy.replace()` protocol (3.13+).
- String constants that serialize to JSON/DB → `enum.StrEnum` (3.11+); bit flags → `enum.Flag`.
- Exposing internal dicts read-only → `types.MappingProxyType(d)`; it is a live view, so copy the mapping first when callers need an immutable snapshot.
- Overriding a base method → mark it `@typing.override` (3.12+) so renames fail the type check instead of silently forking behavior.

### 2.9 Randomness, hashing, and security hygiene

- Tokens/keys/OTPs → `secrets.token_urlsafe()/token_hex()/choice()` — `random` is predictable by design. Reproducible runs → a seeded `random.Random(seed)` instance, not the global `random.seed`.
- Comparing secrets → `hmac.compare_digest` (timing-safe), never `==`.
- Hashing a file → `hashlib.file_digest(f, "sha256")` (3.11+). A non-security fingerprint may use `md5(data, usedforsecurity=False)`; the flag states intent and can permit blocked algorithms, but availability still depends on the Python build and security policy.
- TLS → start from `ssl.create_default_context()` (verification on by default), then customize only the settings the protocol requires. Do not disable certificate or hostname verification merely to make a failing connection succeed.
- Untrusted tar archives → `extractall(filter="data")` (3.12+; the default only from 3.14). Treat stdlib `xml.*` as non-hardened for hostile input and use a hardened third-party parser. Never unpickle untrusted data.
- Parsing trusted, bounded "Python-ish" literal values → `ast.literal_eval`, never `eval`. It avoids code execution but is not resource-safe for arbitrary untrusted input; prefer a typed format parser and input limits at trust boundaries.

### 2.10 Test doubles (runtime side)

- Env-dependent code → `unittest.mock.patch.dict(os.environ, {...})`; interfaces → `patch(..., autospec=True)` so drifted signatures fail loudly; async collaborators → `AsyncMock`. (The test _runner_ is a dev-tooling choice — follow the project.)

---

## 3. Hidden power tools

Single capabilities that replace a dependency or a page of hand-rolled code.

### Algorithms and data

- `graphlib.TopologicalSorter` — dependency ordering + cycle detection; `prepare()/get_ready()/done()` drives **parallel** scheduling of a dependency graph, `static_order()` for the simple case.
- `heapq.merge(*sorted_iters, key=)` — k-way merge of sorted streams in constant memory; `nlargest(k, xs, key=)` beats a full sort for small k.
- `bisect` (+ `key=`) — O(log n) lookups in sorted data; threshold tables (grade cutoffs, tiers) without an if-ladder; `insort` for bounded leaderboards.
- `collections.ChainMap` — layered lookup for CLI args > env > defaults without merging dicts (writes go to the first layer only).
- `collections.deque(maxlen=n)` — O(1) ring buffer for "last n events".
- `difflib` — `get_close_matches()` for "did you mean…" and fuzzy key matching; `unified_diff()` for readable expected-vs-actual in error messages; `SequenceMatcher.ratio()` for similarity scores.

### Numbers and statistics

- `statistics.NormalDist` — z-scores, CDF, confidence intervals, distribution overlap — no scipy for basic inference. Also `quantiles`, `correlation`, `linear_regression`, `fmean(weights=)` (3.11+).
- `math.isclose` — compare values expected to differ by floating-point error, with tolerances chosen for the domain; exact `==` remains correct when exact equality is the requirement. `math.sumprod` (3.12+) provides higher-accuracy dot products.
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
- `ctypes` — call a trusted shared library with a small, stable C ABI without compiling an extension. Declare signatures exactly: incorrect types or ownership can corrupt memory or crash the process. For richer bindings, callbacks, or generated interfaces, `cffi` or an extension may be the safer choice (C API: `https://docs.python.org/3.X/c-api/index.html`).
- One-liners: `python -m http.server` (static files), `-m json.tool` (pretty-print; color 3.14), `-m zipfile` / `-m tarfile` (create/extract), `-m timeit` (micro-bench), `-m calendar`, `-m uuid` (3.12+), `-m sqlite3` (3.12+ interactive shell), `-m asyncio ps PID` / `pstree` (3.14+ live task dump), `-m pydoc -b` (browsable local docs).
