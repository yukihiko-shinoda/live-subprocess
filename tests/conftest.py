"""Configuration of pytest."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def path_file_input(resource_path_root: Path) -> Path:
    return resource_path_root / "sample.mp4"
