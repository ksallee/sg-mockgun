# 053 upload_field

re-asks: finding 013, finding 014, finding 039
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/053_upload_field.py

**Q** What does `upload` return and leave, to `Version.sg_uploaded_movie` and with no field name?

Files: a 4x4 PNG `probe.png` and a 22-byte `probe.txt`. The site has `s3_direct_uploads_enabled: true` and `s3_enabled_upload_types: {"*": ["*"]}`, so the client takes the storage path.

| call | answer |
|---|---|
| `upload("Version", <v>, "probe.png", field_name="sg_uploaded_movie", display_name="shown name", tag_list="probe_a,probe_b")` | `<a1>`, an `int` |
| `upload("Version", <v>, "probe.txt")` | `<a2>`, an `int` |

The return is the id of an Attachment row. Its fields, read straight after:

| field | movie field, `<a1>` | no field, `<a2>` |
|---|---|---|
| `attachment_links` | `[{"id": <v>, "name": "<code>", "type": "Version"}]` | the same |
| `this_file` | `{"url": <s3-url>, "name": "shown name", "content_type": "image/png", "link_type": "upload", "type": "Attachment", "id": <a1>}` | the same keys, `name` `"probe.txt"`, `content_type` `"text/plain"` |
| `filename`, `original_fname` | `"probe.png"` | `"probe.txt"` |
| `display_name`, `cached_display_name` | `"shown name"` | `"probe.txt"` |
| `file_size`, `file_extension` | `null` | `null` |
| `image` | `<site>/images/status/transient/thumbnail_pending.png` | `null` |
| `image_source_entity` | `{"type": "Attachment", "id": <a1>, "name": "shown name"}` | `null` |
| `processing_status` | `"thumbnail_pending_us"` | `null` |
| `tags` | `[{"id": <t>, "name": "probe_a", "type": "Tag"}, {... "probe_b" ...}]` | `[]` |
| `project` | the Version's project | the same |
| `created_by`, `updated_by` | the script's ApiUser | the same |
| `description`, `local_storage`, `metadata`, `sg_type`, `sg_status_list`, `filmstrip_image` | `null` | `null` |

`<s3-url>` is a presigned storage URL of the form `https://<bucket host>/<hex>/<hex>/<filename>?<query>`. It is not `/file_serve/attachment/<id>`.

The Version after both uploads:

| field | value |
|---|---|
| `sg_uploaded_movie` | the `this_file` dict of `<a1>`, key for key |
| `image` | `<site>/images/status/transient/thumbnail_pending.png`, a thumbnail made from the uploaded file |
| `filmstrip_image` | `null` |

`find("Attachment", [["attachment_links", "is", <version>]])` lists both rows. The no-field upload changes no field on the Version.

`tag_list` names a Tag that does not exist, and the server creates it: two site-wide Tag rows, `created_by` the ApiUser. The probe deletes them.

**Same as REST:** the field picks the kind of upload, and no field gives an Attachment reached through `attachment_links` (finding 014). The movie field reads back as a dict with `url` (finding 021). `image` reads the transient placeholder straight after (finding 013). `file_size` is `null` on a good upload (finding 039).
**Differs from REST:** api3 returns the new Attachment id. REST `complete_upload` returns one space and names no row (finding 039). `display_name` and `tag_list` have no REST counterpart in the corpus.
**Mock:** `upload` raises `NotImplementedError`. Needed: create an Attachment with the fields above (`file_size` and `file_extension` `null`, not the computed values PR shotgunsoftware/python-api#469 sets), link it, set `field_name` on the entity to the `this_file` dict, return the id. A Tag named in `tag_list` is created when missing. An upload to a movie field sets `image` to the transient placeholder.
