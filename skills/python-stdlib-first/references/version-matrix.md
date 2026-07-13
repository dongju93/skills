# Version Matrix: Python 3.9 → 3.14

Per-version stdlib additions, removals, and codegen-relevant changes. Full details: `https://docs.python.org/3/whatsnew/3.X.html`.

**Rule of thumb:** before using any module or API tagged with a version in `stdlib-index.md`, confirm the target version here. Before targeting 3.12+, confirm the code uses none of the removed modules listed below.

## Quick availability table (frequently misjudged items)

| Feature                                                                                                                                                                                                                                                         | Minimum version |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| `zoneinfo`, `graphlib`, `functools.cache`, `str.removeprefix/removesuffix`, dict `\|` merge, `asyncio.to_thread`                                                                                                                                                | 3.9             |
| `match` statement, `itertools.pairwise`, `bisect(..., key=)`, `dataclasses(slots=, kw_only=)`, `zip(strict=True)`, `int \| None` union syntax, `statistics.linear_regression`                                                                                   | 3.10            |
| `tomllib`, `asyncio.TaskGroup`, `asyncio.timeout`, `ExceptionGroup`/`except*`, `typing.Self`, `StrEnum`, `datetime.UTC`, expanded `fromisoformat` (not every ISO 8601 form), `hashlib.file_digest`, `contextlib.chdir`                                          | 3.11            |
| `itertools.batched`, `pathlib.Path.walk`, PEP 695 generics (`class Foo[T]`, `type X = ...`), f-string nesting freedom (PEP 701), `typing.override`, tarfile `filter=`, `sqlite3.Connection.autocommit`                                                          | 3.12            |
| `copy.replace`, `dbm.sqlite3`, `PythonFinalizationError`, `base64.z85encode`, experimental free-threading/JIT                                                                                                                                                   | 3.13            |
| `compression.zstd`, `annotationlib`, `concurrent.interpreters`, `string.templatelib` (t-strings), `uuid.uuid7` (v6–v8), `pathlib.Path.copy/move`, `InterpreterPoolExecutor`, deferred annotations by default (PEP 649/749), free-threading officially supported | 3.14            |

## 3.9 (Oct 2020 — EOL Oct 2025)

- **Added modules:** `zoneinfo` (PEP 615), `graphlib`.
- Notable: dict `|`/`|=`, `str.removeprefix`/`removesuffix`, generics in builtins (`list[int]`, PEP 585), `functools.cache`, `math.lcm`/`nextafter`/`ulp`, `random.randbytes`, `asyncio.to_thread`.
- Removed: none relevant.

## 3.10 (Oct 2021)

- **Added modules:** none. `sys.stdlib_module_names` added (programmatic stdlib listing).
- Notable: structural pattern matching (`match`/`case`), `X | Y` union syntax (PEP 604), parenthesized context managers, `itertools.pairwise`, `bisect`/`insort` gain `key=`, `statistics.covariance`/`correlation`/`linear_regression`, `dataclasses` gains `slots=` and `kw_only=`, `zip(strict=)`, better error messages.

## 3.11 (Oct 2022)

- **Added modules:** `tomllib` (PEP 680, read-only TOML).
- **Removed:** `binhex`.
- Notable: 10–60% interpreter speedup; exception groups + `except*` (PEP 654); `asyncio.TaskGroup`, `asyncio.timeout`, `asyncio.Runner`, `asyncio.Barrier`; `typing.Self`, variadic generics (PEP 646), `Required`/`NotRequired`; `enum.StrEnum`; `datetime.UTC`; `fromisoformat` accepts more ISO 8601 forms than before 3.11 (still not every ISO 8601 variant — see datetime docs); `hashlib.file_digest`; `contextlib.chdir`; fine-grained error locations in tracebacks; `sys.exception()`.

## 3.12 (Oct 2023)

- **Removed modules:** `distutils` (PEP 632 — use `setuptools`/`packaging`), `asynchat`, `asyncore`, `imp`, `smtpd`.
- Notable: PEP 695 type-parameter syntax (`class Stack[T]:`, `type Alias = ...`); f-strings formalized (PEP 701 — nesting, multiline); `itertools.batched`; `pathlib.Path.walk`, `Path.relative_to(walk_up=True)`; `typing.override`; `tarfile` extraction filters (use `filter="data"` for untrusted archives; default changes to `"data"` in 3.14); `sqlite3` `autocommit`; per-interpreter GIL (C API, PEP 684); `sys.monitoring`.
- Deprecated: `datetime.utcnow()`/`utcfromtimestamp()` (use tz-aware `now(datetime.UTC)`).

