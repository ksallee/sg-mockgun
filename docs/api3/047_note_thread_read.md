# 047 note_thread_read

re-asks: finding 043
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/047_note_thread_read.py

**Q** What does `note_thread_read` return for a Note with replies and an attachment, and what does `entity_fields` change?

The method sends RPC `note_thread_contents` with `{"note_id", "entity_fields"}` and returns `_parse_records(answer)`: a list of dicts. Dates arrive as `datetime`. A non-dict `entity_fields` raises `ValueError` before the call.

| call | answer |
|---|---|
| `note_thread_read(<note>)`, 3 Replies, 1 Attachment | list of 5: Note, Reply, Reply, Reply, Attachment |
| order | `created_at` ascending, oldest first. The docstring says descending. |
| Note row keys | `content, created_at, created_by, id, type` |
| Reply row keys | `content, created_at, id, type, user` |
| Attachment row keys | `created_at, created_by, id, type` |
| `created_by` on Note and Attachment | `{id, name, type}` |
| `user` on Reply | `{id, name, type, image}`, `image` is `None` here |
| `created_at` | `datetime`, in the client's local zone |
| `entity_fields={"Note": ["subject", "note_links", "created_by.HumanUser.login"], ...}` | Note row adds `subject`, `note_links` and the dotted key `created_by.HumanUser.login` |
| `entity_fields={"Attachment": ["this_file", "filename", "file_size"]}` | Attachment row adds the three. `this_file` keys: `content_type, id, link_type, name, type, url` |
| `entity_fields={"Reply": ["entity", "created_by"]}` | ignored, Reply keys unchanged |
| `entity_fields={"Note": ["sg_not_a_field"]}` | no error, field absent |
| `entity_fields={"Bogus": ["code"]}` | no error, answer unchanged |
| `entity_fields={"Note": "subject"}` | Fault `Uncaught exception! no implicit conversion of Array into String` |
| `entity_fields=["subject"]` | `ValueError: entity_fields parameter must be a dictionary` (client side) |
| `note_thread_read(999999999)` | Fault `Not Found` |
| `note_thread_read(0)` | Fault `Not Found` |
| `note_thread_read("abc")` | Fault `API note_thread_contents() 'note_id' missing:` + `{"note_id" => "abc", "entity_fields" => {}}` |

**Same as REST:** three row types interleaved by time. Author under `created_by` on Note and Attachment, under `user` on Reply. `entity_fields` widens Note and Attachment and is ignored on Reply.
**Differs from REST:** a missing Note is Fault `Not Found`, where REST answers a named 404. An unknown field in `entity_fields` is dropped without error.
**Mock:** `sg_mockgun.Shotgun` has no `note_thread_read`: `AttributeError`. Over the wire the server answers Fault `Error: API method "note_thread_contents" is not permitted.` Needed: the method, rows in ascending `created_at`, the three key sets above, `entity_fields` on Note and Attachment only, unknown fields dropped, and Fault `Not Found` for a missing id.
