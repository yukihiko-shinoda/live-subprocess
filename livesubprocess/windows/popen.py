"""Windows Popen-based implementation of RealtimeStdoutDisplaying."""

from __future__ import annotations

from typing import TYPE_CHECKING

from livesubprocess.pipe.realtime_pipe_reader import StringRealtimePipeReader
from livesubprocess.popen import LivePopen

if TYPE_CHECKING:
    # Reason: This package requires to use subprocess.
    from subprocess import Popen  # nosec

__all__ = ["LivePipeReader"]


class LivePipeReader(LivePopen):
    """A Popen process wrapper using thread-based pipe reading for Windows compatibility.

    Thread-based reading is required to prevent blocking when popen.wait() is called on Windows.
    Without draining the pipes in background threads, the pipe buffers fill up and popen.wait()
    hangs indefinitely.
    See:
      - quiet mode for run_async method might cause ffmpeg process to stick.
        · Issue #195 · kkroening/ffmpeg-python
        https://github.com/kkroening/ffmpeg-python/issues/195#issuecomment-671062263
      - ffmpeg process stops outputting data after ~7 mins · Issue #370 · kkroening/ffmpeg-python
        https://github.com/kkroening/ffmpeg-python/issues/370#issuecomment-638391998
    """

    def __init__(self, popen: Popen[bytes]) -> None:
        self._reader = StringRealtimePipeReader(popen)

    async def wait(self) -> tuple[str, int]:
        """Wait for the process and all output; return (merged_stdout_stderr, returncode)."""
        return await self._reader.wait()

    def stop(self) -> None:
        """Signal pipe reader threads to stop and join them."""
        self._reader.stop()
