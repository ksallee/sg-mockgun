# 024 find_order

re-asks: finding 026
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/024_find_order.py

**Q** How does `order` behave with two keys, and on summary, url, unknown, entity and dotted fields?

The sample project's 100 Versions. Default order is id ascending.

| `order` | answer |
|---|---|
| `sg_status_list asc` | the `valid_values` order of the field (`na`, `rev`, `vwd`, `apr`, `fin`), not alphabetical. Ties by id ascending. |
| `sg_status_list desc` | `valid_values` order reversed. Ties by id ascending. |
| `sg_status_list asc, id asc` | the same as `sg_status_list asc` |
| `sg_status_list asc, id desc` | status first, ties by id descending |
| `id desc, sg_status_list asc` | id descending: the first key is primary |
| `code asc` | by `code` |
| `open_notes_count` (summary), asc or desc | default order, no Fault |
| `sg_uploaded_movie` (url), asc or desc | default order, no Fault |
| `sg_not_a_field_at_all`, asc or desc | default order, no Fault |
| `entity.Shot.nope` | default order, no Fault |
| `entity` asc, desc | by the link's display name, desc reversed. |
| `entity.Shot.code` asc, desc | by the Shot code |
| `{"field_name": "code", "direction": "up"}` | Fault `API read() invalid/missing string 'direction':` + `{"field_name" => "code", "direction" => "up"}` |
| `{"field_name": "code"}` | the client fills `"direction": "asc"` |
| `{"column": "code"}` | the client copies `column` into `field_name` |

The order of the entity type against the name was not separable here: the one Asset sorts first by name and by type.

**Same as REST:** default id ascending; the first key is primary; id ascending is the last tiebreak; a summary, url or unknown field is ignored without an error; a dotted path sorts (finding 026).
**Differs from REST:** a bad direction is a Fault naming `direction`. A status_list sorts by `valid_values` order; finding 026 does not record that.
**Mock:**
- `sg_status_list asc` sorts alphabetically (`apr`, `na`, `rev`). It must sort by the field's `valid_values` index.
- `order` on an entity field raises `TypeError: '<' not supported between instances of 'dict' and 'dict'`. It must sort by the link's display name.
- A bad direction raises `ValueError: Unknown ordering direction`. It must raise the Fault above.
- `{"field_name": "code"}` raises `KeyError: 'direction'`, and `{"column": "code"}` raises `ValueError`. Both must work as the client does.
- An unknown dotted field (`entity.Shot.nope`) must be ignored.
