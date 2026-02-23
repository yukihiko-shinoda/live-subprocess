"""POSIX PTY-based implementation of RealtimeStdoutDisplaying."""

from __future__ import annotations

from livesubprocess.posix.popen import LivePopenByLoop
from livesubprocess.posix.pty import LivePtyProcessPosix
from livesubprocess.pty import LivePty

__all__ = ["LivePopenByLoop", "LivePtyProcessPosix"]


# TODO(Yukihiko Shinoda): Address Pylint warning  # noqa: TD003,FIX002
class LivePtyPosix(LivePty):  # pylint: disable=too-few-public-methods
    """PTY-based mixin that runs subprocesses with real-time stdout display on POSIX."""

    async def run(self, command: list[str], env: dict[str, str] | None = None) -> tuple[str, int]:
        """Run a command with PTY for realtime stdout display.

        Returns (stdout, returncode).
        """
        proc = await LivePtyProcessPosix.create_process(command, env)
        return await proc.wait()
