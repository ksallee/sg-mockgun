"""pytest plugin: the ``sg`` fixture, a fresh mock site per test on the bundled schema."""

import datetime

import pytest

from . import schemas
from .mockgun import Shotgun

CLOCK_START = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


class _FixtureShotgun(Shotgun):
    """A subclass, so its schema paths leave ``Shotgun``'s class-level paths untouched."""


_FixtureShotgun.set_schema_paths(*schemas.paths())


def make_sg():
    """A new instance on the bundled schema with a clock that starts at ``CLOCK_START``."""
    sg = _FixtureShotgun("https://mock.example.com", script_name="pytest", api_key="pytest")
    sg.set_clock(_ticking_clock())
    return sg


def _ticking_clock():
    ticks = [0]

    def clock():
        now = CLOCK_START + datetime.timedelta(seconds=ticks[0])
        ticks[0] += 1
        return now

    return clock


@pytest.fixture
def sg():
    """A fresh mockgun instance on the bundled schema, with a deterministic clock."""
    return make_sg()
