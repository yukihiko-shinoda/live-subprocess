"""Abstract base class for realtime stdout displaying popen processes."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

__all__ = ["LivePopen"]


class LivePopen(ABC):
    """Abstract base class for running Popen-managed processes with realtime stdout display."""

    @abstractmethod
    async def wait(self) -> tuple[str, int]:
        """Wait for the process and all output; return (merged_stdout_stderr, returncode)."""

    @abstractmethod
    def stop(self) -> None:
        """Deregister fd readers; call before popen.communicate() or popen.terminate()."""
