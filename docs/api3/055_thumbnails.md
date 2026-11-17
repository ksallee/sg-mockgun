# 055 thumbnails

re-asks: finding 013, finding 021
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/055_thumbnails.py

**Q** What do `upload_thumbnail` and `upload_filmstrip_thumbnail` return, and what do `image` and `filmstrip_image` read after?

Both call `upload` with `field_name` `thumb_image` and `filmstrip_thumb_image`. File: a 4x4 PNG `probe.png`.

| call | answer |
|---|---|
| `upload_thumbnail("Version", <v>, png)` | an `int`, `<n>` |
| `find_one("Attachment", [["id", "is", <n>]])` | `None` |
| `upload_filmstrip_thumbnail("Version", <v>, png)` | an `int`, `<n>+1` |
| `find_one("Attachment", [["id", "is", <n>+1]])` | `None` |
| `find("Attachment", [["attachment_links", "is", <version>]])` | `[]` |
| `upload_thumbnail("Version", 999999999, png)` | `ShotgunError`, reason `entity with entity_id 999999999 and of entity_type Version not found` (api3 054) |

The returned ids are not Attachment rows, and no Attachment is linked to the Version. The ids run in a sequence of their own, far above the Attachment ids of the same run. A second probe got `<n>+2` from the next `upload_thumbnail`.

The Version, polled every 2 seconds:

| after | `image` | `filmstrip_image` |
|---|---|---|
| `upload_thumbnail`, 0.1 s | `<site>/images/status/transient/thumbnail_pending.png` | `null` |
| 40.7 s | `<s3-url>` ending `/probe_t.jpg?<query>` | `null` |
| `upload_filmstrip_thumbnail`, 0.1 s | the same `probe_t.jpg` URL | `<s3-url>` ending `/probe.png?<query>` |

`image` is transcoded: a placeholder first, then a JPEG named `<stem>_t.jpg`. A second run went final after 34.6 s and 44.1 s. `filmstrip_image` is not transcoded: it reads the uploaded PNG at once, with no placeholder.

**Same as REST:** `image` reads `/images/status/transient/thumbnail_pending.png` until the transcode ends, then a presigned storage URL as a plain string (findings 013, 021).
**Differs from REST:** REST returns no id for the thumbnail upload. The filmstrip upload is not in the corpus.
**Mock:** `upload_thumbnail` returns `None` and changes nothing. `upload_filmstrip_thumbnail` is missing: `AttributeError`. Needed: both return an int from a counter of their own and create no Attachment. `upload_thumbnail` sets `image`, and `upload_filmstrip_thumbnail` sets `filmstrip_image`, to a URL. The transcode delay is optional: a placeholder until a test clock moves, or the final URL at once.
