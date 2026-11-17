"""032 float_writes: what a float field takes on create and update, and the stored value and Python type."""
import uuid

import _lib

FIELD = "sg_movie_aspect_ratio"
VALUES = (2, "2.5", 1.23456789, 2.0, "abc", True, None)


def read(sg, entity):
    value = sg.find_one(entity["type"], [["id", "is", entity["id"]]], [FIELD])[FIELD]
    return [value, type(value).__name__]


def rows(sg, project, code):
    return len(sg.find("Version", [["project", "is", project], ["code", "is", code]]))


def run(sg, project):
    marker = "zzprobe_032_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        v = made.add(sg.create("Version", {"project": project, "code": marker}))
        answers["new row reads"] = read(sg, v)
        for value in VALUES:
            r = _lib.ask(sg.update, "Version", v["id"], {FIELD: value})
            answers["update %r (%s)" % (value, type(value).__name__)] = {"returned": r, "read": read(sg, v)}
        for i, value in enumerate(VALUES):
            code = "%s_%d" % (marker, i)
            r = _lib.ask(sg.create, "Version", {"project": project, "code": code, FIELD: value})
            if "ok" in r:
                made.add(r["ok"])
                r = {"returned": r["ok"].get(FIELD), "read": read(sg, r["ok"])}
            r["rows made"] = rows(sg, project, code)
            answers["create %r (%s)" % (value, type(value).__name__)] = r
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    _lib.emit("032 float_writes", run(sg, _lib.sandbox(sg, env)), env, sg)


if __name__ == "__main__":
    main()
