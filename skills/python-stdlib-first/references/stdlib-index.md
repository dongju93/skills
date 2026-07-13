# Standard Library Index (Python 3.9–3.14)

**Curated shortlist**, not an exhaustive catalog. Use it to map common task capabilities to high-value or underused stdlib modules. One-line summaries only — fetch `https://docs.python.org/3.X/library/{module}.html` for exact APIs, or use local `pydoc` / import checks when offline. Version tags like `(3.11+)` mean "added in that version"; untagged items exist across 3.9–3.14.

If nothing here matches, fall back to:

- Official module name index: `https://docs.python.org/3.X/py-modindex.html`
- Library index: `https://docs.python.org/3.X/library/index.html`
- Local definitive list (3.10+): `python -c "import sys; print(sorted(sys.stdlib_module_names))"`

**Table of contents**

1. Text, encodings, and data formats
2. Data structures and algorithms
3. Functional tools and iteration
4. Numbers, math, and statistics
5. Dates and times
6. Files, paths, and filesystems
7. Persistence and databases
8. Compression and archiving
9. Cryptography and security
10. Concurrency and processes
11. Networking and internet data
12. CLI, terminal, and configuration
13. Testing, debugging, and profiling
14. Typing, introspection, and runtime
15. FFI and C API

---

## 1. Text, encodings, and data formats

