# 002 relations_per_type

re-asks: finding 017, field_types/*
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/002_relations_per_type.py

**Q** Which relations does each data type accept?

Tried on each field of 001: the 24 relations in the union of the REST lists, plus `not_between`,
`name_starts_with` and `name_ends_with` (in shotgun_api3's mockgun, in no REST list). Each value was
well-formed for the relation. "Refused" is a `doesn't support` or `cannot be used in a filter` Fault.

| data type | accepted | other Fault |
|---|---|---|
| text | is, is_not, contains, not_contains, starts_with, ends_with, in, not_in | |
| number, float, percent, duration, timecode | is, is_not, in, not_in, greater_than, less_than, between | |
| date, date_time | is, is_not, in, not_in, greater_than, less_than, between, in_last, not_in_last, in_next, not_in_next, in_calendar_day, in_calendar_week, in_calendar_month, in_calendar_year | |
| checkbox | is, is_not | |
| list, status_list, entity_type, color, uuid | is, is_not, in, not_in | |
| entity, multi_entity | is, is_not, in, not_in, name_contains, name_not_contains, name_is, type_is, type_is_not | |
| image | is, is_not | |
| jsonb | is, is_not, contains, not_contains | |
| calculated (Task.workload) | is, is_not, greater_than, less_than, between | `in [None]`, `not_in [None]`: `API read() CRUD ERROR #10: Read failed for entity type [Task]` |
| pivot_column | none | `is`, `is_not`: `API read() of data type 'pivot_column' not supported in API` |
| url, password, serializable, summary | none | |

`not_between`, `name_starts_with` and `name_ends_with` are refused on every type.

Each type accepts its `Valid relations` list from 001 and refuses every other relation.

**Same as REST:** every list, and pivot_column refusing both listed relations with the same message.
**Differs from REST:** calculated accepts relations (006). `in [None]` on a calculated field is a CRUD error, not a refusal.

**Mock:** `RELATIONS` in `src/sg_mockgun/filters.py` matches for text, number, float, percent, duration,
date, date_time, checkbox, list, status_list, entity_type, color, uuid, image, jsonb and pivot_column.
timecode is listed but the bundled schema has no timecode field. Gaps:
- entity and multi_entity are not in `RELATIONS`. An unlisted relation raises `mockgun does not implement ...`.
  multi_entity raises that for `name_not_contains`, which the site accepts.
- date and date_time raise `mockgun does not implement ...` for `in_last`, `not_in_last`, `in_next`,
  `not_in_next` and the four `in_calendar_*`, which the site accepts.
- calculated refuses every relation. It must take the list of its formula's result type (number here).
- Errors raise `ShotgunError`, not `Fault`.
