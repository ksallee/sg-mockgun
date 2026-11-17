# 048 activity_stream_read

re-asks: finding 043, finding 066, report 009
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/048_activity_stream_read.py

**Q** What does `activity_stream_read` return on a Shot and a Version, how do `limit`, `min_id` and `max_id` page it, and what do bad inputs answer?

The method sends RPC `activity_stream` with `{type, id, max_id, min_id, limit, entity_fields}` and returns `_parse_records(answer)[0]`: one dict. A non-dict `entity_fields` raises `ValueError` before the call.

| call | answer |
|---|---|
| `activity_stream_read("Shot", <shot>)` | dict, keys `earliest_update_id, entity_id, entity_type, latest_update_id, updates` |
| `updates` row keys (`create`) | `created_at, created_by, id, meta, primary_entity, read, update_type` |
| `meta` (`create`) | `entity_id, entity_type, type` |
| `primary_entity` | `id, name, status, type` |
| `created_by` | `id, image, name, status, type` |
| `created_at` | `datetime` |
| `read` | `None` on every row |
| order | `id` descending |
| default `limit` | 25 rows (Project stream). The Shot stream had 15, all returned. |
| `limit=0` | the default, 25 |
| `limit=500` | 500 |
| `limit=501`, `limit=2000` | 500, no error |
| `limit=-1` | Fault `Uncaught exception! Invalid parameter: page_size` |
| `limit=3` | 3 rows, `earliest_update_id` is the lowest id returned |
| stream exhausted | `earliest_update_id` is `0` |
| `max_id=<m>, limit=3` | ids below `<m>`, exclusive. `latest_update_id` is the highest id returned. |
| `min_id=<m>` | ids above `<m>`, exclusive |
| `min_id` above the newest | `updates` `[]`, both bounds set to the site's newest id |
| `latest_update_id` with no `max_id` | the site's newest update id, not the record's. It rose between calls. |
| `entity_fields={"Version": ["sg_status_list", "entity"]}` | Version `primary_entity` keys `entity, id, name, sg_status_list, status, type` |
| `entity_fields={"Shot": ["sg_not_a_field"]}` | no error |
| `activity_stream_read("Version", <version>)` | same envelope, `entity_type` `Version` |
| `("Shot", 999999999)`, `("Version", 999999999)`, `("Shot", 0)` | Fault `Uncaught exception! Entity does not exist or user does not have permission` |
| `("Bogus", 1)`, `("shots", <shot>)` | Fault `Invalid parameter: type` |
| `("Shot", "abc")` | Fault `Invalid parameter: id` |

**Same as REST:** the envelope keys, the row keys, the `create` meta, `id` descending, exclusive `min_id` and `max_id`, `earliest_update_id` `0` at the end, a site-wide `latest_update_id`, `entity_fields` widening `primary_entity`.
**Differs from REST:** `limit` above 500 is capped at 500, where REST answers 400. A missing record id is a Fault with a message, where REST answers 500 with no detail (report 009). A plural or unknown type is `Invalid parameter: type`, where REST answers 404 for an unknown type. `read` is `None`, where REST gives `false`.
**Mock:** `sg_mockgun.Shotgun` has no `activity_stream_read`: `AttributeError`. Over the wire, Fault `Error: API method "activity_stream" is not permitted.` Needed: the envelope above built from the mock's event log or its own update list, default 25, cap 500, `limit=0` as default, exclusive bounds, and the three Faults above.
