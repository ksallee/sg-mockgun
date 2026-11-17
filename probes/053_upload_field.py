"""api3 053: what upload() returns and leaves, to a url field and with no field."""
import _lib
import _media

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("053 writes: run with --write")
project = _lib.sandbox(sg, env)
png, txt = _media.files()
afields = _media.attachment_fields(sg)
out = {"attachment_field_codes": afields}

with _lib.Created(sg) as made:
    v = made.add(sg.create("Version", {"project": project, "code": "zzprobe mockgun 053"}))
    out["upload_movie_field"] = r1 = _lib.ask(sg.upload, "Version", v["id"], png, field_name="sg_uploaded_movie",
                                              display_name="shown name", tag_list="probe_a,probe_b")
    out["upload_no_field"] = r2 = _lib.ask(sg.upload, "Version", v["id"], txt)
    for key, r in (("movie", r1), ("nofield", r2)):
        if "ok" in r and isinstance(r["ok"], int):
            row = sg.find_one("Attachment", [["id", "is", r["ok"]]], afields)
            if row:
                made.add({"type": "Attachment", "id": r["ok"]})
            out["attachment_row_" + key] = row
            out["type_of_return_" + key] = type(r["ok"]).__name__
    out["version_after"] = sg.find_one("Version", [["id", "is", v["id"]]], ["sg_uploaded_movie", "image", "filmstrip_image"])
    linked = sg.find("Attachment", [["attachment_links", "is", {"type": "Version", "id": v["id"]}]], ["id", "this_file", "display_name"])
    out["attachments_linked_to_version"] = linked
    for a in linked:
        if a["id"] not in (r1.get("ok"), r2.get("ok")):
            made.add({"type": "Attachment", "id": a["id"]})
    tags = sg.find("Tag", [["name", "in", ["probe_a", "probe_b"]]], ["name", "created_by"])
    out["tags_named"] = [{"name": t["name"], "created_by_type": t["created_by"]["type"]} for t in tags]
    for t in tags:
        made.add(t)  # tag_list creates site-wide Tag rows; delete them first

_lib.emit("053_upload_field", _media.shapes(out), env, sg)
