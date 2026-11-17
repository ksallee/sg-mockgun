"""Shared plumbing for api3 probes: env, client, sandbox guard, cleanup and a mechanical scrubber.

A probe asks one question of a live site over api3 and prints the answer. It never writes
`docs/api3/`: the agent running it judges what is identifying and writes the answer file by hand.

Rules:

- Read-only by default. Writes need `--write` and go only into the project named by
  `FPT_PROBE_SANDBOX_PROJECT`.
- A probe leaves no trace. Rows it creates go through `Created`, which deletes them in reverse order.
- A schema field a probe creates is named `sg_zzprobe_mockgun_<nnn>_*`. A deleted field keeps its name
  until the Trash page is emptied by hand.
- Never print a secret. `scrub` replaces the site URL, script name, key, emails and tokens.
- Never rewrite an API error, a field name or a data type. Those are the answer.
"""
import json
import os
import re
import sys
from pathlib import Path

import shotgun_api3

ROOT = Path(__file__).resolve().parent.parent
ANSWERS = ROOT / "docs" / "api3"
ENV_FILES = (ROOT / ".env.local", ROOT.parent / "sg-groundtruth" / ".env.local")
SECRET_KEYS = ("FPT_API_SITE_URL", "FPT_API_SCRIPT_NAME", "FPT_API_API_KEY")


def parse_env(text):
    """The `KEY=value` pairs of an env file, quotes stripped, comments and blank lines skipped."""
    pairs = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        pairs[key.strip()] = value.strip().strip("'\"")
    return pairs


def load_env():
    """sg-mockgun's `.env.local`, else sg-groundtruth's, layered over a copy of os.environ."""
    env = dict(os.environ)
    for path in ENV_FILES:
        if path.exists():
            env.update(parse_env(path.read_text()))
            return env
    raise SystemExit("no .env.local in sg-mockgun or ../sg-groundtruth")


def need(env, key):
    value = (env.get(key) or "").strip()
    if not value:
        raise SystemExit("set %s in .env.local" % key)
    return value


def client(env):
    """A shotgun_api3 client on the site named in the env."""
    return shotgun_api3.Shotgun(
        need(env, "FPT_API_SITE_URL"),
        script_name=need(env, "FPT_API_SCRIPT_NAME"),
        api_key=need(env, "FPT_API_API_KEY"),
    )


def writes_allowed(argv=None):
    return "--write" in (sys.argv if argv is None else argv)


def sandbox(sg, env):
    """The one project a probe may write into, as an entity dict. Exits when it is missing."""
    name = need(env, "FPT_PROBE_SANDBOX_PROJECT")
    project = sg.find_one("Project", [["name", "is", name]], ["name"])
    if not project:
        raise SystemExit("no project named by FPT_PROBE_SANDBOX_PROJECT")
    return {"type": "Project", "id": project["id"]}


class Created(object):
    """Rows a probe made, deleted in reverse order when the block exits."""

    def __init__(self, sg):
        self.sg, self.rows = sg, []

    def add(self, entity):
        self.rows.append((entity["type"], entity["id"]))
        return entity

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for entity_type, entity_id in reversed(self.rows):
            try:
                self.sg.delete(entity_type, entity_id)
                print("  deleted %s %s" % (entity_type, entity_id))
            except shotgun_api3.Fault as e:
                print("  delete %s %s failed: %s" % (entity_type, entity_id, e))
        return False


def ask(fn, *args, **kwargs):
    """Call an api3 method and return its answer: the value, or the exception class and message."""
    try:
        return {"ok": fn(*args, **kwargs)}
    except Exception as e:  # the exception is the answer
        return {"raised": type(e).__name__, "message": str(e)}


def scrub(text, env):
    """Mechanical substitutions only. Never touches ordinary words."""
    for key in SECRET_KEYS:
        value = env.get(key)
        if value:
            text = text.replace(value, "<%s>" % key)
    host = (env.get("FPT_API_SITE_URL") or "").split("//")[-1].split(".")[0]
    if host:
        text = text.replace(host, "<site>")
    home = os.path.expanduser("~")
    if home and home != "/":
        text = text.replace(home, "<home>")
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", text)
    text = re.sub(r"\beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}", "<token>", text)
    text = re.sub(r"https://[\w.\-]*(amazonaws|shotgrid|shotgunstudio|autodesk)[\w.\-]*/\S+", "<media-url>", text)
    return text


def site_line(sg):
    """The site version and client version, for an answer file's `measured:` line."""
    version = sg.info().get("version") or []
    return "Flow PT %s, shotgun_api3 %s" % (".".join(str(v) for v in version[:3]), shotgun_api3.__version__)


def emit(slug, answers, env, sg=None):
    """Print a probe's answers as scrubbed JSON, with the measured line when a client is given."""
    print("===== %s =====" % slug)
    if sg is not None:
        print("measured: %s" % site_line(sg))
    print(scrub(json.dumps(answers, indent=2, default=str), env))
