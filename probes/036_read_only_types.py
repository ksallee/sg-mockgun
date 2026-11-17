"""036 read_only_types: writes to uuid, calculated, summary and pivot_column fields, on create and update."""
import uuid

import _lib

UUID = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"


def read(sg, entity, field):
    value = sg.find_one(entity["type"], [["id", "is", entity["id"]]], [field])[field]
    return [value, type(value).__name__]


def try_create(sg, made, entity_type, data, name_field):
    r = _lib.ask(sg.create, entity_type, data)
    if "ok" in r:
        made.add(r["ok"])
    r["rows made"] = len(sg.find(entity_type, [["project", "is", data["project"]], [name_field, "is", data[name_field]]]))
    return r


def try_update(sg, entity, field, value):
    before = read(sg, entity, field)
    r = _lib.ask(sg.update, entity["type"], entity["id"], {field: value})
    return {"returned": r, "before": before, "after": read(sg, entity, field)}


def run(sg, project):
    marker = "zzprobe_036_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        shot = made.add(sg.create("Shot", {"project": project, "code": marker}))
        task = made.add(sg.create("Task", {"project": project, "content": marker, "entity": shot}))
        asset = made.add(sg.create("Asset", {"project": project, "code": marker}))

        event = sg.find_one("EventLogEntry", [["project", "is", project], ["entity", "is", shot]], ["session_uuid"])
        if event:
            answers["EventLogEntry.session_uuid update"] = try_update(sg, event, "session_uuid", UUID)
            answers["EventLogEntry.session_uuid update None"] = try_update(sg, event, "session_uuid", None)
        answers["EventLogEntry create with session_uuid"] = try_create(sg, made, "EventLogEntry", {
            "project": project, "event_type": "zzprobe_036_Probe", "description": marker, "session_uuid": UUID,
        }, "description")

        answers["Task.workload new row"] = read(sg, task, "workload")
        answers["Task.workload update 5"] = try_update(sg, task, "workload", 5)
        answers["Task.workload update None"] = try_update(sg, task, "workload", None)
        answers["Task create with workload"] = try_create(sg, made, "Task", {"project": project, "content": marker + "_w", "workload": 5}, "content")

        answers["Shot.open_notes_count new row"] = read(sg, shot, "open_notes_count")
        answers["Shot.open_notes_count update 3"] = try_update(sg, shot, "open_notes_count", 3)
        answers["Asset.sg_latest_version new row"] = read(sg, asset, "sg_latest_version")
        answers["Asset.sg_latest_version update None"] = try_update(sg, asset, "sg_latest_version", None)
        answers["Asset create with sg_latest_version None"] = try_create(sg, made, "Asset", {"project": project, "code": marker + "_s", "sg_latest_version": None}, "code")

        answers["Shot.step_0 new row"] = read(sg, shot, "step_0")
        answers["Shot.step_0 update None"] = try_update(sg, shot, "step_0", None)
        answers["Shot create with step_0 None"] = try_create(sg, made, "Shot", {"project": project, "code": marker + "_p", "step_0": None}, "code")
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    _lib.emit("036 read_only_types", run(sg, _lib.sandbox(sg, env)), env, sg)


if __name__ == "__main__":
    main()
