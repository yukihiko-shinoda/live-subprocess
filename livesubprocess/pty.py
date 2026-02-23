"""Mixin base class for running subprocesses with real-time stdout display."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

__all__ = ["LivePty"]


# TODO(Yukihiko Shinoda): Address Pylint warning  # noqa: TD003,FIX002
class LivePty(ABC):  # pylint: disable=too-few-public-methods
    """Mixin base class that runs subprocesses with real-time stdout display."""

    @abstractmethod
    async def run(self, command: list[str], env: dict[str, str] | None = None) -> tuple[str, int]:
        """Run a command with real-time stdout display.

        Returns (stdout, returncode).
        """