- `string` — constants, `Template` ($-substitution); `string.templatelib` (3.14+) for t-string `Template`/`Interpolation` processing (PEP 750).
- `re` — regex; note `re.Match` supports `[]` group access; possessive quantifiers and atomic groups added in 3.11.
- `difflib` — diffs and **fuzzy matching**: `get_close_matches()`, `SequenceMatcher.ratio()` — replaces trivial uses of `thefuzz`/`rapidfuzz`.
- `textwrap` — `dedent`, `indent`, `shorten`, `fill` — replaces manual string-wrangling helpers.
- `unicodedata` — normalization (`NFC`/`NFKD`), category lookup — the correct tool for "strip accents" tasks.
- `json` — parsing/serialization; `object_hook`, `default=`, `json.tool` CLI (color output in 3.14).
- `csv` — `DictReader`/`DictWriter`, dialects, `Sniffer` for delimiter detection.
- `tomllib` (3.11+) — read-only TOML parsing. No writer in stdlib.
- `xml.etree.ElementTree` — parse/build XML, limited XPath; `iterparse` for streaming large docs. **Untrusted XML:** stdlib XML modules are not hardened against XXE/billion-laughs-class attacks — use a defused/hardened third-party parser for untrusted input (see [xml vulnerabilities](https://docs.python.org/3/library/xml.html#xml-vulnerabilities)).
- `html.parser`, `html` — event-driven HTML parsing; `html.escape`/`unescape`.
- `base64` — also z85 (3.13+); `binascii` — hex/CRC32; `struct` — binary (un)packing; `codecs` — incremental encoders/decoders.
- `email.message.EmailMessage` — modern MIME construction/parsing (use this, not the legacy `email.mime.*` classes, for new code).
- `mimetypes` — extension ↔ MIME type mapping.

## 2. Data structures and algorithms

- `collections` — `Counter` (with `most_common`, arithmetic), `defaultdict`, `deque` (O(1) ends, `maxlen` ring buffer), `ChainMap` (layered configs), `namedtuple`.
- `heapq` — priority queues, `nlargest`/`nsmallest`, `merge` for k-way merging of sorted inputs.
- `bisect` — binary search on sorted sequences; `key=` parameter (3.10+).
- `array` — compact typed numeric arrays — often enough where `numpy` is overkill.
- `graphlib` (3.9+) — `TopologicalSorter`: dependency ordering + cycle detection — replaces `networkx` for this single capability.
- `enum` — `Enum`, `IntEnum`, `Flag`, `auto`; `StrEnum` (3.11+); `@verify`, `@member` (3.11+).
- `dataclasses` — `field`, `__post_init__`, `slots=`/`kw_only=` (3.10+), `frozen=`, `asdict`/`astuple`, `replace`.
- `types` — `SimpleNamespace`, `MappingProxyType` (read-only dict views).
- `copy` — `deepcopy`; `copy.replace()` protocol (3.13+).
- `weakref` — caches that don't block GC: `WeakValueDictionary`, `finalize`.

## 3. Functional tools and iteration

- `itertools` — `chain`, `islice`, `groupby` (requires sorted input), `product`, `permutations`, `combinations`, `accumulate`, `takewhile`/`dropwhile`, `zip_longest`; `pairwise` (3.10+); **`batched`** (3.12+) — replaces hand-rolled chunking.
- `functools` — `lru_cache`, `cache` (3.9+), **`cached_property`**, `partial`, `reduce`, **`singledispatch`/`singledispatchmethod`** (type-based polymorphism without isinstance chains), `total_ordering`, `wraps`.
- `operator` — `itemgetter`/`attrgetter` (fast sort keys), `methodcaller`.
- `contextlib` — **`ExitStack`** (dynamic/conditional context management), `suppress`, `closing`, `redirect_stdout`, `nullcontext`, `chdir` (3.11+), `asynccontextmanager`.

## 4. Numbers, math, and statistics

- `math` — includes `isclose`, `prod`, `dist`, `lcm` (3.9+), `nextafter` (3.9+), `sumprod` (3.12+), `fma` (3.13+).
- `statistics` — `fmean`, `geometric_mean`, `median_grouped`, `quantiles`, `mode`/`multimode`; `covariance`, `correlation`, **`linear_regression`** (3.10+); **`NormalDist`** (z-scores, CDF, overlap) — replaces scipy for basic descriptive/inferential work.
- `decimal` — exact decimal arithmetic (money); `fractions` — rational numbers.
- `random` — `choices` (weighted), `sample`, `shuffle`, `Random(seed)` instances; `randbytes` (3.9+). Not for security — use `secrets`.

## 5. Dates and times

- `datetime` — `fromisoformat` (expanded ISO 8601 support in 3.11+; still **not** every ISO 8601 form — check the target-version docs before claiming full compliance), `timestamp`/`fromtimestamp`, `timedelta`; `datetime.UTC` alias (3.11+).
- `zoneinfo` (3.9+) — IANA time zones; prefer over `pytz` for new code. **Requires IANA data:** system tzdb and/or the `tzdata` package (especially on Windows). Existing `pytz`-heavy codebases may keep `pytz` for interop until migration is planned. DST-correct arithmetic with `fold`.
- `calendar` — month/week math, `isleap`; enhanced CLI + color (3.14).
- `time` — `monotonic` (elapsed-time measurement), `perf_counter` (benchmarking), `sleep`.

## 6. Files, paths, and filesystems

- `pathlib` — object paths: `glob`/`rglob`, `read_text`/`write_bytes`, `mkdir(parents=True, exist_ok=True)`; `walk()` (3.12+); `full_match()` (3.13+); `copy()`/`move()` (3.14+); `Path.from_uri` (3.13+).
- `shutil` — `copytree`, `rmtree`, `which`, `disk_usage`, `make_archive`/`unpack_archive`, `get_terminal_size`.
- `tempfile` — `TemporaryDirectory`, `NamedTemporaryFile` (mind Windows `delete=` semantics; `delete_on_close` 3.12+).
- `glob`/`fnmatch` — pattern matching (prefer `pathlib` equivalents in new code); `filecmp` — file/dir comparison.
- `fileinput` — line-by-line over multiple files with in-place edit support.
- `os` — env vars, `scandir` (fast dir walks with cached stat), process info; `os.path` for low-level path ops.
- `mmap` — memory-mapped file I/O for large-file random access.
- `stat` — mode-bit interpretation.

## 7. Persistence and databases

- `sqlite3` — full embedded SQL DB: transactions, `executemany`, row factories, `backup()`, user-defined functions (`create_function`, deterministic flag), FTS5 full-text search, JSON1 functions, `autocommit` attribute (3.12+). Frequently sufficient where a "real database" or `redis` feels like the default. **Portability:** features depend on how the linked SQLite was compiled (e.g. FTS5, JSON1, loadable extensions) — verify at runtime/`PRAGMA compile_options` before relying on them; see [SQLite compile options](https://www.sqlite.org/compile.html).
- `dbm` — key-value stores; `dbm.sqlite3` backend (3.13+).
- `shelve` — persistent dict of pickled objects.
- `pickle` — Python object serialization (never unpickle untrusted data).
- `configparser` — INI files.

## 8. Compression and archiving

- `zlib`, `gzip`, `bz2`, `lzma` — stream and one-shot compression.
- `compression.zstd` (3.14+) — Zstandard (PEP 784) — replaces the `zstandard` PyPI package. The `compression.*` namespace (3.14+) also aliases gzip/bz2/lzma/zlib.
- `zipfile` — read/write ZIP; **`zipfile.Path`** for pathlib-style access inside archives; CLI (`python -m zipfile`).
- `tarfile` — read/write tar; **extraction `filter=` (3.12+; required thinking for untrusted archives — use `filter="data"`)**.

## 9. Cryptography and security

- `hashlib` — SHA-2/SHA-3, BLAKE2, `scrypt`/`pbkdf2_hmac` (password hashing); **`file_digest`** (3.11+) for efficient file hashing.
- `hmac` — message authentication; `compare_digest` for timing-safe comparison.
- `secrets` — CSPRNG tokens: `token_hex`, `token_urlsafe`, `choice` — the correct module for tokens and security-sensitive random choices.
- `ssl` — TLS contexts; `ssl.create_default_context()` is the safe starting point.
- **No general encryption in stdlib:** no AES/RSA/JWT primitives. For encryption, digital signatures, or authenticated encryption, use a maintained third-party library such as `cryptography`. Never assemble crypto from `hashlib` + XOR or similar.

## 10. Concurrency and processes

- `subprocess` — `run(..., capture_output=True, text=True, check=True)` covers most needs; prefer list argv over `shell=True`; pair with `shlex.split`/`shlex.quote` when shell is unavoidable.
- `concurrent.futures` — `ThreadPoolExecutor` (I/O-bound), `ProcessPoolExecutor` (CPU-bound), `as_completed`, `wait`; `InterpreterPoolExecutor` (3.14+).
- `concurrent.interpreters` (3.14+) — isolated subinterpreters (PEP 734), CSP-style concurrency.
- `threading` — `Lock`/`RLock`/`Event`/`Condition`/`Barrier`, `Timer`, `local`.
- `multiprocessing` — shared memory (`shared_memory` 3.8+), `Manager`, pools. Note: default start method is no longer fork on Linux in 3.14.
- `queue` — thread-safe FIFO/LIFO/priority queues; `SimpleQueue`.
- `asyncio` — **`TaskGroup`** (3.11+, structured concurrency), **`asyncio.timeout`** (3.11+), `Runner` (3.11+), `to_thread` (3.9+), streams, subprocesses; introspection CLI `python -m asyncio ps/pstree` (3.14+).
- `sched` — simple event scheduler; `signal` — signal handlers, `SIGALRM` timeouts (Unix).
- `selectors` — high-level I/O multiplexing over `select`.
- `contextvars` — context-local state that is async-correct (unlike `threading.local`).

## 11. Networking and internet data

- `urllib.request` — HTTP(S) requests: GET/POST, headers, timeouts, proxies — sufficient for simple scripted calls; `urllib.parse` — URL parsing/quoting/query building (`urlencode`, `parse_qs`).
- `http.client` — lower-level HTTP; `http` — `HTTPStatus`/`HTTPMethod` enums.
- `http.server` — dev/static file server (`python -m http.server`), request-handler framework. Not for production.
- `socket` — TCP/UDP primitives; `create_connection`, `getaddrinfo`.
- `socketserver` — threaded/forking server framework (`ThreadingTCPServer`).
- `ipaddress` — IP/CIDR math: membership, subnetting, supernets — replaces hand-rolled CIDR logic.
- `uuid` — v1–v5; **v6–v8 including `uuid7()` (3.14+, RFC 9562)** — replaces `uuid6`/`uuid7` PyPI packages on 3.14+.
- `smtplib`, `imaplib`, `poplib` — mail protocols (pair with `email.message`).
- `xmlrpc`, `ftplib` — legacy protocols, still present through 3.14.

## 12. CLI, terminal, and configuration

- `argparse` — subcommands, groups, custom types, `BooleanOptionalAction`; color output + "did you mean" suggestions (3.14+).
- `shlex` — `split`, `quote`, `join` — safe shell-string handling.
- `getpass` — prompt without echo; `platform` — OS/interpreter info.
- `readline`/`rlcompleter` — interactive input editing (Unix); `curses` — TUI (Unix).
- `logging` — `dictConfig`, rotating handlers, `QueueHandler`/`QueueListener` (non-blocking logging); `logging.config`.
- `warnings` — deprecation plumbing; `atexit` — shutdown hooks.
- `webbrowser` — open URLs in the user's browser.

## 13. Testing, debugging, and profiling

- `unittest` — test framework; **`unittest.mock`** (`patch`, `MagicMock`, `AsyncMock`, autospec), `IsolatedAsyncioTestCase`. Note: choosing `pytest` (or another runner) is a **dev-tooling** decision — follow the project toolchain; stdlib-first does not require replacing an established test stack with `unittest`.
- `doctest` — executable examples in docstrings.
- `pdb` — debugger; **remote attach to a running process** (3.14+).
- `timeit` — micro-benchmarks; `cProfile`/`pstats` — profiling; `tracemalloc` — memory attribution; `faulthandler` — crash tracebacks.
- `traceback` — formatting/inspection of exceptions; `TracebackException` for structured handling.

## 14. Typing, introspection, and runtime

- `typing` — `Protocol`, `TypedDict`, `Literal`, `Self` (3.11+), `override` (3.12+), `TypeAliasType`; PEP 695 generics syntax (3.12+) reduces need for `TypeVar` boilerplate.
- `annotationlib` (3.14+) — inspect deferred annotations (PEP 649/749); use `get_annotations()` instead of raw `__annotations__` access on 3.14+.
- `inspect` — signatures, source, `iscoroutinefunction`, frame inspection.
- `dataclasses`, `abc` — see above; `abc.ABC` + `@abstractmethod` for interfaces (or prefer `typing.Protocol` for structural typing).
- `importlib.resources` — access data files inside packages (replaces `pkg_resources`); `importlib.metadata` — installed-package metadata/entry points (replaces `pkg_resources` here too).
- `ast` — parse/transform Python source; `ast.literal_eval` for safe literal parsing (never `eval`).
- `sys`, `sysconfig`, `gc`, `site` — interpreter internals and lifecycle.

## 15. FFI and C API

- `ctypes` — call shared libraries (C ABI) from pure Python without compiling anything — check before `cffi`.
- CPython C API — for extension modules: `https://docs.python.org/3.X/c-api/index.html`. Key entry points: stable ABI / limited API (`Py_LIMITED_API`), `PyObject` protocols, GIL management (`Py_BEGIN_ALLOW_THREADS`). On 3.12+ note per-interpreter GIL isolation (PEP 684); on 3.13+/3.14 note free-threaded build implications for extensions.
