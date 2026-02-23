"""Configuration of pytest."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


collect_ignore = []
if os.name == "nt":  # pragma: no cover
    collect_ignore.append("tests/posix/test_popen.py")


@pytest.fixture
def path_file_input(resource_path_root: Path) -> Path:
    return resource_path_root / "sample.mp4"
