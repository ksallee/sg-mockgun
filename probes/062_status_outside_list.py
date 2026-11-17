"""`sg_status_list` set to a value outside the list, on create and on update."""
import _lib

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("this probe writes: pass --write")
proj = _lib.sandbox(sg, env)
out = {}
with _lib.Created(sg) as made:
    for t in ("Shot", "Version"):
        r = _lib.ask(sg.create, t, {"project": proj, "code": "zzprobe062", "sg_status_list": "zz_bad"})
        if "ok" in r:
            made.add(r["ok"])
        out["%s create zz_bad" % t] = r
        out["%s rows after" % t] = len(sg.find(t, [["project", "is", proj], ["code", "is", "zzprobe062"]]))
        row = made.add(sg.create(t, {"project": proj, "code": "zzprobe062_ok"}))
        st = sg.find_one(t, [["id", "is", row["id"]]], ["sg_status_list"])["sg_status_list"]
        out["%s update zz_bad" % t] = _lib.ask(sg.update, t, row["id"], {"sg_status_list": "zz_bad"})
        out["%s status before/after" % t] = [st, sg.find_one(t, [["id", "is", row["id"]]], ["sg_status_list"])["sg_status_list"]]
        out["%s update ''" % t] = _lib.ask(sg.update, t, row["id"], {"sg_status_list": ""})
        out["%s update None" % t] = _lib.ask(sg.update, t, row["id"], {"sg_status_list": None})
        hidden = sg.schema_field_read(t, "sg_status_list", project_entity=proj)["sg_status_list"]["properties"]["hidden_values"]["value"]
        if hidden:
            out["%s update hidden in project %s" % (t, hidden[0])] = _lib.ask(sg.update, t, row["id"], {"sg_status_list": hidden[0]})
        out["%s status end" % t] = sg.find_one(t, [["id", "is", row["id"]]], ["sg_status_list"])["sg_status_list"]
_lib.emit("062_status_outside_list", out, env, sg)
