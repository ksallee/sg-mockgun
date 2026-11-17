"""Pytest plugin that makes tk-core's test suite run on sg-mockgun instead of upstream mockgun.

Load it with ``-p sg_mockgun_tk_core_shim`` from a tk-core checkout, with this folder on
``PYTHONPATH``. ``tools/run_tk_core.py`` does both.

``SG_MOCKGUN_EVENT_LOG`` set to ``0`` turns the event log off on every instance. Any other value,
or unset, leaves the default.
"""

import os
import sys

import pytest

_ALIASES = (
    "shotgun_api3.lib.mockgun",
    "tank_vendor.shotgun_api3.lib.mockgun",
)


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """Alias sg_mockgun under the upstream mockgun module names after tk-toolchain puts tk-core on sys.path."""
    # tank_vendor loads requirements/<py>/pkgs.zip and registers its shotgun_api3 as the top-level
    # module. Importing it first makes sg_mockgun's `import shotgun_api3` resolve to that copy.
    import tank_vendor  # noqa: F401
    from tank_vendor import shotgun_api3
    import shotgun_api3.lib

    import sg_mockgun
    import sg_mockgun.mockgun

    if sg_mockgun.mockgun.Fault is not shotgun_api3.Fault:
        raise RuntimeError(
            "sg_mockgun imported a different shotgun_api3 than tank_vendor's. "
            "Install sg-mockgun with --no-deps so only tk-core's copy is importable. "
            "sg_mockgun's: %s. tank_vendor's: %s."
            % (sys.modules[sg_mockgun.mockgun.Fault.__module__].__file__, shotgun_api3.__file__)
        )

    for name in _ALIASES:
        sys.modules[name] = sg_mockgun
        sys.modules[name + ".mockgun"] = sg_mockgun.mockgun
    shotgun_api3.lib.mockgun = sg_mockgun

    if os.environ.get("SG_MOCKGUN_EVENT_LOG") == "0":
        _turn_off_event_log(sg_mockgun.Shotgun)


def _turn_off_event_log(cls):
    """Wrap the constructor so each new instance starts with the event log off."""
    original = cls.__init__

    def __init__(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.generate_event_log_entries = False

    cls.__init__ = __init__


def pytest_report_header(config):
    """Name the mockgun under test and the event log setting in the pytest header."""
    import sg_mockgun

    state = "off" if os.environ.get("SG_MOCKGUN_EVENT_LOG") == "0" else "on"
    return "mockgun: sg_mockgun from %s, event log %s" % (os.path.dirname(sg_mockgun.__file__), state)
