"""Unit tests for `livesubprocess/posix/popen.py` targeting missing coverage lines."""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import sys

# Reason: This package requires to use subprocess.
from subprocess import PIPE  # nosec
from subprocess import Popen  # nosec

import pytest

from livesubprocess.posix.popen import EventLoopWrapper
from livesubprocess.posix.popen import LivePopenByLoop
from livesubprocess.posix.popen import StandardStream
from livesubprocess.posix.popen import StreamReader

# Example condition: skip the file if the Python version is less than 3.10
if os.name == "nt":
    pytest.skip("This test file requires a POSIX system.", allow_module_level=True)

# ---------------------------------------------------------------------------
# Fake helpers used for defensive-branch tests (lines 133-134 and 148-149).
#
# Reason: real Popen.wait() always sets returncode to a non-None integer after
# returning, making the two `if self._popen.returncode is None: raise RuntimeError`
# guards unreachable with a genuine subprocess.  Minimal fake objects with real
# OS-level file descriptors let us exercise those branches without unittest.mock.
# ---------------------------------------------------------------------------


class _FakePopen(Popen[bytes]):
    """Fake Popen whose wait() is a no-op, so returncode stays None.

    Used to reach the sync-fallback defensive branch (lines 133-134). Subclasses Popen[bytes] so LivePopenByLoop
    accepts it without a type: ignore. __init__ skips super().__init__() to avoid launching a real process;
    _child_created=False prevents Popen.__del__ from crashing on missing state.
    """

    def __init__(self, r_out: int, r_err: int) -> None:
        self._child_created = False  # prevent Popen.__del__ from accessing uninitialized state
        self.returncode: int | None = None
        self.stdout = io.FileIO(r_out, mode="r", closefd=False)
        self.stderr = io.FileIO(r_err, mode="r", closefd=False)

    def wait(self, _timeout: float | None = None) -> int:
        return 0


class _FakePopenWithEof(Popen[bytes]):
    """Fake Popen whose wait() closes pipe write-ends (EOF) but leaves returncode None.

    Used to reach the async-path defensive branch (lines 148-149).  Closing the write ends causes os.read() on the read
    ends to return b"", which signals EOF to StreamReader and unblocks StandardStream.wait_done(), allowing
    asyncio.gather to complete while returncode remains None. Subclasses Popen[bytes] for the same reason as _FakePopen
    above.
    """

    def __init__(self, r_out: int, w_out: int, r_err: int, w_err: int) -> None:
        self._child_created = False  # prevent Popen.__del__ from accessing uninitialized state
        self.returncode: int | None = None
        self.stdout = io.FileIO(r_out, mode="r", closefd=False)
        self.stderr = io.FileIO(r_err, mode="r", closefd=False)
        self._w_out = w_out
        self._w_err = w_err

    def wait(self, _timeout: float | None = None) -> int:
        # Close write ends so read ends see EOF, but do NOT set returncode.
        os.close(self._w_out)
        os.close(self._w_err)
        return 0


# ---------------------------------------------------------------------------
# StreamReader tests
# ---------------------------------------------------------------------------


def test_stream_reader_oserror_on_closed_fd() -> None:
    """Covers lines 53-56: OSError path when the read fd is already closed."""
    r, w = os.pipe()
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)  # Ensure Python 3.9 has a current loop for lazy asyncio.Event() creation.
        stream = StandardStream(r, [])
        reader = StreamReader(loop, stream)
        os.close(r)  # Closing before the read triggers OSError inside __call__.
        reader()
        assert stream.done.is_set()
    finally:
        asyncio.set_event_loop(None)  # Restore clean state so subsequent tests start fresh.
        loop.close()
        os.close(w)


# ---------------------------------------------------------------------------
# EventLoopWrapper tests
# ---------------------------------------------------------------------------


def test_event_loop_wrapper_get_running_loop_with_explicit_loop() -> None:
    """Covers line 83: get_running_loop() returns the stored explicit loop."""
    loop = asyncio.new_event_loop()
    try:
        wrapper = EventLoopWrapper(loop)
        assert wrapper.get_running_loop() is loop
    finally:
        loop.close()


def test_event_loop_wrapper_len_with_explicit_loop() -> None:
    """Covers line 99 (truthy branch): __len__ returns 1 when a loop is stored."""
    loop = asyncio.new_event_loop()
    try:
        wrapper = EventLoopWrapper(loop)
        assert len(wrapper) == 1
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# LivePopenByLoop.__init__ tests
# ---------------------------------------------------------------------------


def test_live_popen_raises_value_error_without_pipes() -> None:
    """Covers lines 107-108: ValueError when Popen lacks stdout/stderr pipes."""
    # Reason: Popen with no PIPE for stdout/stderr — LivePopenByLoop must reject it.
    with Popen([sys.executable, "-c", ""]) as popen, pytest.raises(ValueError, match="stdout and stderr pipes"):  # noqa: S603  # nosec B603
        LivePopenByLoop(popen)


