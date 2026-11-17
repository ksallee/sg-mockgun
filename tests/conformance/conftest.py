"""Fixtures for the conformance suite: one set of api3 calls, run on the mock or on a live site.

The default target is the mock on the bundled schema. `--live` targets the site named in `.env.local`,
found as `probes/_lib.py` finds it. Writes go through `made` and schema field writes through `fields`, which refuse
anything outside the sandbox project and the `sg_zzprobe_mockgun_` prefix, on both targets.
"""

import datetime
import importlib.util
import json
import time
from pathlib import Path

import pytest

from sg_mockgun import Shotgun as Mockgun, schemas

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LIVE_RESULTS = ROOT / "docs" / "conformance-live.json"
FIELD_PREFIX = "sg_zzprobe_mockgun_"
ENTITY_WRITES = ("create", "update", "delete", "revive", "batch")
MEDIA_WRITES = ("upload", "upload_thumbnail", "upload_filmstrip_thumbnail", "share_thumbnail")
SCHEMA_WRITES = ("schema_field_create", "schema_field_update", "schema_field_delete")


def _probe_lib():
    spec = importlib.util.spec_from_file_location("probe_lib", ROOT / "probes" / "_lib.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)
    return lib


def load_env():
    """The env the probes read: `.env.local` here, else a sibling sg-groundtruth's, over os.environ."""
    lib = _probe_lib()
    try:
        return lib.load_env()
    except SystemExit:
        raise pytest.UsageError("Add .env.local here or in a sibling sg-groundtruth to run --live.")


def need(env, key):
    """The value of ``key``, or a usage error naming the key and never its value."""
    value = (env.get(key) or "").strip()
    if not value:
        raise pytest.UsageError("Set %s in .env.local to run --live." % key)
    return value


# Collection


def _is_conformance(item):
    return HERE in Path(str(item.fspath)).resolve().parents


def pytest_collection_modifyitems(config, items):
    missing = [item.nodeid for item in items if _is_conformance(item) and item.get_closest_marker("finding") is None]
    if missing:
        raise pytest.UsageError(
            "Add @pytest.mark.finding(\"NNN\") to each conformance test. Missing on:\n  " + "\n  ".join(missing))


# Results


class _Results:
    """Each conformance test's markers and outcome, written as JSON when the session ends."""

    def __init__(self):
        self.tests = {}
        self.site_version = None
        self.connected = False

    def record(self, item, outcome):
        finding = item.get_closest_marker("finding")
        cell = item.get_closest_marker("cell")
        self.tests[item.nodeid] = {
            "finding": finding.args[0],
            "api3": finding.kwargs.get("api3"),
            "cell": list(cell.args) if cell else None,
            "outcome": outcome,
        }


_RESULTS = _Results()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if not _is_conformance(item):
        return
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        state = "skip" if report.skipped else ("pass" if report.passed else "fail")
        _RESULTS.record(item, state)
    elif report.when == "teardown" and report.failed:
        _RESULTS.record(item, "fail")


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    paths = []
    if config.getoption("--conformance-out"):
        paths.append(Path(config.getoption("--conformance-out")))
    if config.getoption("--live") and _RESULTS.connected:
        paths.append(LIVE_RESULTS)
    if not paths:
        return
    payload = {
        "target": "live" if config.getoption("--live") else "mock",
        "site_version": _RESULTS.site_version,
        "date": datetime.date.today().isoformat(),
        "tests": _RESULTS.tests,
    }
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")


# Clients


class ReadOnly:
    """A client whose write methods refuse, so every write goes through `made` or `fields`."""

    def __init__(self, client):
        self._client = client

    def __getattr__(self, name):
        if name in ENTITY_WRITES + MEDIA_WRITES + SCHEMA_WRITES:
            raise AttributeError("Write through the made or fields fixture, not site.%s." % name)
        return getattr(self._client, name)


@pytest.fixture(scope="session")
def live(request):
    """True when the suite targets a live site."""
    return request.config.getoption("--live")


@pytest.fixture(scope="session")
def live_client(live):
    """The shotgun_api3 client on the site in .env.local, made once per session."""
    if not live:
        return None
    import shotgun_api3

    env = load_env()
    client = shotgun_api3.Shotgun(need(env, "FPT_API_SITE_URL"), script_name=need(env, "FPT_API_SCRIPT_NAME"),
                                  api_key=need(env, "FPT_API_API_KEY"))
    version = client.info().get("version")
    _RESULTS.connected = True
    _RESULTS.site_version = ".".join(str(v) for v in version) if version else None
    return client


@pytest.fixture
def client(live, live_client):
    """The raw client: a fresh mock on the bundled schema, or the live client."""
    if live:
        return live_client
    Mockgun.set_schema_paths(*schemas.paths())
    return Mockgun("https://mock.example.com", script_name="conformance", api_key="x")


@pytest.fixture
def site(client):
    """The target for reads: the mock or a shotgun_api3.Shotgun. Its write methods refuse."""
    return ReadOnly(client)


@pytest.fixture
def sandbox(live, client):
    """The project writes go to: FPT_PROBE_SANDBOX_PROJECT on a live site, a fresh Project on the mock."""
    if not live:
        return client.create("Project", {"name": "conformance sandbox"})
    name = need(load_env(), "FPT_PROBE_SANDBOX_PROJECT")
    project = client.find_one("Project", [["name", "is", name]], ["name"])
    if project is None:
        raise pytest.UsageError("No Project named in FPT_PROBE_SANDBOX_PROJECT on this site. Create it first.")
    return {"type": "Project", "id": project["id"]}


@pytest.fixture(scope="session")
def run_token(live):
    """A string unique to this run on a live site, so names do not meet rows a past run left."""
    return "r%x" % int(time.time()) if live else "r0"


# Writes


MISSING_IDS = (0, 999999999)


class Created:
    """Rows a test made, deleted in reverse order when it finishes.

    A create must link the sandbox project. A TaskDependency must join two Tasks made here, a Reply a Note made here.
    An update, delete or revive must name a row made here.
    """

    def __init__(self, client, sandbox):
        self.client, self.sandbox, self.rows = client, sandbox, []

    def _check_create(self, entity_type, data):
        if entity_type == "TaskDependency":
            for key in ("task", "dependent_task"):
                self._check_known("Task", (data.get(key) or {}).get("id"))
            return
        if entity_type == "Reply":
            self._check_known("Note", (data.get("entity") or {}).get("id"))
            return
        project = data.get("project") or {}
        if entity_type == "Project" or project.get("type") != "Project" or project.get("id") != self.sandbox["id"]:
            raise ValueError("A create must set project to the sandbox project.")

    def _check_known(self, entity_type, entity_id):
        if (entity_type, entity_id) not in self.rows:
            raise ValueError("Write only to rows this test made: %s %s is not one." % (entity_type, entity_id))

    def track(self, entity_type, entity_id):
        """Record a row the site made for a write here, such as an upload's Attachment, so cleanup deletes it."""
        if (entity_type, entity_id) not in self.rows:
            self.rows.append((entity_type, entity_id))

    def create(self, entity_type, data, return_fields=None):
        self._check_create(entity_type, data)
        row = self.client.create(entity_type, data, return_fields)
        self.rows.append((entity_type, row["id"]))
        return row

    def refused(self, method, *args):
        """Send a write the site refuses and return its exception. A write that succeeds is undone and fails the test.

        A refused create may omit the sandbox project. An update or delete names a row made here or a missing id.
        """
        requests = args[0] if method == "batch" else [
            {"request_type": method, "entity_type": args[0], "data": args[1]} if method == "create"
            else {"request_type": method, "entity_type": args[0], "entity_id": args[1]}]
        for r in requests:
            if r["request_type"] == "create":
                if r["entity_type"] == "Project" or (r["data"].get("project") not in (None, self.sandbox)
                                                     and r["entity_type"] != "TaskDependency"):
                    raise ValueError("A refused create must name the sandbox project or none.")
            elif r["entity_id"] not in MISSING_IDS:
                self._check_known(r["entity_type"], r["entity_id"])
        try:
            result = getattr(self.client, method)(*args)
        except Exception as e:  # noqa: BLE001
            return e
        results = result if method == "batch" else [result]
        for r, row in zip(requests, results):
            if r["request_type"] == "create":
                self.rows.append((r["entity_type"], row["id"]))
        raise AssertionError("The %s was accepted. The site refuses it." % method)

    def update(self, entity_type, entity_id, data, **kwargs):
        self._check_known(entity_type, entity_id)
        for key in data:
            if "." in key:
                link = self.client.find_one(entity_type, [["id", "is", entity_id]], [key.split(".")[0]])
                target = link[key.split(".")[0]] or {}
                self._check_known(target.get("type"), target.get("id"))
        return self.client.update(entity_type, entity_id, data, **kwargs)

    def delete(self, entity_type, entity_id):
        self._check_known(entity_type, entity_id)
        return self.client.delete(entity_type, entity_id)

    def revive(self, entity_type, entity_id):
        self._check_known(entity_type, entity_id)
        return self.client.revive(entity_type, entity_id)

    def batch(self, requests):
        for r in requests:
            if r["request_type"] == "create":
                self._check_create(r["entity_type"], r["data"])
            else:
                self._check_known(r["entity_type"], r["entity_id"])
        results = self.client.batch(requests)
        for r, result in zip(requests, results):
            if r["request_type"] == "create":
                self.rows.append((r["entity_type"], result["id"]))
        return results

    def upload(self, entity_type, entity_id, path, **kwargs):
        """Upload to a row made here. The Attachment the site makes is deleted on cleanup."""
        self._check_known(entity_type, entity_id)
        attachment_id = self.client.upload(entity_type, entity_id, path, **kwargs)
        self.track("Attachment", attachment_id)
        return attachment_id

    def upload_thumbnail(self, entity_type, entity_id, path):
        self._check_known(entity_type, entity_id)
        return self.client.upload_thumbnail(entity_type, entity_id, path)

    def share_thumbnail(self, entities, source_entity):
        for entity in entities + [source_entity]:
            self._check_known(entity["type"], entity["id"])
        return self.client.share_thumbnail(entities, source_entity=source_entity)

    def cleanup(self):
        """Delete every row made here, newest first.

        A row already deleted answers False and is skipped. A row the site erased, such as an edge a template
        re-apply replaced, answers `does not exist` and is skipped.
        """
        errors = []
        for entity_type, entity_id in reversed(self.rows):
            try:
                self.client.delete(entity_type, entity_id)
            except Exception as e:  # noqa: BLE001
                if "does not exist" in str(e):
                    continue
                errors.append("%s %s: %s" % (entity_type, entity_id, e))
        self.rows = []
        if errors:
            raise RuntimeError("Rows left behind:\n" + "\n".join(errors))


@pytest.fixture
def made(client, sandbox):
    """The write path for rows: creates in the sandbox project, deletes them all on teardown."""
    created = Created(client, sandbox)
    yield created
    created.cleanup()


class Fields:
    """Schema fields a test made, deleted in reverse order when it finishes.

    A deleted field's name stays taken on a live site, so each code must start with sg_zzprobe_mockgun_.
    """

    def __init__(self, client):
        self.client, self.made = client, []

    def create(self, entity_type, data_type, display_name, properties=None):
        code = "sg_" + "".join(c if c.isalnum() else "_" for c in display_name.lower())
        if not code.startswith(FIELD_PREFIX):
            raise ValueError("Name a probe field zzprobe mockgun ..., so its code starts with %s." % FIELD_PREFIX)
        made = self.client.schema_field_create(entity_type, data_type, display_name, properties)
        self.made.append((entity_type, made))
        return made

    def _check_known(self, entity_type, field_name):
        if (entity_type, field_name) not in self.made:
            raise ValueError("Write only to fields this test made: %s.%s is not one." % (entity_type, field_name))

    def update(self, entity_type, field_name, properties):
        self._check_known(entity_type, field_name)
        return self.client.schema_field_update(entity_type, field_name, properties)

    def delete(self, entity_type, field_name):
        self._check_known(entity_type, field_name)
        self.made.remove((entity_type, field_name))
        return self.client.schema_field_delete(entity_type, field_name)

    def cleanup(self):
        """Delete every field made here, newest first."""
        for entity_type, field_name in reversed(self.made):
            self.client.schema_field_delete(entity_type, field_name)
        self.made = []


@pytest.fixture
def fields(request, live, client):
    """The write path for schema fields. On a live site it runs only with --live-schema."""
    if live and not request.config.getoption("--live-schema"):
        pytest.skip("Schema field writes run live only with --live-schema.")
    made = Fields(client)
    yield made
    made.cleanup()
