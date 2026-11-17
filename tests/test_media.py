"""upload, thumbnails, download and share_thumbnail, shaped like api3 answers 053 to 058."""

import pickle

import pytest
from shotgun_api3 import ShotgunError, ShotgunFileDownloadError, ShotgunThumbnailNotReady

from sg_mockgun import Shotgun, schemas

TRANSIENT = "https://mock.example.com/images/status/transient/thumbnail_pending.png"
TXT = b"sg-mockgun probe file\n"


@pytest.fixture
def sg():
    Shotgun.set_schema_paths(*schemas.paths())
    return Shotgun("https://mock.example.com", script_name="probe-script", api_key="y")


@pytest.fixture
def files(tmp_path):
    png = tmp_path / "probe.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    txt = tmp_path / "probe.txt"
    txt.write_bytes(TXT)
    return str(png), str(txt)


@pytest.fixture
def version(sg):
    project = sg.create("Project", {"name": "sandbox"})
    return sg.create("Version", {"project": project, "code": "v001"})


def _read(sg, entity_type, entity_id, fields):
    return sg.find_one(entity_type, [["id", "is", entity_id]], fields)


def _refusal(path, reason):
    return ("Could not upload file successfully, but not sure why.\nPath: %s\n"
            "Url: https://mock.example.com/upload/api_link_file\nError: 0\n%s\n" % (path, reason))


# api3 053
def test_upload_to_url_field_returns_attachment_id_and_sets_field(sg, files, version):
    png, _ = files
    aid = sg.upload("Version", version["id"], png, field_name="sg_uploaded_movie",
                    display_name="shown name", tag_list="probe_a,probe_b")
    assert isinstance(aid, int)
    row = _read(sg, "Attachment", aid, ["attachment_links", "this_file", "filename", "original_fname",
                                        "display_name", "file_size", "file_extension", "image",
                                        "image_source_entity", "processing_status", "tags", "project"])
    assert row["attachment_links"] == [{"type": "Version", "id": version["id"], "name": "v001"}]
    this_file = row["this_file"]
    assert {k: this_file[k] for k in ("name", "content_type", "link_type", "type", "id")} == {
        "name": "shown name", "content_type": "image/png", "link_type": "upload", "type": "Attachment", "id": aid}
    assert this_file["url"].startswith("https://") and "/probe.png?" in this_file["url"]
    assert "/file_serve/attachment/" not in this_file["url"]
    assert (row["filename"], row["original_fname"], row["display_name"]) == ("probe.png", "probe.png", "shown name")
    assert row["file_size"] is None and row["file_extension"] is None
    assert row["image"] == TRANSIENT
    assert row["image_source_entity"]["id"] == aid
    assert row["processing_status"] == "thumbnail_pending_us"
    assert sorted(t["name"] for t in row["tags"]) == ["probe_a", "probe_b"]
    assert row["project"]["id"] == version["project"]["id"]
    after = _read(sg, "Version", version["id"], ["sg_uploaded_movie", "image", "filmstrip_image"])
    assert after["sg_uploaded_movie"] == this_file
    assert after["image"] == TRANSIENT
    assert after["filmstrip_image"] is None
    assert sorted(t["name"] for t in sg.find("Tag", [], ["name"])) == ["probe_a", "probe_b"]


# api3 053
def test_upload_without_field_links_attachment_and_leaves_entity(sg, files, version):
    _, txt = files
    aid = sg.upload("Version", version["id"], txt)
    row = _read(sg, "Attachment", aid, ["this_file", "display_name", "image", "processing_status"])
    assert row["this_file"]["content_type"] == "text/plain"
    assert row["this_file"]["name"] == "probe.txt"
    assert row["display_name"] == "probe.txt"
    assert row["image"] is None and row["processing_status"] is None
    assert _read(sg, "Version", version["id"], ["sg_uploaded_movie", "image"])["image"] is None
    linked = sg.find("Attachment", [["attachment_links", "is", {"type": "Version", "id": version["id"]}]])
    assert [a["id"] for a in linked] == [aid]


# api3 053
def test_upload_reuses_an_existing_tag(sg, files, version):
    _, txt = files
    tag = sg.create("Tag", {"name": "probe_a"})
    aid = sg.upload("Version", version["id"], txt, tag_list="probe_a")
    assert [t["id"] for t in _read(sg, "Attachment", aid, ["tags"])["tags"]] == [tag["id"]]
    assert len(sg.find("Tag", [])) == 1


