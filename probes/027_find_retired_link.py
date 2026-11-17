"""027: a find on a row whose entity and multi_entity links point at a retired row. Needs --write."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("needs --write")
project = _lib.sandbox(sg, env)
FIELDS = ["sg_task", "playlists", "entity"]


def read(v):
    r = sg.find_one("Version", [["id", "is", v["id"]]], FIELDS)
    if not r:
        return None
    return {"sg_task": r["sg_task"] and r["sg_task"]["name"], "playlists": [p["name"] for p in r["playlists"]],
            "entity": r["entity"] and r["entity"]["name"]}


answers = {}
with _lib.Created(sg) as made:
    task = made.add(sg.create("Task", {"project": project, "content": "zzprobe_027_task"}))
    p1 = made.add(sg.create("Playlist", {"project": project, "code": "zzprobe_027_doomed"}))
    p2 = made.add(sg.create("Playlist", {"project": project, "code": "zzprobe_027_kept"}))
    asset = made.add(sg.create("Asset", {"project": project, "code": "zzprobe_027_asset"}))
    v = made.add(sg.create("Version", {"project": project, "code": "zzprobe_027_version",
                                       "sg_task": task, "playlists": [p1, p2], "entity": asset}))
    answers["linked"] = read(v)
    sg.delete("Task", task["id"])
    sg.delete("Playlist", p1["id"])
    answers["after deleting the Task and one Playlist"] = read(v)
    answers["filter sg_task is <retired Task>"] = len(sg.find("Version", [["sg_task", "is", task]], ["id"]))
    answers["filter playlists is <retired Playlist>"] = len(sg.find("Version", [["playlists", "is", p1]], ["id"]))
    answers["Playlist.versions on the retired Playlist, retired_only"] = _lib.ask(
        lambda: [x["name"] for x in sg.find_one("Playlist", [["id", "is", p1["id"]]], ["versions"], retired_only=True)["versions"]])
    sg.revive("Task", task["id"])
    sg.revive("Playlist", p1["id"])
    answers["after revive"] = read(v)
    sg.delete("Asset", asset["id"])
    answers["after deleting the Asset in entity: Version, default"] = read(v)
    answers["after deleting the Asset: Version, retired_only"] = _lib.ask(
        lambda: sg.find_one("Version", [["id", "is", v["id"]]], FIELDS, retired_only=True) is not None)
    sg.revive("Asset", asset["id"])
    answers["after reviving the Asset"] = read(v)
_lib.emit("027_find_retired_link", answers, env, sg)
