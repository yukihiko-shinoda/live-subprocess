"""Top-level package for Live Subprocess."""

from __future__ import annotations

from livesubprocess.factory import *  # noqa: F403
from livesubprocess.popen import *  # noqa: F403
from livesubprocess.pty import *  # noqa: F403

__author__ = """Yukihiko Shinoda"""
__email__ = "yuk.hik.future@gmail.com"
__version__ = "0.1.0"

__all__: list[str] = []
__all__ += factory.__all__  # type: ignore[name-defined]  # noqa: F405 pylint: disable=undefined-variable
__all__ += popen.__all__  # type: ignore[name-defined]  # noqa: F405 pylint: disable=undefined-variable
__all__ += pty.__all__  # type: ignore[name-defined]  # noqa: F405 pylint: disable=undefined-variable
