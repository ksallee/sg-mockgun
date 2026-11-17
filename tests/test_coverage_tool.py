"""tools/coverage.py render: one row per cell, the live column from the live results or `gap`."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("coverage_tool", Path(__file__).resolve().parents[1] / "tools" / "coverage.py")
coverage_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage_tool)

MOCK = {"tests": {
    "a.py::test_is": {"finding": "017", "api3": None, "cell": ["find", "is", "text"], "outcome": "pass"},
    "a.py::test_is_2": {"finding": "017", "api3": None, "cell": ["find", "is", "text"], "outcome": "fail"},
    "b.py::test_log": {"finding": "049", "api3": "docs/x.md", "cell": None, "outcome": "pass"},
}}


def test_without_a_live_run_the_site_column_is_gap():
    page = coverage_tool.render(MOCK, None)
    assert "No live run recorded." in page
    assert "| find | is | text | fail | gap | 017 | REST only |" in page
    assert "| `test_log` | pass | gap | 049 | api3 |" in page


def test_live_results_fill_the_site_column_and_header():
    live = {"site_version": "8.91.0", "date": "2026-11-17",
            "tests": {"a.py::test_is": {"outcome": "pass"}, "a.py::test_is_2": {"outcome": "pass"}}}
    page = coverage_tool.render(MOCK, live)
    assert "Site: Flow PT 8.91.0. Live run: 2026-11-17." in page
    assert "| find | is | text | fail | pass | 017 | REST only |" in page
    assert "| `test_log` | pass | gap | 049 | api3 |" in page
