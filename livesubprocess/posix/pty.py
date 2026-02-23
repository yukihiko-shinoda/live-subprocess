"""POSIX PTY-based implementation of RealtimeStdoutDisplaying."""

from __future__ import annotations

import asyncio
import os
import pty
import sys

__all__ = ["LivePtyProcessPosix"]


class LivePtyProcessPosix:
    """A running PTY-managed process that can be independently awaited."""

    def __init__(
        self,
        master_fd: int,
        proc: asyncio.subprocess.Process,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._master_fd = master_fd
        self._proc = proc
        self._loop = loop if loop is not None else asyncio.get_running_loop()
        self._chunks: list[bytes] = []
        self._pty_done = asyncio.Event()
        self._loop.add_reader(master_fd, self._on_readable)

    def _on_readable(self) -> None:
        """Read available bytes from the PTY master, buffer them, and forward to stdout."""
        try:
            chunk = os.read(self._master_fd, 4096)
            self._chunks.append(chunk)
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        except OSError:  # EIO when slave side closes after process exits
            # Deregister now; the fd stays "readable" after EIO and would re-fire indefinitely otherwise
            self._loop.remove_reader(self._master_fd)
            self._pty_done.set()

    async def wait(self) -> tuple[str, int]:
        """Wait for the process to finish and return (stdout, returncode).

        Waits for both the process to exit and the PTY master fd to close (EIO), then normalizes line endings and
        returns captured stdout.
        """
        await asyncio.gather(self._proc.wait(), self._pty_done.wait())
        # Defensive: no-op if _on_readable's except path already removed it, but guards against
        # any future code path that sets _pty_done without going through that handler
        self._loop.remove_reader(self._master_fd)
        os.close(self._master_fd)
        # PTY converts \n to \r\n; normalize back before returning
        stdout = b"".join(self._chunks).decode(errors="replace").replace("\r\n", "\n").strip()
        if self._proc.returncode is None:
            msg = "Process finished but returncode is None"
            raise RuntimeError(msg)
        return stdout, self._proc.returncode

    @staticmethod
    async def create_process(
        command: list[str],
        env: dict[str, str] | None = None,
    ) -> LivePtyProcessPosix:
        """Set up PTY and create subprocess.

        Creates master/slave PTY pair, launches the subprocess with the slave fd as stdout/stderr/stdin, closes the
        slave fd in the parent, and registers the async reader on the master fd.

        Returns the running process handle.
        """
        # PTY is used instead of PIPE so the child process sees a TTY and flushes output immediately
        # (line-buffered). With PIPE the child switches to full-buffering and output only appears
        # when the process exits.
        master_fd, slave_fd = pty.openpty()
        proc = await asyncio.create_subprocess_exec(
            *command,
            env=env if env is not None else os.environ,
            stdout=slave_fd,
            stderr=slave_fd,
            stdin=slave_fd,
        )
        os.close(slave_fd)
        return LivePtyProcessPosix(master_fd, proc)
