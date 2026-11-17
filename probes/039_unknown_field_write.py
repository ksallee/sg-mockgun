"""039 unknown_field_write: an unknown field name in a create body and in an update body."""
import uuid

import _lib


def run(sg, project):
    marker = "zzprobe_039_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        code = marker + "_c"
        r = _lib.ask(sg.create, "Version", {"project": project, "code": code, "sg_not_a_field": "x"})
        if "ok" in r:
            made.add(r["ok"])
        r["rows made"] = len(sg.find("Version", [["project", "is", project], ["code", "is", code]]))
        answers["create with sg_not_a_field"] = r
        v = made.add(sg.create("Version", {"project": project, "code": marker}))
        r = _lib.ask(sg.update, "Version", v["id"], {"description": "changed", "sg_not_a_field": "x"})
        r["description after"] = sg.find_one("Version", [["id", "is", v["id"]]], ["description"])["description"]
        answers["update with description and sg_not_a_field"] = r
        # A dotted name writes through to the linked row. Link a sandbox Shot: never dot through project.
        shot = made.add(sg.create("Shot", {"project": project, "code": marker}))
        sg.update("Version", v["id"], {"entity": shot})
        r = _lib.ask(sg.update, "Version", v["id"], {"entity.Shot.description": "via dotted"})
        r["Shot.description after"] = sg.find_one("Shot", [["id", "is", shot["id"]]], ["description"])["description"]
        answers["update with entity.Shot.description"] = r
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    _lib.emit("039 unknown_field_write", run(sg, _lib.sandbox(sg, env)), env, sg)


if __name__ == "__main__":
    main()
