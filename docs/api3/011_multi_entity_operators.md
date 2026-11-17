# 011 multi_entity_operators

re-asks: field_types/multi_entity
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/010_filter_links.py

**Q** How does each multi_entity operator match a row with no links? Which values are refused?

Three Notes on `note_links`: `n_shot` links a Shot, `n_asset` links an Asset, `n_none` links nothing.
`<Shot>` and `<Asset>` are `{"type": ..., "id": <id>}`. The Shot's code ends in `shot`.

| call | answer |
|---|---|
| `["note_links", "is", <Shot>]` | `n_shot` |
| `["note_links", "is", [<Shot>, <Asset>]]` | Fault `API read() 'is' 'relation' expects a 1-element array:\n[{"type" => "Shot", "id" => <id>}, {"type" => "Asset", "id" => <id>}]` |
| `["note_links", "is", None]` | `n_none` |
| `["note_links", "is_not", None]` | `n_asset n_shot` |
| `["note_links", "is_not", <Shot>]` | `n_asset n_none` |
| `["note_links", "in", [<Shot>]]` | `n_shot` |
| `["note_links", "in", [<Shot>, <Asset>]]` | `n_asset n_shot` |
| `["note_links", "not_in", [<Shot>]]` | `n_asset n_none` |
| `["note_links", "not_in", [<Shot>, <Asset>]]` | `n_none` |
| `["note_links", "type_is", "Shot"]` | `n_shot` |
| `["note_links", "type_is_not", "Shot"]` | `n_asset n_none` |
| `["note_links", "type_is", None]` | `n_none` |
| `["note_links", "type_is_not", None]` | `n_asset n_shot` |
| `["note_links", "name_is", <shot code>]` | `n_shot` |
| `["note_links", "name_contains", "shot"]` | `n_shot` |
| `["note_links", "name_not_contains", "shot"]` | `n_asset n_none` |
| `["note_links", "name_not_contains", "x"]` | `n_asset n_none n_shot` |
| `["note_links", "name_is", None]` | Fault `API read() Note.note_links expected [String] data type(s) but got NilClass:\nnil` |
| `["note_links", "in", []]` | client raises `IndexError: list index out of range`, no request sent |
| `["note_links", "not_in", []]` | same `IndexError` |
| `in []`, entity optimisation off | Fault `API read() 'in' 'relation' expects at least a 1-element array:\n[]` |
| `not_in []`, entity optimisation off | Fault `API read() 'not_in' 'relation' expects at least a 1-element array:\n[]` |

The row with no links matches each negating operator: `is_not`, `not_in`, `type_is_not`, `name_not_contains`.

The `IndexError` comes from `_translate_filters_simple` in `shotgun_api3/shotgun.py`. For `is`, `is_not`,
`in` and `not_in` on any path but `id` it reads `values[0]` to decide whether to strip entity dicts to
`type` and `id`. Setting `shotgun_api3.shotgun.SHOTGUN_API_DISABLE_ENTITY_OPTIMIZATION = True` skips that
read, and the site answers the Fault.

**Same as REST:** every match, the `is [A, B]` refusal and the `in []` refusal. `name_not_contains`, unmeasured
over REST, matches the row with no links.
**Differs from REST:** over api3 `in []` and `not_in []` never reach the site: the client raises `IndexError`.
**Mock:** `type_is None` matches nothing and must match `n_none`. `type_is_not None` matches all three and
must exclude `n_none`. `name_not_contains` raises `mockgun does not implement the 'name_not_contains'
relation on the 'multi_entity' data type` and must match as above. `name_is None` returns `[]` and must
raise the Fault above. `in []` and `not_in []` raise `ShotgunError` with the site text; the mock skips
`_translate_filters`, so a mock client gets that error where a site client gets `IndexError`. The mock raises
`ShotgunError` where the site raises `Fault`.
