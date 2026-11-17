# 056 download_attachment

re-asks: finding 039, finding 048
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/056_download_attachment.py

**Q** What does `download_attachment` return for each accepted shape, and what does it raise for a missing id?

Setup: `upload("Version", <v>, "probe.txt", field_name="sg_uploaded_movie")`, 22 bytes, Attachment `<a>`.

| call | answer |
|---|---|
| `download_attachment({"type": "Attachment", "id": <a>})` | `bytes`, equal to the file sent |
| `download_attachment(<sg_uploaded_movie value>)` | the same |
| `download_attachment(<a>)` | the same |
| `download_attachment(attachment_id=<a>)` | the same |
| `download_attachment(<a>, file_path=<target>)` | `<target>`, the file written with the bytes sent |
| `download_attachment(None)` | `None` |
| `download_attachment()` | `TypeError` `Missing parameter 'attachment'. Expected a dict, int, NoneType value oran int for parameter attachment_id` |
| `download_attachment(999999999)` | `ShotgunFileDownloadError` `Failed to open <site>/file_serve/attachment/999999999` + newline + `HTTP Error 404: Not Found` |
| `download_attachment({"type": "Attachment", "id": 999999999})` | the same |
| `download_attachment(999999999, file_path=<target>)` | the same, and `<target>` is left on disk, empty |
| `download_attachment({"type": "Version", "id": <v>})` | `ValueError` `Missing 'url' key in Attachment dict` |

`oran` is printed as is: the client's message lacks a space. A missing id is a 404, so the client adds none of its 400, 403, 409 or 410 hints.

**Same as REST:** a good upload's stored file downloads, and its bytes match (finding 039). By id, the client fetches `<site>/file_serve/attachment/<id>`; by field value, it fetches the storage URL in `url` (api3 057). REST downloads through `?alt=original`, a 302 to storage (finding 048).
**Differs from REST:** api3 has no field path form: the caller passes the Attachment, its id or the field value. A missing id is a 404 on `/file_serve/attachment/<id>`; REST answers 404 for an empty field on `?alt=original` (finding 048).
**Mock:** `download_attachment` is missing: `AttributeError`. Needed: the shapes above, bytes or the written path, `None` for `None`, the `TypeError` with no argument, and `ShotgunFileDownloadError` with the 404 message for an id with no stored file. PR shotgunsoftware/python-api#470 matches these returns and exceptions. The `ValueError` comes from `get_attachment_download_url` (api3 057).
