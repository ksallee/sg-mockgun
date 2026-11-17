"""batch: atomic on a failing request? Results order? A create missing `project` inside a batch?"""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("this probe writes: pass --write")
proj = _lib.sandbox(sg, env)
out = {}


def count(code):
    return len(sg.find("Shot", [["project", "is", proj], ["code", "is", code]]))


with _lib.Created(sg) as made:
    shot = made.add(sg.create("Shot", {"project": proj, "code": "zzprobe063_base", "description": "before"}))
    for name, bad in (
        ("update id 0", {"request_type": "update", "entity_type": "Shot", "entity_id": 0, "data": {"description": "x"}}),
        ("update id 999999999", {"request_type": "update", "entity_type": "Shot", "entity_id": 999999999, "data": {"description": "x"}}),
        ("delete id 999999999", {"request_type": "delete", "entity_type": "Shot", "entity_id": 999999999}),
        ("create status zz_bad", {"request_type": "create", "entity_type": "Shot", "data": {"project": proj, "code": "zzprobe063_bad", "sg_status_list": "zz_bad"}}),
    ):
        reqs = [
            {"request_type": "create", "entity_type": "Shot", "data": {"project": proj, "code": "zzprobe063_a"}},
            {"request_type": "update", "entity_type": "Shot", "entity_id": shot["id"], "data": {"description": "after"}},
            bad,
        ]
        r = _lib.ask(sg.batch, reqs)
        if "ok" in r:
            for row in r["ok"]:
                if isinstance(row, dict) and row.get("type") == "Shot" and row.get("id") != shot["id"]:
                    made.add(row)
        out["batch create, update, %s" % name] = r
        out["  after: zzprobe063_a rows"] = count("zzprobe063_a")
        out["  after: base description"] = sg.find_one("Shot", [["id", "is", shot["id"]]], ["description"])["description"]
        out["after %s" % name] = {"created rows": count("zzprobe063_a"),
                                  "base description": sg.find_one("Shot", [["id", "is", shot["id"]]], ["description"])["description"]}
    del out["  after: zzprobe063_a rows"], out["  after: base description"]

    reqs = [
        {"request_type": "update", "entity_type": "Shot", "entity_id": shot["id"], "data": {"description": "u1"}},
        {"request_type": "create", "entity_type": "Shot", "data": {"project": proj, "code": "zzprobe063_o1"}},
        {"request_type": "update", "entity_type": "Shot", "entity_id": shot["id"], "data": {"description": "u2"}},
        {"request_type": "create", "entity_type": "Shot", "data": {"project": proj, "code": "zzprobe063_o2"}},
        {"request_type": "delete", "entity_type": "Shot", "entity_id": 0},
    ]
    reqs.pop()  # keep the order batch successful
    r = _lib.ask(sg.batch, reqs)
    if "ok" in r:
        for row in r["ok"]:
            if row.get("id") != shot["id"]:
                made.add(row)
    out["order batch [update, create, update, create]"] = r

    tmp = made.add(sg.create("Shot", {"project": proj, "code": "zzprobe063_del"}))
    r = _lib.ask(sg.batch, [{"request_type": "delete", "entity_type": "Shot", "entity_id": tmp["id"]}])
    out["batch delete row"] = r
    if "ok" in r:
        made.rows.remove(("Shot", tmp["id"]))

    for t in ("Shot", "Version"):
        out["%s single create no project" % t] = _lib.ask(sg.create, t, {"code": "zzprobe063_np"})
        r = _lib.ask(sg.batch, [{"request_type": "create", "entity_type": t, "data": {"code": "zzprobe063_np"}}])
        out["%s batch create no project" % t] = r
        if "ok" in r and r["ok"]:
            nid = r["ok"][0]["id"]
            made.add({"type": t, "id": nid})
            out["%s find_one by id" % t] = sg.find_one(t, [["id", "is", nid]], ["code", "project"])
            out["%s find by code, site-wide" % t] = len(sg.find(t, [["code", "is", "zzprobe063_np"]]))
            out["%s update by id" % t] = _lib.ask(sg.update, t, nid, {"description": "x"})
_lib.emit("063_batch", out, env, sg)
