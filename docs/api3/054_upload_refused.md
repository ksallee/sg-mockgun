# 054 upload_refused

re-asks: finding 013
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/054_upload_refused.py

**Q** What does `upload` raise for a field that takes no file, and for an entity that does not exist?

Each server refusal is a `ShotgunError`, not a `Fault`. The client puts the bytes on storage first, then calls `/upload/api_link_file`, and that call refuses. The message is a fixed preamble, the local path, the URL, `Error: 0`, then the server's reason:

```
Could not upload file successfully, but not sure why.
Path: <path>
Url: <site>/upload/api_link_file
Error: 0
<reason>
```

| call | `<reason>` |
|---|---|
| `upload("Version", <v>, png, field_name="description")`, a `text` field | `Column description isn't a valid entity column for Version` |
| `field_name="sg_nope_054"`, no such field | `Column sg_nope_054 isn't a valid entity column for Version` |
| `upload("Version", 999999999, txt)` | `entity with entity_id 999999999 and of entity_type Version not found` |
| `upload("NotAType", 1, png)` | `entity_type NotAType is not a valid class` |

Each message ends with a newline. A text field and a missing field get the same reason.

No Attachment row is left: none is linked to the Version, and no Attachment has the uploaded file name. The Version's `description` and `image` stay `null`.

Client-side, before any request:

| call | answer |
|---|---|
| `upload("Version", <v>, "/nonexistent/probe.png")` | `ShotgunError` `Path must be a valid file, got '/nonexistent/probe.png'` |

**Same as REST:** nothing to compare. The corpus records no REST upload to a non-file field or a missing entity.
**Differs from REST:** not measured over REST.
**Mock:** `upload` raises `NotImplementedError` for all four. Needed: `ShotgunError` with the preamble and the reasons above, raised before any row is made. The client-side path checks (`Path must be a valid file, got '<path>'`, `Path cannot be an empty file: '<path>'`) come first.
