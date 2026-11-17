"""034 multi_entity_none: what a multi_entity field answers to None on create and update."""
import uuid

import _lib


def read(sg, entity, field):
    value = sg.find_one(entity["type"], [["id", "is", entity["id"]]], [field])[field]
    return [value, type(value).__name__]


def rows(sg, project, code):
    return len(sg.find("Shot", [["project", "is", project], ["code", "is", code]]))


def run(sg, project):
    marker = "zzprobe_034_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        v = made.add(sg.create("Shot", {"project": project, "code": marker}))
        w = made.add(sg.create("Shot", {"project": project, "code": marker + "_w"}))
        answers["new row reads shots"] = read(sg, v, "shots")
        link = [{"type": "Shot", "id": w["id"]}]
        sg.update("Shot", v["id"], {"shots": link})
        for value in (None, []):
            r = _lib.ask(sg.update, "Shot", v["id"], {"shots": value})
            answers["update %r" % (value,)] = {"returned": r, "read": [len(x) if isinstance(x, list) else x for x in read(sg, v, "shots")]}
            sg.update("Shot", v["id"], {"shots": link})
        code = marker + "_none"
        r = _lib.ask(sg.create, "Shot", {"project": project, "code": code, "shots": None})
        if "ok" in r:
            made.add(r["ok"])
        answers["create None"] = {"returned": r, "rows made": rows(sg, project, code)}
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    _lib.emit("034 multi_entity_none", run(sg, _lib.sandbox(sg, env)), env, sg)


if __name__ == "__main__":
    main()
