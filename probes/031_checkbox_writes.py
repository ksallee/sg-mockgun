"""031 checkbox_writes: an untouched checkbox on a new row, and writes of None and strings."""
import uuid

import _lib


def read(sg, entity, field):
    value = sg.find_one(entity["type"], [["id", "is", entity["id"]]], [field])[field]
    return [value, type(value).__name__]


def rows(sg, project, code):
    return len(sg.find("Version", [["project", "is", project], ["code", "is", code]]))


def run(sg, project):
    marker = "zzprobe_031_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        v = made.add(sg.create("Version", {"project": project, "code": marker}))
        answers["create returns flagged key"] = "flagged" in v
        answers["new row reads flagged"] = read(sg, v, "flagged")
        for value in (None, "true", "false", "True", "yes", "1", 1, 0, True):
            sg.update("Version", v["id"], {"flagged": not value if isinstance(value, bool) else False})
            before = read(sg, v, "flagged")
            r = _lib.ask(sg.update, "Version", v["id"], {"flagged": value})
            answers["update flagged %r" % (value,)] = {"before": before, "returned": r, "read": read(sg, v, "flagged")}
        code = marker + "_none"
        r = _lib.ask(sg.create, "Version", {"project": project, "code": code, "flagged": None})
        if "ok" in r:
            made.add(r["ok"])
        answers["create flagged None"] = {"returned": r, "rows made": rows(sg, project, code)}
        code = marker + "_str"
        r = _lib.ask(sg.create, "Version", {"project": project, "code": code, "flagged": "true"})
        if "ok" in r:
            made.add(r["ok"])
            r["read"] = read(sg, r["ok"], "flagged")
        answers["create flagged 'true'"] = {"returned": r, "rows made": rows(sg, project, code)}
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    _lib.emit("031 checkbox_writes", run(sg, _lib.sandbox(sg, env)), env, sg)


if __name__ == "__main__":
    main()
