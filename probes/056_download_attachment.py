"""api3 056: download_attachment on each accepted shape, to bytes and to a path, and on a missing id."""
import os
import _lib
import _media

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("056 writes: run with --write")
project = _lib.sandbox(sg, env)
_png, txt = _media.files()
with open(txt, "rb") as f:
    sent = f.read()
out = {"sent_bytes": sent}


def answer(r):
    """Bytes are compared with what was sent; anything else is returned as is."""
    if isinstance(r.get("ok"), bytes):
        return {"ok_type": "bytes", "equal_to_sent": r["ok"] == sent, "len": len(r["ok"])}
    return r


with _lib.Created(sg) as made:
    v = made.add(sg.create("Version", {"project": project, "code": "zzprobe mockgun 056"}))
    aid = sg.upload("Version", v["id"], txt, field_name="sg_uploaded_movie")
    made.add({"type": "Attachment", "id": aid})
    value = sg.find_one("Version", [["id", "is", v["id"]]], ["sg_uploaded_movie"])["sg_uploaded_movie"]
    out["attachment_dict"] = answer(_lib.ask(sg.download_attachment, {"type": "Attachment", "id": aid}))
    out["field_value"] = answer(_lib.ask(sg.download_attachment, value))
    out["id"] = answer(_lib.ask(sg.download_attachment, aid))
    out["attachment_id_kw"] = answer(_lib.ask(sg.download_attachment, attachment_id=aid))
    target = os.path.join(os.path.dirname(txt), "downloaded.txt")
    r = _lib.ask(sg.download_attachment, aid, file_path=target)
    out["id_with_file_path"] = {"returned": r, "returned_is_target": r.get("ok") == target,
                                "file_equal_to_sent": os.path.exists(target) and open(target, "rb").read() == sent}
    out["none"] = _lib.ask(sg.download_attachment, None)
    out["no_argument"] = _lib.ask(sg.download_attachment)
    out["missing_id"] = _lib.ask(sg.download_attachment, 999999999)
    out["missing_attachment_dict"] = _lib.ask(sg.download_attachment, {"type": "Attachment", "id": 999999999})
    out["version_dict"] = _lib.ask(sg.download_attachment, {"type": "Version", "id": v["id"]})
    missing_target = os.path.join(os.path.dirname(txt), "missing.txt")
    out["missing_id_with_file_path"] = _lib.ask(sg.download_attachment, 999999999, file_path=missing_target)
    out["missing_id_file_left_on_disk"] = {"exists": os.path.exists(missing_target),
                                           "size": os.path.getsize(missing_target) if os.path.exists(missing_target) else None}

_lib.emit("056_download_attachment", _media.shapes(out), env, sg)
