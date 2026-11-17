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
    sg.set_clock(_TickingClock())
    return sg


class _TickingClock(object):
    """A clock that starts at ``CLOCK_START`` and advances one second per reading."""

    def __init__(self):
        self.ticks = 0

    def __call__(self):
        now = CLOCK_START + datetime.timedelta(seconds=self.ticks)
        self.ticks += 1
        return now


@pytest.fixture
def sg():
    """A fresh mockgun instance on the bundled schema, with a deterministic clock."""
    return make_sg()