# ---------------------------------------------------------------------------
# LivePopenByLoop.stop() tests
# ---------------------------------------------------------------------------


def test_live_popen_stop_with_explicit_loop_returns_early() -> None:
    """Covers lines 117-118: stop() returns immediately when an explicit loop is set."""
    loop = asyncio.new_event_loop()
    try:
        # Reason: This only executes test code.
        with Popen([sys.executable, "-c", ""], stdout=PIPE, stderr=PIPE) as popen:  # noqa: S603  # nosec B603
            live = LivePopenByLoop(popen, loop=loop)
            live.stop()  # Should return early without calling remove_reader.
            popen.communicate()
    finally:
        loop.close()


def test_live_popen_stop_without_explicit_loop_removes_readers() -> None:
    """Covers lines 119-120: stop() calls remove_reader when no explicit loop is set.

    Must run inside asyncio.run() so that asyncio.get_running_loop() succeeds
    inside EventLoopWrapper.remove_reader().
    """

    async def _inner() -> None:
        # Reason:
        #   S603: This only executes test code.
        #   ASYNC220: The async wrapper is required so asyncio.get_running_loop() succeeds
        #             inside the code under test; Popen is intentional — LivePopenByLoop wraps a synchronous Popen.
        with Popen([sys.executable, "-c", ""], stdout=PIPE, stderr=PIPE) as popen:  # noqa: S603, ASYNC220  # nosec B603
            live = LivePopenByLoop(popen)  # No explicit loop → _loop is falsy.
            live.stop()  # Reaches lines 119-120; remove_reader is a no-op here.
            popen.communicate()

    asyncio.run(_inner())


# ---------------------------------------------------------------------------
# LivePopenByLoop.wait() — synchronous fallback tests
# ---------------------------------------------------------------------------


def test_live_popen_wait_sync_fallback() -> None:
    """Covers lines 126-132, 135: sync fallback when no event loop is running.

    Advancing the coroutine with .send(None) from synchronous code means asyncio.get_running_loop() raises
    RuntimeError, triggering the fallback.
    """
    # Reason: This only executes test code.
    with Popen([sys.executable, "-c", ""], stdout=PIPE, stderr=PIPE) as popen:  # noqa: S603  # nosec B603
        live = LivePopenByLoop(popen)
        coroutine = live.wait()
        result: tuple[str, int] | None = None
        try:
            # Reason: Pylint's bug:
            # - Coroutine type inferred incorrectly · Issue #4908 · pylint-dev/pylint
            #   https://github.com/pylint-dev/pylint/issues/4908
            coroutine.send(None)  # pylint: disable=no-member
        except StopIteration as exc:
            result = exc.value
        assert result is not None
        stdout, returncode = result
        assert returncode == 0
        assert stdout == ""


def test_live_popen_wait_sync_fallback_returncode_none_raises() -> None:
    """Covers lines 133-134: RuntimeError when sync fallback finds returncode is None.

    Fake Popen required: a real Popen.wait() always sets returncode to a non-None
    integer, so the defensive check is unreachable without a controlled fake.
    """
    r_out, w_out = os.pipe()
    r_err, w_err = os.pipe()
    try:
        fake_popen = _FakePopen(r_out, r_err)
        live = LivePopenByLoop(fake_popen)
        coroutine = live.wait()
        with pytest.raises(RuntimeError, match="returncode is None"), contextlib.suppress(StopIteration):
            # Reason: Pylint's bug:
            # - Coroutine type inferred incorrectly · Issue #4908 · pylint-dev/pylint
            #   https://github.com/pylint-dev/pylint/issues/4908
            coroutine.send(None)  # pylint: disable=no-member
    finally:
        for fd in [r_out, w_out, r_err, w_err]:
            with contextlib.suppress(OSError):
                os.close(fd)


# ---------------------------------------------------------------------------
# LivePopenByLoop.wait() — async path defensive check
# ---------------------------------------------------------------------------


def test_live_popen_wait_async_returncode_none_raises() -> None:
    """Covers lines 148-149: RuntimeError when async path finds returncode is None.

    Fake Popen required: same reason as the sync case above.  _FakePopenWithEof
    closes the write ends of both pipes inside wait(), which triggers EOF in the
    StreamReader callbacks and unblocks StandardStream.wait_done(), allowing
    asyncio.gather to complete while returncode stays None.
    """
    r_out, w_out = os.pipe()
    r_err, w_err = os.pipe()
    try:
        fake_popen = _FakePopenWithEof(r_out, w_out, r_err, w_err)
        live = LivePopenByLoop(fake_popen)
        with pytest.raises(RuntimeError, match="returncode is None"):
            asyncio.run(live.wait())
    finally:
        for fd in [r_out, w_out, r_err, w_err]:
            with contextlib.suppress(OSError):
                os.close(fd)
