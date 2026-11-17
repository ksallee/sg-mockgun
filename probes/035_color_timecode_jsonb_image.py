"""035 color_timecode_jsonb_image: what Task.color, Sequence.sg_timecode, Note.meta and Version.image take."""
import uuid

import _lib


def read(sg, entity, field):
    value = sg.find_one(entity["type"], [["id", "is", entity["id"]]], [field])[field]
    return [value, type(value).__name__]


def try_create(sg, made, entity_type, project, name_field, name, field, value):
    data = {"project": project, name_field: name, field: value}
    if entity_type == "Note":
        data["content"] = "probe"
    r = _lib.ask(sg.create, entity_type, data)
    if "ok" in r:
        made.add(r["ok"])
        r = {"returned": r["ok"].get(field), "read": read(sg, r["ok"], field)}
    found = sg.find(entity_type, [["project", "is", project], [name_field, "is", name]])
    r["rows made"] = len(found)
    if "raised" in r:
        for row in found:  # api3 creates the row before it uploads an image, then raises
            made.add(row)
    return r


def updates(sg, entity, field, values):
    out = {}
    for value in values:
        r = _lib.ask(sg.update, entity["type"], entity["id"], {field: value})
        out["update %r" % (value,)] = {"returned": r, "read": read(sg, entity, field)}
    return out


def run(sg, project):
    marker = "zzprobe_035_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        task = made.add(sg.create("Task", {"project": project, "content": marker}))
        answers["Task.color new row"] = read(sg, task, "color")
        answers["Task.color"] = updates(sg, task, "color", ["255,0,0", "pipeline_step", "red", "#ff0000", "", None])
        answers["Task.color create 'red'"] = try_create(sg, made, "Task", project, "content", marker + "_c", "color", "red")
        answers["Task.color create None"] = try_create(sg, made, "Task", project, "content", marker + "_n", "color", None)

        seq = made.add(sg.create("Sequence", {"project": project, "code": marker}))
        answers["Sequence.sg_timecode new row"] = read(sg, seq, "sg_timecode")
        answers["Sequence.sg_timecode"] = updates(sg, seq, "sg_timecode", [3600000, -1, "3600000", 1.5, "01:00:00:00", 2 ** 31, None])
        answers["Sequence.sg_timecode create 2**31"] = try_create(sg, made, "Sequence", project, "code", marker + "_big", "sg_timecode", 2 ** 31)

        answers["Note.meta create dict"] = try_create(sg, made, "Note", project, "subject", marker + "_d", "meta", {"a": {"b": [1, 2]}, "n": None})
        answers["Note.meta create list"] = try_create(sg, made, "Note", project, "subject", marker + "_l", "meta", [{"x": 1}, 2])
        answers["Note.meta create string"] = try_create(sg, made, "Note", project, "subject", marker + "_s", "meta", "x")
        note = sg.find_one("Note", [["project", "is", project], ["subject", "is", marker + "_d"]], ["id"])
        if note:
            answers["Note.meta"] = updates(sg, note, "meta", [{"a": 1}, None])

        v = made.add(sg.create("Version", {"project": project, "code": marker}))
        answers["Version.image new row"] = read(sg, v, "image")
        answers["Version.image"] = updates(sg, v, "image", ["https://example.com/a.png", "/tmp/a.png", None])
        answers["Version.image create string"] = try_create(sg, made, "Version", project, "code", marker + "_i", "image", "https://example.com/a.png")
        answers["Version.image create None"] = try_create(sg, made, "Version", project, "code", marker + "_in", "image", None)
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    _lib.emit("035 color_timecode_jsonb_image", run(sg, _lib.sandbox(sg, env)), env, sg)


if __name__ == "__main__":
    main()
