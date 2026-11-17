"""Delete a Task that a Version links to in `sg_task`: is `sg_task` nulled? Does revive restore it?"""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("this probe writes: pass --write")
proj = _lib.sandbox(sg, env)
out = {}


def read(v, t):
    return {"Version.sg_task": sg.find_one("Version", [["id", "is", v["id"]]], ["sg_task"])["sg_task"],
            "find Version sg_task is task": len(sg.find("Version", [["sg_task", "is", t]])),
            "find_one Task": sg.find_one("Task", [["id", "is", t["id"]]], ["content"])}


with _lib.Created(sg) as made:
    task = made.add(sg.create("Task", {"project": proj, "content": "zzprobe065"}))
    ver = made.add(sg.create("Version", {"project": proj, "code": "zzprobe065", "sg_task": task}))
    out["before"] = read(ver, task)
    out["delete Task"] = _lib.ask(sg.delete, "Task", task["id"])
    out["after delete"] = read(ver, task)
    out["revive Task"] = _lib.ask(sg.revive, "Task", task["id"])
    out["after revive"] = read(ver, task)
_lib.emit("065_task_delete_version", out, env, sg)
