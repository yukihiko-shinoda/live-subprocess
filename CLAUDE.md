# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`realtime_stdout_displaying` is a mixin package for running subprocesses with real-time stdout display using PTY (pseudo-terminal). It ensures child processes see a TTY and use line-buffering rather than full-buffering, so output appears immediately rather than only at process exit.

## Development Commands

All commands are run from the workspace root (`/workspace`). See the root `CLAUDE.md` for the full list. Most relevant:

```bash
uv run invoke test          # Run fast tests
uv run invoke lint          # Fast linting
uv run invoke lint.deep     # Deep linting (mypy strict, pylint)
uv run invoke style         # Format code
```

## Architecture

The package uses a factory pattern with platform-specific implementations:

- **`RealtimeStdoutDisplaying`** (`realtime_stdout_displaying.py`) — Abstract mixin base class. Declares `run()` as abstract.

- **`RealtimeStdoutDisplayingPtyProcess`** (`posix/pty.py`) — Encapsulates all state for a single PTY-backed subprocess run. Created via the `create_process()` static async factory method, which calls `pty.openpty()`, launches the subprocess with the slave fd as stdout/stderr/stdin, closes the slave fd in the parent, registers `_on_readable()` on the master fd, and returns the instance. Instance variables: `_master_fd`, `_proc`, `_loop`, `_chunks`, and `_pty_done`. The `_on_readable()` callback reads up to 4096 bytes from the master fd, appends to `_chunks`, and writes immediately to `sys.stdout.buffer`; on `OSError` (EIO) it removes the reader and sets `_pty_done`. The `wait()` method uses `asyncio.gather()` to await both process exit and `_pty_done`, then defensively calls `remove_reader()`, closes the master fd, joins and decodes chunks (`errors="replace"`), normalises `\r\n` → `\n`, and strips whitespace.

- **`RealtimeStdoutDisplayingPosix`** (`posix/__init__.py`) — Stateless concrete POSIX implementation of `RealtimeStdoutDisplaying`. `run()` delegates entirely to `RealtimeStdoutDisplayingPtyProcess.create_process()` followed by `wait()`, so the mixin itself holds no per-run state.

- **`RealtimeStdoutDisplayingFactory`** (`factory.py`) — Returns a `RealtimeStdoutDisplayingPosix` on POSIX; raises `NotImplementedError` on Windows.

### `pipe/` Subpackage

Provides non-blocking, thread-backed pipe readers that prevent subprocess pipe buffers from filling up and causing deadlocks.

- **`PipeManager`** (`pipe/pipe_manager.py`) — Abstract base class. Constructor accepts a `threading.Event` (for shutdown signalling) and an `IO[bytes]` pipe; spawns a daemon thread that calls the abstract `log()` method. Buffers data in a `Queue[bytes]`. Abstract methods: `log(pipe)` (background reader loop) and `read()` (returns buffered output).

  - **`BytesPipeManager`** — Reads fixed-size binary chunks (`frame_bytes`). `log()` reads until the shutdown event is set, putting non-empty chunks in the queue. `read()` performs a non-blocking queue drain and returns `list[bytes]`.
  - **`StringPipeManager`** — Reads line-by-line using `iter(pipe.readline, b"")`. `log()` also logs each decoded line to the module logger. `read()` drains the queue, decodes lines as UTF-8, and returns a joined `str`.

- **`RealtimePipeReader`** (`pipe/realtime_pipe_reader.py`) — Abstract base class. Holds a `threading.Event` for coordinating shutdown. Abstract methods: `read_stdout()`, `read_stderr()`, `stop()`.

  - **`StringRealtimePipeReader`** — General-purpose reader. Constructs two `StringPipeManager` instances (one for stdout, one for stderr). `stop()` sets the event and joins both threads.
  - **`FFmpegRealtimePipeReader`** — FFmpeg-specific reader. Always uses a `StringPipeManager` for stderr; optionally uses a `BytesPipeManager` for stdout when `frame_bytes` is provided (raw frame capture). `read_stdout()` returns `list[bytes]`; `read_stderr()` returns a decoded `str`.

### Key Implementation Details

- **PTY vs PIPE**: PTY is essential. When a subprocess sees a pipe on stdout it switches to full-buffering and output is withheld until exit. PTY makes the child believe it is connected to a terminal, keeping line-buffering active.
- **Line ending normalization**: PTY translates `\n` to `\r\n`. `run()` normalizes these back before returning the captured string.
- **Per-invocation isolation**: A new `RealtimeStdoutDisplayingPtyProcess` object is created for every `run()` call, so the mixin is inherently reusable without any reset logic. `asyncio.gather()` waits for both process exit and PTY EOF before the master fd is closed.
- **Shutdown sequencing**: `_pty_done` is set inside `_on_readable()` when EIO fires; `wait()` then defensively calls `remove_reader()` before `os.close(master_fd)` to prevent any late callback.
- **Windows**: Not implemented. `RealtimeStdoutDisplayingFactory.create()` raises `NotImplementedError` on Windows (`os.name == "nt"`).

### Relationship to Root-Level File

There is also `/workspace/realtime_stdout_displaying.py` (a single-file version with Japanese error messages and an additional abstract `execute` method). The package in this directory (`realtime_stdout_displaying/`) is the refactored, English version with the factory pattern separating platform concerns. Prefer the package version for new work.

## Code Conventions

Follows the workspace-wide conventions from the root `CLAUDE.md`: Python 3.9+, mypy strict, Google docstrings, 119-char line length, single-line imports, all imports at module top level.