## 3.13 (Oct 2024)

- **Removed modules (21 total):** 19 PEP 594 "dead batteries" — `aifc`, `audioop`, `cgi`, `cgitb`, `chunk`, `crypt`, `imghdr`, `mailcap`, `msilib`, `nis`, `nntplib`, `ossaudiodev`, `pipes`, `sndhdr`, `spwd`, `sunau`, `telnetlib`, `uu`, `xdrlib` — plus `lib2to3` and `tkinter.tix`.
  - Common migration targets: `cgi` → `urllib.parse`/`email.message`; `telnetlib` → `socket` or third-party `telnetlib3`; `imghdr` → `filetype`/`puremagic` (PyPI); `pipes` → `shlex`; `crypt` → `hashlib`/`bcrypt` (stdlib has no general encryption).
- **Added:** `dbm.sqlite3` (new default dbm backend).
- Notable: new interactive REPL; `copy.replace()`; `base64.z85encode`/`z85decode`; experimental free-threaded build (PEP 703) and JIT (PEP 744); `typing.ReadOnly`, `TypeIs`; `pathlib.Path.full_match`, `Path.from_uri`; `random` CLI; `locale.resetlocale` removed; `typing.io`/`typing.re` namespaces removed.

## 3.14 (Oct 2025)

- **Added modules:** `compression.zstd` (PEP 784, Zstandard; `compression.*` namespace aliases gzip/bz2/lzma/zlib), `annotationlib` (PEP 749), `concurrent.interpreters` (PEP 734), `string.templatelib` (PEP 750 t-strings).
- Notable:
  - Deferred annotation evaluation by default (PEP 649/749) — introspect via `annotationlib.get_annotations()`; `from __future__ import annotations` still honored.
  - `uuid`: v6/v7/v8 generation (`uuid.uuid7()` for time-ordered DB-friendly IDs, RFC 9562); v3–v5 up to 40% faster.
  - `concurrent.futures.InterpreterPoolExecutor`; free-threaded build officially supported (PEP 779).
  - `pathlib.Path.copy()`/`copy_into()`/`move()`/`move_into()`.
  - `pdb` remote attach (`python -m pdb -p PID`); `python -m asyncio ps/pstree` task introspection; safe external debugger interface (PEP 768).
  - `argparse` color + suggestions; color in `unittest`/`json`/`calendar` CLIs; syntax-highlighted REPL.
  - `except`/`except*` may omit parentheses for multiple exception types without `as` (PEP 758); control flow that exits a `finally` via `return`/`break`/`continue` emits a `SyntaxWarning` (PEP 765) — it is not a hard syntax error in 3.14; avoid the pattern, do not claim it is banned.
  - `multiprocessing`: default start method on Linux is no longer `fork` (now `forkserver`) — code relying on fork-inherited state must set it explicitly.
  - tarfile extraction `filter=` defaults to `"data"`.
- Removed: no widely-used stdlib modules removed (PEP 594 cleanup completed in 3.13).

## Choosing a floor version

- Library code: support the oldest non-EOL CPython unless there is a reason not to (as of mid-2026: 3.10+; 3.9 reached EOL Oct 2025).
- Application code: pin to the deployed interpreter; verify with `requires-python` and lockfiles.
- If a wanted stdlib feature is above the floor (e.g., `tomllib` on 3.10), either raise the floor deliberately or use the documented backport (`tomli`) behind a version guard — do not silently vendor.

## Local verification (offline)

When docs cannot be fetched, confirm availability against a target-version interpreter:

```bash
uv run --python 3.12 python -c "import tomllib"
uv run --python 3.12 python -m pydoc zoneinfo
uv run --python 3.12 python -c "import sys; print('tomllib' in sys.stdlib_module_names)"
```

`sys.stdlib_module_names` (3.10+) is the definitive programmatic list for that interpreter.