# api3 054
@pytest.mark.parametrize("entity_type, entity_id, field_name, reason", [
    ("Version", None, "description", "Column description isn't a valid entity column for Version"),
    ("Version", None, "sg_nope_054", "Column sg_nope_054 isn't a valid entity column for Version"),
    ("Version", 999999999, None, "entity with entity_id 999999999 and of entity_type Version not found"),
    ("NotAType", 1, None, "entity_type NotAType is not a valid class"),
])
def test_upload_refusals(sg, files, version, entity_type, entity_id, field_name, reason):
    png, _ = files
    with pytest.raises(ShotgunError) as e:
        sg.upload(entity_type, entity_id or version["id"], png, field_name=field_name)
    assert str(e.value) == _refusal(png, reason)
    assert sg.find("Attachment", []) == []


# api3 054
def test_upload_path_checks(sg, version, tmp_path):
    with pytest.raises(ShotgunError) as e:
        sg.upload("Version", version["id"], "/nonexistent/probe.png")
    assert str(e.value) == "Path must be a valid file, got '/nonexistent/probe.png'"
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    with pytest.raises(ShotgunError) as e:
        sg.upload("Version", version["id"], str(empty))
    assert str(e.value) == "Path cannot be an empty file: '%s'" % empty


# api3 055
def test_upload_thumbnail_is_transient_until_finalised(sg, files, version):
    png, _ = files
    first = sg.upload_thumbnail("Version", version["id"], png)
    assert isinstance(first, int)
    assert _read(sg, "Attachment", first, ["id"]) is None
    assert sg.find("Attachment", []) == []
    assert _read(sg, "Version", version["id"], ["image"])["image"] == TRANSIENT
    sg.finalize_thumbnails()
    image = _read(sg, "Version", version["id"], ["image"])["image"]
    assert image.startswith("https://") and "/probe_t.jpg?" in image
    second = sg.upload_filmstrip_thumbnail("Version", version["id"], png)
    assert second == first + 1
    after = _read(sg, "Version", version["id"], ["image", "filmstrip_image"])
    assert after["image"] == image
    assert "/probe.png?" in after["filmstrip_image"]


# api3 055
def test_upload_thumbnail_missing_entity(sg, files):
    png, _ = files
    with pytest.raises(ShotgunError) as e:
        sg.upload_thumbnail("Version", 999999999, png)
    assert str(e.value) == _refusal(png, "entity with entity_id 999999999 and of entity_type Version not found")


# api3 056
def test_download_attachment_shapes(sg, files, version, tmp_path):
    _, txt = files
    aid = sg.upload("Version", version["id"], txt, field_name="sg_uploaded_movie")
    value = _read(sg, "Version", version["id"], ["sg_uploaded_movie"])["sg_uploaded_movie"]
    assert sg.download_attachment({"type": "Attachment", "id": aid}) == TXT
    assert sg.download_attachment(value) == TXT
    assert sg.download_attachment(aid) == TXT
    assert sg.download_attachment(attachment_id=aid) == TXT
    target = str(tmp_path / "downloaded.txt")
    assert sg.download_attachment(aid, file_path=target) == target
    assert open(target, "rb").read() == TXT
    assert sg.download_attachment(None) is None


# api3 056
def test_download_keeps_bytes_after_source_is_gone(sg, files, version):
    import os
    _, txt = files
    aid = sg.upload("Version", version["id"], txt)
    os.remove(txt)
    assert sg.download_attachment(aid) == TXT


# api3 056
def test_download_attachment_refusals(sg, tmp_path, version):
    with pytest.raises(TypeError) as e:
        sg.download_attachment()
    assert str(e.value) == ("Missing parameter 'attachment'. Expected a dict, int, NoneType value oran int "
                            "for parameter attachment_id")
    message = "Failed to open https://mock.example.com/file_serve/attachment/999999999\nHTTP Error 404: Not Found"
    for value in (999999999, {"type": "Attachment", "id": 999999999}):
        with pytest.raises(ShotgunFileDownloadError) as e:
            sg.download_attachment(value)
        assert str(e.value) == message
    target = tmp_path / "missing.txt"
    with pytest.raises(ShotgunFileDownloadError):
        sg.download_attachment(999999999, file_path=str(target))
    assert target.exists() and target.stat().st_size == 0
    with pytest.raises(ValueError) as e:
        sg.download_attachment({"type": "Version", "id": version["id"]})
    assert str(e.value) == "Missing 'url' key in Attachment dict"


# api3 056
def test_download_of_deleted_attachment_is_404(sg, files, version):
    _, txt = files
    aid = sg.upload("Version", version["id"], txt)
    sg.delete("Attachment", aid)
    with pytest.raises(ShotgunFileDownloadError):
        sg.download_attachment(aid)


