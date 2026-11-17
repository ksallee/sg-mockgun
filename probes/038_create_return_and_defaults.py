"""038 create_return_and_defaults: what create returns, the server-set fields, and the defaults of a new row."""
import datetime
import uuid

import _lib

SERVER_SET = ["created_at", "updated_at", "created_by", "updated_by", "cached_display_name"]
PAST = datetime.datetime(2020, 1, 2, 3, 4, 5)


def describe(value):
    if isinstance(value, dict) and "type" in value:
        return {"type": value["type"], "keys": sorted(value)}
    return [repr(value) if isinstance(value, datetime.datetime) else value, type(value).__name__]


def run(sg, project, script_name=None):
    marker = "zzprobe_038_" + uuid.uuid4().hex[:6]
    answers = {}
    with _lib.Created(sg) as made:
        v = made.add(sg.create("Version", {"project": project, "code": marker}))
        answers["create, no return_fields: keys"] = sorted(v)
        answers["create, no return_fields: values"] = {k: describe(v[k]) for k in sorted(v)}
        w = made.add(sg.create("Version", {"project": project, "code": marker + "_r"}, return_fields=SERVER_SET))
        answers["create, return_fields server-set"] = {k: describe(w.get(k)) for k in sorted(w)}
        row = sg.find_one("Version", [["id", "is", v["id"]]], SERVER_SET)
        answers["read server-set"] = {k: describe(row[k]) for k in SERVER_SET}
        answers["created_by == updated_by"] = row["created_by"] == row["updated_by"] and row["created_by"] is not None
        creator = row["created_by"] or {}
        user = creator and sg.find_one(creator["type"], [["id", "is", creator["id"]]], ["firstname"])
        if script_name is not None and user:
            answers["created_by is the script's ApiUser (name matches)"] = script_name in (user.get("firstname"), row["created_by"].get("name"))

        code = marker + "_past"
        r = _lib.ask(sg.create, "Version", {"project": project, "code": code, "created_at": PAST})
        if "ok" in r:
            made.add(r["ok"])
            r = {"returned created_at": describe(r["ok"].get("created_at")),
                 "read created_at": describe(sg.find_one("Version", [["id", "is", r["ok"]["id"]]], ["created_at"])["created_at"])}
        answers["create with created_at 2020-01-02 03:04:05"] = r
        for field in ("created_at", "updated_at"):
            answers["update %s" % field] = _lib.ask(sg.update, "Version", v["id"], {field: PAST})

        defaults = {}
        fresh = sg.find_one("Version", [["id", "is", v["id"]]], ["frame_count", "flagged", "sg_movie_aspect_ratio"])
        defaults.update(("Version." + k, describe(fresh[k])) for k in ("frame_count", "flagged", "sg_movie_aspect_ratio"))
        shot = made.add(sg.create("Shot", {"project": project, "code": marker}))
        for k in ("sg___complete", "sg_turnover_date", "sg_cut_order"):
            r = _lib.ask(sg.find_one, "Shot", [["id", "is", shot["id"]]], [k])
            defaults["Shot." + k] = describe(r["ok"].get(k)) if "ok" in r else r
        task = made.add(sg.create("Task", {"project": project, "content": marker}))
        fields = ["start_date", "due_date", "duration", "color"]
        fresh = sg.find_one("Task", [["id", "is", task["id"]]], fields)
        defaults.update(("Task." + k, describe(fresh.get(k))) for k in fields)
        seq = made.add(sg.create("Sequence", {"project": project, "code": marker}))
        r = _lib.ask(sg.find_one, "Sequence", [["id", "is", seq["id"]]], ["sg_timecode"])
        defaults["Sequence.sg_timecode"] = describe(r["ok"].get("sg_timecode")) if "ok" in r else r
        answers["defaults on a new row"] = defaults
    return answers


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    if not _lib.writes_allowed():
        raise SystemExit("run with --write: this probe writes sandbox rows")
    project = _lib.sandbox(sg, env)
    _lib.emit("038 create_return_and_defaults", run(sg, project, env.get("FPT_API_SCRIPT_NAME")), env, sg)


if __name__ == "__main__":
    main()
