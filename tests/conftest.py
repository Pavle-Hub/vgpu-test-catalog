"""Test setup shared by local runs and clean CI checkouts."""

from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Create the parent that pytest requires for an explicit --basetemp."""

    if config.option.basetemp:
        Path(config.option.basetemp).resolve().parent.mkdir(parents=True, exist_ok=True)
