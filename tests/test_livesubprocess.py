"""Tests for `livesubprocess` package."""

from __future__ import annotations

import asyncio
import sys

# Reason: This package requires to use subprocess.
from subprocess import PIPE  # nosec
from subprocess import Popen  # nosec

from livesubprocess.factory import LiveSubProcessFactory


def test_create_popen() -> None:
    # Reason: This only executes test code.
    with Popen([sys.executable, "-c", "print('hello')"], stdout=PIPE, stderr=PIPE) as popen:  # nosec B603
        live_popen = LiveSubProcessFactory.create_popen(popen)
        stdout, returncode = asyncio.run(live_popen.wait())
    assert "hello" in stdout
    assert returncode == 0
