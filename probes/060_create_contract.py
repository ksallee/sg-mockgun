"""Is `project` required on a Shot and Version create? Is `code` required, and is it unique?"""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("this probe writes: pass --write")
proj = _lib.sandbox(sg, env)
out = {}
with _lib.Created(sg) as made:
    for t in ("Shot", "Version"):
        out["%s no project, code" % t] = _lib.ask(sg.create, t, {"code": "zzprobe060"})
        out["%s {}" % t] = _lib.ask(sg.create, t, {})
        r = _lib.ask(sg.create, t, {"project": proj})
        if "ok" in r:
            made.add(r["ok"])
            r["read"] = sg.find_one(t, [["id", "is", r["ok"]["id"]]], ["code"])
        out["%s project only" % t] = r
        out["%s code empty" % t] = _lib.ask(sg.create, t, {"project": proj, "code": ""})
        out["%s code None" % t] = _lib.ask(sg.create, t, {"project": proj, "code": None})
        for i in (1, 2):
            r = _lib.ask(sg.create, t, {"project": proj, "code": "zzprobe060_dup"})
            if "ok" in r:
                made.add(r["ok"])
            out["%s dup %d" % (t, i)] = r
        out["%s find dup" % t] = sg.find(t, [["project", "is", proj], ["code", "is", "zzprobe060_dup"]], ["code"])
        out["%s schema code" % t] = {k: sg.schema_field_read(t, "code")["code"][k] for k in ("mandatory", "unique")}
        out["%s schema project mandatory" % t] = sg.schema_field_read(t, "project")["project"]["mandatory"]
    for k in list(out):
        if "no project" in k or "{}" in k:
            r = out[k]
            if "ok" in r:
                made.add(r["ok"])
_lib.emit("060_create_contract", out, env, sg)
