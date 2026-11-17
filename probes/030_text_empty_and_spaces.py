"""030 text_empty_and_spaces: what a text field stores and returns for "" and "  x  "."""
import uuid

import _lib


def read(sg, entity, field):
    value = sg.find_one(entity["type"], [["id", "is", entity["id"]]], [field])[field]
    return [value, type(value).__name__]


def run(sg, project):
    marker = "zzprobe_030_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        a = made.add(sg.create("Shot", {"project": project, "code": marker + "_a", "description": ""}))
        answers["create description ''"] = {"returned": a.get("description"), "read": read(sg, a, "description")}
        b = made.add(sg.create("Shot", {"project": project, "code": marker + "_b", "description": "  x  "}))
        answers["create description '  x  '"] = {"returned": b.get("description"), "read": read(sg, b, "description")}
        r = _lib.ask(sg.update, "Shot", a["id"], {"description": "  x  "})
        answers["update description '  x  '"] = {"returned": r, "read": read(sg, a, "description")}
        r = _lib.ask(sg.update, "Shot", a["id"], {"description": "   "})
        answers["update description '   '"] = {"returned": r, "read": read(sg, a, "description")}
        sg.update("Shot", a["id"], {"description": "y"})
        r = _lib.ask(sg.update, "Shot", a["id"], {"description": ""})
        answers["update description '' over 'y'"] = {"returned": r, "read": read(sg, a, "description")}
        answers["filter description is ''"] = len(sg.find("Shot", [["project", "is", project], ["code", "starts_with", marker], ["description", "is", ""]]))
        answers["filter description is None"] = len(sg.find("Shot", [["project", "is", project], ["code", "starts_with", marker], ["description", "is", None]]))
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    _lib.emit("030 text_empty_and_spaces", run(sg, _lib.sandbox(sg, env)), env, sg)


if __name__ == "__main__":
    main()
