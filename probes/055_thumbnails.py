"""api3 055: upload_thumbnail and upload_filmstrip_thumbnail, their returns and the image fields after."""
import time
import _lib
import _media

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("055 writes: run with --write")
project = _lib.sandbox(sg, env)
png, _txt = _media.files()
FIELDS = ["image", "filmstrip_image"]
out = {}


def poll(v, seconds=90):
    """Read image and filmstrip_image until neither is a transient placeholder; record each change."""
    seen, start, last = [], time.time(), None
    while time.time() - start < seconds:
        row = sg.find_one("Version", [["id", "is", v["id"]]], FIELDS)
        now = {k: _media.url_shape(row[k]) for k in FIELDS}
        if now != last:
            seen.append({"after_s": round(time.time() - start, 1), **now})
            last = now
        if not any(isinstance(x, str) and "/transient/" in x for x in now.values()):
            break
        time.sleep(2)
    return seen


with _lib.Created(sg) as made:
    v = made.add(sg.create("Version", {"project": project, "code": "zzprobe mockgun 055"}))
    out["upload_thumbnail"] = r = _lib.ask(sg.upload_thumbnail, "Version", v["id"], png)
    out["thumbnail_attachment_row"] = sg.find_one("Attachment", [["id", "is", r.get("ok")]], ["this_file", "attachment_links", "image"]) if isinstance(r.get("ok"), int) else None
    out["image_after_thumbnail"] = poll(v)
    out["upload_filmstrip_thumbnail"] = r = _lib.ask(sg.upload_filmstrip_thumbnail, "Version", v["id"], png)
    out["filmstrip_attachment_row"] = sg.find_one("Attachment", [["id", "is", r.get("ok")]], ["this_file", "attachment_links"]) if isinstance(r.get("ok"), int) else None
    out["after_filmstrip"] = poll(v)
    linked = sg.find("Attachment", [["attachment_links", "is", {"type": "Version", "id": v["id"]}]], ["filename"])
    out["attachments_linked_after"] = linked
    for a in linked:
        made.add(a)
    out["upload_thumbnail_missing_entity"] = _lib.ask(sg.upload_thumbnail, "Version", 999999999, png)

_lib.emit("055_thumbnails", _media.shapes(out), env, sg)
