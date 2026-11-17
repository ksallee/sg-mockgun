"""api3 057: what get_attachment_download_url returns for each shape. Client-side: no request is sent."""
import _lib
import _media

env = _lib.load_env()
sg = _lib.client(env)
url = "https://example-bucket.s3.amazonaws.com/abc/probe.txt?sig=1"
cases = {
    "int": 42,
    "attachment_dict_no_url": {"type": "Attachment", "id": 42},
    "field_value_with_url": {"type": "Attachment", "id": 42, "url": url, "link_type": "upload"},
    "local_link": {"link_type": "local", "local_path": "/tmp/x.txt", "url": "file:///tmp/x.txt"},
    "version_dict_no_url": {"type": "Version", "id": 42},
    "dict_no_type": {"id": 42},
    "none": None,
    "zero": 0,
    "str": "42",
}
out = {name: _lib.ask(sg.get_attachment_download_url, value) for name, value in cases.items()}
for v in out.values():
    if isinstance(v.get("ok"), str):
        v["ok"] = v["ok"].replace(sg.config.server, "<site>")
_lib.emit("057_attachment_download_url", out, env)
