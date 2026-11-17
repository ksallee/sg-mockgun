"""upload, thumbnails, download and share_thumbnail as api3 answers 053 to 058 record them, on sandbox Versions."""

import pytest
from shotgun_api3 import ShotgunError, ShotgunFileDownloadError, ShotgunThumbnailNotReady

TRANSIENT = "/images/status/transient/thumbnail_pending.png"
TXT = b"sg-mockgun probe file\n"
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7V\xbd\xfa\x00\x00\x00\x00IEND\xaeB`\x82")


@pytest.fixture
def files(tmp_path):
    png = tmp_path / "probe.png"
    png.write_bytes(PNG)
    txt = tmp_path / "probe.txt"
    txt.write_bytes(TXT)
    return str(png), str(txt)


@pytest.fixture
def version(made, sandbox, run_token):
    return made.create("Version", {"code": "zzconf_%s_media" % run_token, "project": sandbox})


def read(site, entity_type, entity_id, fields):
    return site.find_one(entity_type, [["id", "is", entity_id]], fields)


# api3 053


@pytest.mark.finding("014", api3="053")
@pytest.mark.cell("upload", "-", "url")
def test_upload_to_a_movie_field_returns_the_attachment(site, made, files, version):
    png, _ = files
    aid = made.upload("Version", version["id"], png, field_name="sg_uploaded_movie", display_name="shown name")
    assert isinstance(aid, int)
    row = read(site, "Attachment", aid, ["attachment_links", "this_file", "filename", "file_size", "display_name"])
    assert [link["id"] for link in row["attachment_links"]] == [version["id"]]
    assert set(row["this_file"]) == {"url", "name", "content_type", "link_type", "type", "id"}
    assert (row["this_file"]["name"], row["this_file"]["content_type"], row["this_file"]["id"]) == (
        "shown name", "image/png", aid)
    assert (row["filename"], row["file_size"], row["display_name"]) == ("probe.png", None, "shown name")
    movie = read(site, "Version", version["id"], ["sg_uploaded_movie", "image"])
    assert movie["sg_uploaded_movie"]["id"] == aid and movie["image"].endswith(TRANSIENT)


@pytest.mark.finding("014", api3="053")
@pytest.mark.cell("upload", "-", "-")
def test_upload_without_a_field_links_an_attachment(site, made, files, version):
    _, txt = files
    aid = made.upload("Version", version["id"], txt)
    linked = site.find("Attachment", [["attachment_links", "is", {"type": "Version", "id": version["id"]}]], ["id"])
    assert [r["id"] for r in linked] == [aid]
    assert read(site, "Version", version["id"], ["image"])["image"] is None


# api3 054


@pytest.mark.finding("013", api3="054")
@pytest.mark.cell("upload", "-", "text")
def test_upload_to_a_text_field_is_refused(site, made, files, version):
    png, _ = files
    with pytest.raises(ShotgunError) as e:
        made.upload("Version", version["id"], png, field_name="description")
    assert str(e.value).startswith("Could not upload file successfully, but not sure why.\nPath: %s\n" % png)
    assert str(e.value).endswith("/upload/api_link_file\nError: 0\n"
                                 "Column description isn't a valid entity column for Version\n")
    assert site.find("Attachment", [["attachment_links", "is", {"type": "Version", "id": version["id"]}]], ["id"]) == []
    with pytest.raises(ShotgunError, match="Path must be a valid file, got '/nonexistent/probe.png'"):
        made.upload("Version", version["id"], "/nonexistent/probe.png")


# api3 055, 058


@pytest.mark.finding("013", api3="055")
@pytest.mark.cell("upload_thumbnail", "-", "image")
def test_thumbnail_is_transient_and_not_shareable_yet(site, made, sandbox, run_token, files, version):
    png, _ = files
    tid = made.upload_thumbnail("Version", version["id"], png)
    assert isinstance(tid, int) and read(site, "Attachment", tid, ["id"]) is None
    assert read(site, "Version", version["id"], ["image"])["image"].endswith(TRANSIENT)
    assert site.find("Attachment", [["attachment_links", "is", {"type": "Version", "id": version["id"]}]], ["id"]) == []
    target = made.create("Version", {"code": "zzconf_%s_media_target" % run_token, "project": sandbox})
    with pytest.raises(ShotgunThumbnailNotReady) as e:
        made.share_thumbnail([{"type": "Version", "id": target["id"]}],
                               source_entity={"type": "Version", "id": version["id"]})
    assert str(e.value).startswith("Unable to share thumbnail: 2\nsource_entity image is a transient thumbnail")
    assert read(site, "Version", target["id"], ["image"])["image"] is None


@pytest.mark.finding("none", api3="058")
@pytest.mark.cell("share_thumbnail", "-", "image")
def test_share_from_a_version_without_image(site, made, sandbox, run_token, version):
    target = made.create("Version", {"code": "zzconf_%s_media_none" % run_token, "project": sandbox})
    assert made.share_thumbnail([{"type": "Version", "id": target["id"]}],
                                  source_entity={"type": "Version", "id": version["id"]}) is None
    assert read(site, "Version", target["id"], ["image"])["image"] is None


# api3 056, 057


@pytest.mark.finding("039", api3="056")
@pytest.mark.cell("download_attachment", "-", "-")
def test_download_returns_the_bytes_sent(site, made, files, version, tmp_path):
    _, txt = files
    aid = made.upload("Version", version["id"], txt, field_name="sg_uploaded_movie")
    assert site.download_attachment({"type": "Attachment", "id": aid}) == TXT
    assert site.download_attachment(aid) == TXT
    movie = read(site, "Version", version["id"], ["sg_uploaded_movie"])["sg_uploaded_movie"]
    assert site.download_attachment(movie) == TXT
    target = tmp_path / "out.txt"
    assert site.download_attachment(aid, file_path=str(target)) == str(target) and target.read_bytes() == TXT
    assert site.download_attachment(None) is None


@pytest.mark.finding("039", api3="056")
@pytest.mark.cell("download_attachment", "-", "-")
def test_download_of_a_missing_attachment(site):
    with pytest.raises(ShotgunFileDownloadError) as e:
        site.download_attachment(999999999)
    assert str(e.value).endswith("/file_serve/attachment/999999999\nHTTP Error 404: Not Found")
    with pytest.raises(ValueError, match="Missing 'url' key in Attachment dict"):
        site.download_attachment({"type": "Version", "id": 1})


@pytest.mark.finding("none", api3="057")
@pytest.mark.cell("get_attachment_download_url", "-", "-")
def test_attachment_download_url(site):
    assert site.get_attachment_download_url(42).endswith("/file_serve/attachment/42")
    assert site.get_attachment_download_url({"url": "https://example.com/x", "id": 42}) == "https://example.com/x"
    assert site.get_attachment_download_url(None) is None
