"""Shared fixtures: every test gets its own lab data directory."""
from __future__ import annotations

import pytest

from app.api import endpoints
from app.lab.game import LabGame


@pytest.fixture(autouse=True)
def isolated_lab(tmp_path):
    """Keep the trainer profile and trainee copy out of backend/.lab during tests."""
    lab = LabGame(str(tmp_path / "lab"))
    endpoints.set_lab(lab)
    yield lab
    endpoints.set_lab(None)  # type: ignore[arg-type]
