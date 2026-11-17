"""025: where None sorts in find order, ascending and descending, per data type. Needs --write."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("needs --write")
project = _lib.sandbox(sg, env)

ROWS = [  # (code, description, frame_count, sg_status_list)
    ("zzprobe_025_b", "b", 5, "rev"),
    ("zzprobe_025_none", None, None, None),
    ("zzprobe_025_a", "a", 1, "na"),
    ("zzprobe_025_empty", "", 0, "apr"),
]
answers = {}
with _lib.Created(sg) as made:
    shot = made.add(sg.create("Shot", {"project": project, "code": "zzprobe_025_shot"}))
    made_ids = []
    for code, desc, frames, status in ROWS:
        data = {"project": project, "code": code, "description": desc, "frame_count": frames}
        if status:
            data["sg_status_list"] = status
        if code.endswith("_b"):
            data["entity"] = shot
        v = made.add(sg.create("Version", data))
        if status is None:
            answers["status None on create: written"] = _lib.ask(sg.update, "Version", v["id"], {"sg_status_list": None})
        made_ids.append(v["id"])
    F = [["id", "in", made_ids]]
    stored = {r["id"]: r for r in sg.find("Version", F, ["code", "description", "frame_count", "sg_status_list", "entity"])}
    answers["stored"] = {r["code"]: [r["description"], r["frame_count"], r["sg_status_list"], bool(r["entity"])]
                         for r in stored.values()}
    for field in ("description", "frame_count", "sg_status_list", "entity", "entity.Shot.code"):
        for direction in ("asc", "desc"):
            rows = sg.find("Version", F, ["code"], order=[{"field_name": field, "direction": direction}])
            answers["%s %s" % (field, direction)] = [r["code"].replace("zzprobe_025_", "") for r in rows]
_lib.emit("025_find_order_none", answers, env, sg)
