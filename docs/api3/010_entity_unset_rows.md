# 010 entity_unset_rows

re-asks: field_types/entity
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/010_filter_links.py

**Q** Which entity filters match a row whose link is unset? Which values do the `name_*` operators refuse?

Three Versions: `v_shot` links a Shot, `v_asset` links an Asset, `v_none` is unset. `<Shot>` is
`{"type": "Shot", "id": <id>}`. Every filter is ANDed with a scope that matches only those three.

| call | answer |
|---|---|
| `["entity", "is", None]` | `v_none` |
| `["entity", "is_not", None]` | `v_asset v_shot` |
| `["entity", "is_not", <Shot>]` | `v_asset v_none` |
| `["entity", "type_is", None]` | `v_none` |
| `["entity", "type_is_not", None]` | `v_asset v_shot` |
| `["entity", "type_is", "Shot"]` | `v_shot` |
| `["entity", "type_is_not", "Shot"]` | `v_asset v_none` |
| `["entity", "in", [<Shot>]]` | `v_shot` |
| `["entity", "not_in", [<Shot>]]` | `v_asset v_none` |
| `["entity", "name_not_contains", "x"]` | `v_asset v_none v_shot` |
| `["entity", "name_not_contains", <shot code>]` | `v_asset v_none` |
| `["entity", "name_is", None]` | Fault `API read() Version.entity expected [String] data type(s) but got NilClass:\nnil` |
| `["entity", "name_contains", None]` | same Fault |
| `["entity", "name_not_contains", None]` | same Fault |

The unset row matches each negating operator: `is_not`, `not_in`, `type_is_not` and `name_not_contains`.
`type_is None` means unset and `type_is_not None` means set.

**Same as REST:** the vocabulary, the matches on linked rows, and a refused `null` for the three `name_*`
operators.
**Differs from REST:** nothing measured differs. REST measured `type_is null` and `type_is_not null` only
on a baseline with no unset row; here `type_is None` matches the unset row.
**Mock:** `type_is None` matches no row and must match `v_none`. `type_is_not None` matches all three
and must exclude `v_none`. The `name_*` refusal with `None` raises `ShotgunError` `API read() 'name_is'
'relation' does not accept a null value`; it must raise `Fault` with the site message above, the same for
all three operators. Every other row matches the site.