# api3 056
def test_download_local_link_reads_the_file(sg, files):
    _, txt = files
    assert sg.download_attachment({"link_type": "local", "url": "file://" + txt}) == TXT


# api3 057
@pytest.mark.parametrize("value, expected", [
    (42, "https://mock.example.com/file_serve/attachment/42"),
    ({"type": "Attachment", "id": 42}, "https://mock.example.com/file_serve/attachment/42"),
    ({"type": "Attachment", "id": 42, "url": "https://bucket.example.com/a/b.txt?q=1"},
     "https://bucket.example.com/a/b.txt?q=1"),
    ({"link_type": "local", "url": "file:///tmp/x.txt"}, "file:///tmp/x.txt"),
    (None, None),
])
def test_get_attachment_download_url(sg, value, expected):
    assert sg.get_attachment_download_url(value) == expected


# api3 057
@pytest.mark.parametrize("value, exc, message", [
    ({"type": "Version", "id": 42}, ValueError, "Missing 'url' key in Attachment dict"),
    ({"id": 42}, ValueError, "Missing 'url' key in Attachment dict"),
    ("42", TypeError, "Unable to determine download url. Expected dict, int, or NoneType. Instead got <class 'str'>"),
    (0, UnboundLocalError, None),
])
def test_get_attachment_download_url_refusals(sg, value, exc, message):
    with pytest.raises(exc) as e:
        sg.get_attachment_download_url(value)
    if message:
        assert str(e.value) == message


NOT_READY = ("Unable to share thumbnail: 2\nsource_entity image is a transient thumbnail that cannot be shared. "
             "Try again later, when the final thumbnail is available\n")


# api3 058
def test_share_thumbnail(sg, files, version):
    png, _ = files
    project = version["project"]
    a = {"type": "Version", "id": version["id"]}
    b, c, d = (sg.create("Version", {"project": project, "code": n}) for n in ("b", "c", "d"))
    thumb = sg.upload_thumbnail("Version", a["id"], png)
    with pytest.raises(ShotgunThumbnailNotReady) as e:
        sg.share_thumbnail([{"type": "Version", "id": b["id"]}], source_entity=a)
    assert str(e.value) == NOT_READY
    assert _read(sg, "Version", b["id"], ["image"])["image"] is None
    sg.finalize_thumbnails()
    assert sg.share_thumbnail([{"type": "Version", "id": b["id"]}], source_entity=a) == thumb
    image_a = _read(sg, "Version", a["id"], ["image"])["image"]
    assert _read(sg, "Version", b["id"], ["image"])["image"].split("?")[0] == image_a.split("?")[0]
    with pytest.raises(ShotgunThumbnailNotReady):
        sg.share_thumbnail([{"type": "Version", "id": c["id"]}, {"type": "Version", "id": d["id"]}],
                           thumbnail_path=png)
    assert _read(sg, "Version", c["id"], ["image"])["image"] == TRANSIENT
    assert _read(sg, "Version", d["id"], ["image"])["image"] is None
    assert sg.share_thumbnail([{"type": "Version", "id": b["id"]}], source_entity=d) is None
    assert _read(sg, "Version", b["id"], ["image"])["image"] is None
    with pytest.raises(ShotgunError) as e:
        sg.share_thumbnail([{"type": "Version", "id": 999999999}], source_entity=a)
    assert str(e.value) == ("Unable to share thumbnail: 0\n"
                            "Couldn't find Version with 'id'=999999999 in 'entities' parameter\n")


# api3 058
def test_share_thumbnail_client_checks(sg):
    with pytest.raises(ShotgunError) as e:
        sg.share_thumbnail([], source_entity={"type": "Version", "id": 1})
    assert str(e.value) == "'entities' parameter must be a list of entity hashes and may not be empty"
    with pytest.raises(ShotgunError) as e:
        sg.share_thumbnail([{"type": "Version", "id": 1}])
    assert str(e.value) == "You must supply either thumbnail_path OR source_entity."


def test_instance_with_uploads_pickles_and_snapshots(sg, files, version):
    _, txt = files
    aid = sg.upload("Version", version["id"], txt)
    copy = pickle.loads(pickle.dumps(sg))
    assert copy.download_attachment(aid) == TXT
    state = sg.snapshot()
    sg.upload("Version", version["id"], txt)
    sg.restore(state)
    assert sg.download_attachment(aid) == TXT
    assert len(sg.find("Attachment", [])) == 1
