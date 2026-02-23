"""Real-time stdout displaying factory."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if os.name == "nt":  # pragma: no cover
    from livesubprocess.windows.popen import LivePipeReader
else:
    from livesubprocess.posix import LivePtyPosix
    from livesubprocess.posix.popen import LivePopenByLoop

if TYPE_CHECKING:
    # Reason: This package requires to use subprocess.
    from subprocess import Popen  # nosec

    from livesubprocess.popen import LivePopen
    from livesubprocess.pty import LivePty

__all__ = ["LiveSubProcessFactory"]


class LiveSubProcessFactory:
    """Factory for creating platform-appropriate realtime stdout displaying processes."""

    @staticmethod
    def create_pty() -> LivePty:
        if os.name == "nt":  # pragma: no cover
            raise NotImplementedError
        # Reason: LivePtyPosix is only used on POSIX, so it's safe to return it without checking os.name again.
        return LivePtyPosix()  # pylint: disable=possibly-used-before-assignment

    @staticmethod
    def create_popen(popen: Popen[bytes]) -> LivePopen:
        """Create a platform-appropriate realtime stdout displaying process for a Popen object.

        On Windows, asyncio.add_reader() is not supported for pipe fds, so a thread-based
        RealtimeStdoutDisplayingPopenByRealtimePipeReaderProcess is used instead.

        Args:
            popen: The Popen object whose stdout and stderr will be read.

        Returns:
            RealtimeStdoutDisplayingPopenByLoopProcess on POSIX, or RealtimeStdoutDisplayingPopenByRealtimePipeReaderProcess on Windows.
        """
        if os.name == "nt":  # pragma: no cover
            return LivePipeReader(popen)
        # Reason: LivePtyPosix is only used on POSIX, so it's safe to return it without checking os.name again.
        return LivePopenByLoop(popen)  # pylint: disable=possibly-used-before-assignment
