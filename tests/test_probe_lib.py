"""The probe helpers that run without a site."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("probe_lib", Path(__file__).parent.parent / "probes" / "_lib.py")
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)


def test_parse_env_strips_quotes_and_skips_comments():
    text = "# comment\n\nFPT_API_SITE_URL='https://x.example.com'\nFPT_PROBE_SANDBOX_PROJECT=\"Sand box\"\nBAD LINE\n"
    assert lib.parse_env(text) == {"FPT_API_SITE_URL": "https://x.example.com", "FPT_PROBE_SANDBOX_PROJECT": "Sand box"}


def test_scrub_replaces_secrets_host_and_emails():
    env = {"FPT_API_SITE_URL": "https://studio.shotgrid.autodesk.com", "FPT_API_SCRIPT_NAME": "probe", "FPT_API_API_KEY": "k3y"}
    out = lib.scrub("https://studio.shotgrid.autodesk.com probe k3y a.b@c.io studio", env)
    assert "k3y" not in out and "a.b@c.io" not in out and "studio" not in out
    assert "API read()" in lib.scrub("API read() Shot.code doesn't exist", env)


def test_ask_returns_the_value_or_the_exception():
    assert lib.ask(lambda: 3) == {"ok": 3}
    assert lib.ask(lambda: 1 / 0)["raised"] == "ZeroDivisionError"


def test_writes_need_the_flag():
    assert lib.writes_allowed(["probe.py", "--write"])
    assert not lib.writes_allowed(["probe.py"])


def test_env_lookup_reaches_sg_groundtruth_from_a_worktree():
    assert lib.ROOT.parent.parent / "sg-groundtruth" / ".env.local" in lib.ENV_FILES
