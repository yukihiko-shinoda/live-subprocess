"""POSIX Popen-based implementation of RealtimeStdoutDisplaying."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Literal
from typing import TypeVar

from livesubprocess.popen import LivePopen

if TYPE_CHECKING:
    from collections.abc import Coroutine

    # Reason: This package requires to use subprocess.
    from subprocess import Popen  # nosec

__all__ = ["LivePopenByLoop", "StandardStream"]


class StandardStream:
    """Per-stream state (file descriptor + EOF event) for LivePopenByLoop."""

    def __init__(self, fd: int, chunks: list[bytes]) -> None:
        self.fd = fd
        self.chunks = chunks
        self._done: asyncio.Event | None = None

    @property
    def done(self) -> asyncio.Event:
        """Return the EOF event, creating it lazily on first access inside a running loop.

        Deferred to avoid calling asyncio.Event() at construction time: in Python 3.9 asyncio.Event.__init__ calls
        get_event_loop(), which raises RuntimeError when a previous asyncio.run() has already set the current loop to
        None.
        """
        if self._done is None:
            self._done = asyncio.Event()
        return self._done

    def wait_done(self) -> Coroutine[Any, Any, Literal[True]]:
        """Wait for EOF event to be set."""
        return self.done.wait()


class StreamReader:
    """Callable for asyncio loop.add_reader() to read from a fd and write to stdout in real time."""

    def __init__(self, loop: asyncio.AbstractEventLoop, standard_stream: StandardStream) -> None:
        self.loop = loop
        self.standard_stream = standard_stream

    def __call__(self) -> None:
        """Read available data from fd; append to chunks, write to stdout, and signal EOF."""
        loop = self.loop
        done = self.standard_stream.done
        try:
            chunk = os.read(self.standard_stream.fd, 4096)
        except OSError:
            loop.remove_reader(self.standard_stream.fd)
            done.set()
            return
        if chunk:
            self.standard_stream.chunks.append(chunk)
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        else:  # EOF
            loop.remove_reader(self.standard_stream.fd)
            done.set()


TypeVarReturnValue = TypeVar("TypeVarReturnValue")


class EventLoopWrapper:
    """Wrapper for asyncio event loop to allow testing fallback behavior when no loop is running."""

    def __init__(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Initialize with an explicit loop, or None to get from running loop in wait().

        Args:
            loop: An explicit event loop to use, or None to get from running loop in wait.
                  Initialized lazily in wait() to avoid requiring a running event loop at construction time.
        """
        self._loop = loop

    def get_running_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None:
            return self._loop
        return asyncio.get_running_loop()

    def add_reader(self, standard_stream: StandardStream) -> None:
        loop = self.get_running_loop()
        loop.add_reader(standard_stream.fd, StreamReader(loop, standard_stream))

    def remove_reader(self, standard_stream: StandardStream) -> None:
        loop = self.get_running_loop()
        loop.remove_reader(standard_stream.fd)

    def run_in_executor(self, func: Callable[[], TypeVarReturnValue]) -> asyncio.Future[TypeVarReturnValue]:
        loop = self.get_running_loop()
        return loop.run_in_executor(None, func)

    def __len__(self) -> int:
        return 1 if self._loop is not None else 0


class LivePopenByLoop(LivePopen):
    """A running Popen-managed process that can be independently awaited."""

    def __init__(self, popen: Popen[bytes], loop: asyncio.AbstractEventLoop | None = None) -> None:
        if popen.stdout is None or popen.stderr is None:
            msg = "Popen must have stdout and stderr pipes"
            raise ValueError(msg)
        self._popen = popen
        self._loop = EventLoopWrapper(loop)  # Explicit loop; None means get from running loop in wait()
        self._chunks: list[bytes] = []
        self._stdout = StandardStream(popen.stdout.fileno(), self._chunks)
        self._stderr = StandardStream(popen.stderr.fileno(), self._chunks)

    def stop(self) -> None:
        """Deregister fd readers; call before popen.communicate() or popen.terminate()."""
        if self._loop:
            return
        self._loop.remove_reader(self._stdout)
        self._loop.remove_reader(self._stderr)

    async def wait(self) -> tuple[str, int]:
        """Wait for process and all output; return (merged_stdout_stderr, returncode)."""
        try:
            self._loop.get_running_loop()
        except RuntimeError:
            # No running event loop (e.g., coroutine advanced via .send() in a subprocess without
            # asyncio.run()). Fall back to synchronous blocking wait, matching the old thread-based
            # behavior: popen.wait() blocks here and remains interruptable by KeyboardInterrupt.
            self._popen.wait()
            stdout = b"".join(self._chunks).decode(errors="replace").strip()
            if self._popen.returncode is None:
                msg = "Process finished but returncode is None"
                raise RuntimeError(msg) from None
            return stdout, self._popen.returncode
        self._loop.add_reader(self._stdout)
        self._loop.add_reader(self._stderr)
        await asyncio.gather(
            self._loop.run_in_executor(self._popen.wait),
            self._stdout.wait_done(),
            self._stderr.wait_done(),
        )
        # Defensive: no-op if already removed by on_readable()
        self._loop.remove_reader(self._stdout)
        self._loop.remove_reader(self._stderr)
        stdout = b"".join(self._chunks).decode(errors="replace").strip()
        if self._popen.returncode is None:
            msg = "Process finished but returncode is None"
            raise RuntimeError(msg)
        return stdout, self._popen.returncode
