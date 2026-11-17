"""api3 058: share_thumbnail between sandbox Versions, before and after the source thumbnail is ready."""
import time
import _lib
import _media

env = _lib.load_env()
sg = _lib.client(env)
if not _lib.writes_allowed():
    raise SystemExit("058 writes: run with --write")
project = _lib.sandbox(sg, env)
png, _txt = _media.files()
out = {}


def image(v):
    return _media.url_shape(sg.find_one("Version", [["id", "is", v["id"]]], ["image"])["image"])


def wait_ready(v, seconds=120):
    start = time.time()
    while time.time() - start < seconds:
        if "/transient/" not in (image(v) or "/transient/"):
            return round(time.time() - start, 1)
        time.sleep(3)
    return None


with _lib.Created(sg) as made:
    a, b, c, d = (made.add(sg.create("Version", {"project": project, "code": "zzprobe mockgun 058 %s" % n})) for n in "abcd")
    out["upload_thumbnail_a"] = r = _lib.ask(sg.upload_thumbnail, "Version", a["id"], png)
    out["share_before_ready"] = _lib.ask(sg.share_thumbnail, [{"type": "Version", "id": b["id"]}], source_entity=a)
    out["b_image_after_refused_share"] = image(b)
    out["a_ready_after_s"] = wait_ready(a)
    out["a_image"] = image(a)
    out["share_source_entity"] = _lib.ask(sg.share_thumbnail, [{"type": "Version", "id": b["id"]}], source_entity=a)
    out["b_image_after_share"] = image(b)
    raw = [sg.find_one("Version", [["id", "is", x["id"]]], ["image"])["image"] for x in (a, b)]
    out["b_image_equals_a_image"] = raw[0] == raw[1]
    out["b_image_path_equals_a_image_path"] = raw[0].split("?")[0] == raw[1].split("?")[0]
    out["share_thumbnail_path"] = _lib.ask(sg.share_thumbnail, [{"type": "Version", "id": c["id"]}, {"type": "Version", "id": d["id"]}], thumbnail_path=png)
    out["c_d_image_right_after"] = [image(c), image(d)]
    out["share_source_without_thumbnail"] = _lib.ask(sg.share_thumbnail, [{"type": "Version", "id": b["id"]}], source_entity=d)
    out["b_image_after_share_from_imageless_source"] = image(b)
    out["share_missing_target"] = _lib.ask(sg.share_thumbnail, [{"type": "Version", "id": 999999999}], source_entity=a)
    for v in (a, b, c, d):
        for att in sg.find("Attachment", [["attachment_links", "is", {"type": "Version", "id": v["id"]}]], ["filename"]):
            made.add(att)

_lib.emit("058_share_thumbnail", _media.shapes(out), env, sg)
