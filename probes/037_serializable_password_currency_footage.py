"""037 serializable_password_currency_footage: a write to Task.splits, and which stock fields have the rarer types."""
import uuid

import _lib

RARE = ("password", "currency", "footage", "serializable")
SPLITS = [
    [{"start": "2026-01-05", "end": "2026-01-06"}],
    [],
    [{"start": "2026-01-05", "end": "2026-01-06"}, {"start": "2026-01-08", "end": "2026-01-09"}],
    {"a": 1},
    "hello",
    None,
]


def read(sg, entity, field):
    value = sg.find_one(entity["type"], [["id", "is", entity["id"]]], [field])[field]
    return [value, type(value).__name__]


def schema_scan(sg):
    """Every field of a rarer data type on the site, with its editable flag."""
    found = {data_type: [] for data_type in RARE}
    for entity_type in sorted(sg.schema_entity_read()):
        for name, field in sg.schema_field_read(entity_type).items():
            data_type = field["data_type"]["value"]
            if data_type in found:
                found[data_type].append("%s.%s editable=%s" % (entity_type, name, field["editable"]["value"]))
    return found


def run(sg, project, scan=True):
    marker = "zzprobe_037_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        task = made.add(sg.create("Task", {"project": project, "content": marker, "start_date": "2026-01-05", "due_date": "2026-01-09"}))
        answers["Task.splits new row"] = read(sg, task, "splits")
        for value in SPLITS:
            r = _lib.ask(sg.update, "Task", task["id"], {"splits": value})
            answers["update splits %r" % (value,)] = {"returned": r, "read": read(sg, task, "splits")}
        code = marker + "_c"
        r = _lib.ask(sg.create, "Task", {"project": project, "content": code, "splits": SPLITS[0]})
        if "ok" in r:
            made.add(r["ok"])
            r["read"] = read(sg, r["ok"], "splits")
        r["rows made"] = len(sg.find("Task", [["project", "is", project], ["content", "is", code]]))
        answers["create with splits"] = r
    users = sg.find("HumanUser", [], ["password_proxy"], limit=3)
    answers["HumanUser.password_proxy reads"] = sorted(set(repr(u["password_proxy"]) for u in users))
    if scan:
        answers["fields of rarer types"] = schema_scan(sg)
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    _lib.emit("037 serializable_password_currency_footage", run(sg, _lib.sandbox(sg, env)), env, sg)


if __name__ == "__main__":
    main()
