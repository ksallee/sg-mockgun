# 015 entity_in_empty

re-asks: field_types/entity, field_types/multi_entity
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/010_filter_links.py

**Q** Is `in []` or `not_in []` on a single entity field refused or answered?

| call | answer |
|---|---|
| `find("Version", [["entity", "in", []]])` | client raises `IndexError: list index out of range`, no request sent |
| `find("Version", [["entity", "not_in", []]])` | same `IndexError` |
| `in []`, entity optimisation off | Fault `API read() 'in' 'relation' expects at least a 1-element array:\n[]` |
| `not_in []`, entity optimisation off | Fault `API read() 'not_in' 'relation' expects at least a 1-element array:\n[]` |

The cause and the switch are in 011: `_translate_filters_simple` reads `values[0]` for `is`, `is_not`, `in`
and `not_in` on any path but `id`. The site refuses an empty list on entity as on multi_entity.

**Same as REST:** the Fault text matches multi_entity `in []` over REST.
**Differs from REST:** over api3 the call never reaches the site: the client raises `IndexError`.
**Mock:** `entity in []` returns `[]` and `entity not_in []` returns every row. Both must raise `Fault` with
the site text, as multi_entity does on dev.
