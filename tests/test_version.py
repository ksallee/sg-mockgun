"""The package version is read from pyproject.toml."""

import re
from pathlib import Path

from sg_mockgun import mockgun


def test_version_matches_pyproject():
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    assert mockgun.__version__ == declared
