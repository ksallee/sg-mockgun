"""api3 054: upload() to a field that takes no file, and to an entity that does not exist."""
import os
import _lib
import _media

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("054 writes: run with --write")
project = _lib.sandbox(sg, env)
png, txt = _media.files()
missing_txt = os.path.join(os.path.dirname(txt), "probe_054_missing.txt")
os.rename(txt, missing_txt)
out = {
    "s3_direct_uploads_enabled": sg.server_info.get("s3_direct_uploads_enabled"),
    "s3_enabled_upload_types": sg.server_info.get("s3_enabled_upload_types"),
    "description_data_type": sg.schema_field_read("Version", "description")["description"]["data_type"]["value"],
}
with _lib.Created(sg) as made:
    v = made.add(sg.create("Version", {"project": project, "code": "zzprobe mockgun 054"}))
    out["upload_to_text_field"] = r = _lib.ask(sg.upload, "Version", v["id"], png, field_name="description")
    if isinstance(r.get("ok"), int):
        made.add({"type": "Attachment", "id": r["ok"]})
    out["upload_to_missing_field"] = r = _lib.ask(sg.upload, "Version", v["id"], png, field_name="sg_nope_054")
    if isinstance(r.get("ok"), int):
        made.add({"type": "Attachment", "id": r["ok"]})
    out["version_after"] = sg.find_one("Version", [["id", "is", v["id"]]], ["description", "image"])
    linked = sg.find("Attachment", [["attachment_links", "is", {"type": "Version", "id": v["id"]}]], ["filename"])
    out["attachments_linked_after"] = linked
    for a in linked:
        made.add(a)
    out["upload_to_missing_entity"] = r = _lib.ask(sg.upload, "Version", 999999999, missing_txt)
    if isinstance(r.get("ok"), int):
        made.add({"type": "Attachment", "id": r["ok"]})
    orphans = sg.find("Attachment", [["filename", "is", "probe_054_missing.txt"]], ["attachment_links", "project"])
    out["attachments_named_missing_txt"] = orphans
    for a in orphans:
        made.add(a)
    out["upload_missing_entity_type"] = _lib.ask(sg.upload, "NotAType", 1, png)
    out["upload_empty_path"] = _lib.ask(sg.upload, "Version", v["id"], "/nonexistent/probe.png")

_lib.emit("054_upload_refused", _media.shapes(out), env, sg)
