"""To realize non-blocking read.

see:
    - Answer: A non-blocking read on a subprocess.PIPE in Python - Stack Overflow
    https://stackoverflow.com/a/4896288/12721873
"""

from __future__ import annotations

import asyncio
from abc import abstractmethod
from threading import Event
from typing import TYPE_CHECKING

from livesubprocess.pipe.pipe_manager import BytesPipeManager
from livesubprocess.pipe.pipe_manager import StringPipeManager

if TYPE_CHECKING:
    # Reason: This package requires to use subprocess.
    from subprocess import Popen  # nosec


class RealtimePipeReader:
    """Abstract class."""

    def __init__(self) -> None:
        self.event = Event()

    @abstractmethod
    def read_stdout(self) -> str | list[bytes]:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def read_stderr(self) -> str:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError  # pragma: no cover


class StringRealtimePipeReader(RealtimePipeReader):
    """For strings."""

    def __init__(self, popen: Popen[bytes]) -> None:
        super().__init__()
        if not popen.stdout:
            msg = "popen.stdout is None"
            raise ValueError(msg)
        if not popen.stderr:
            msg = "popen.stderr is None"
            raise ValueError(msg)
        self.popen = popen
        self.pipe_manager_stdout = StringPipeManager(self.event, popen.stdout)
        self.pipe_manager_stderr = StringPipeManager(self.event, popen.stderr)

    def read_stdout(self) -> str:
        return self.pipe_manager_stdout.read()

    def read_stderr(self) -> str:
        return self.pipe_manager_stderr.read()

    async def wait(self) -> tuple[str, int]:
        """Wait for the process to finish, and return (stdout, returncode)."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.popen.wait)
        self.pipe_manager_stdout.thread.join()
        self.pipe_manager_stderr.thread.join()
        stdout = self.read_stdout() + self.read_stderr()
        if self.popen.returncode is None:
            msg = "Process finished but returncode is None"
            raise RuntimeError(msg)
        return stdout, self.popen.returncode

    def stop(self) -> None:
        self.event.set()
        self.pipe_manager_stdout.thread.join()
        self.pipe_manager_stderr.thread.join()


class FFmpegRealtimePipeReader(RealtimePipeReader):
    """For FFmpeg."""

    def __init__(self, popen: Popen[bytes], *, frame_bytes: int | None = None) -> None:
        super().__init__()
        if not popen.stdout:
            msg = "popen.stdout is None"
            raise ValueError(msg)
        if not popen.stderr:
            msg = "popen.stderr is None"
            raise ValueError(msg)
        self.pipe_manager_stderr = StringPipeManager(self.event, popen.stderr)
        self.pipe_manager_stdout = (
            None if frame_bytes is None else BytesPipeManager(self.event, popen.stdout, frame_bytes)
        )

    def read_stdout(self) -> list[bytes]:
        # Reason: omit if statement for excluding None for performance.
        return self.pipe_manager_stdout.read()  # type: ignore[union-attr]

    def read_stderr(self) -> str:
        return self.pipe_manager_stderr.read()

    def stop(self) -> None:
        self.event.set()
        self.pipe_manager_stderr.thread.join()
        if self.pipe_manager_stdout is not None:
            self.pipe_manager_stdout.thread.join()
