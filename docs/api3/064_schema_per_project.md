# 064 schema_per_project

re-asks: finding 009, finding 115
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/064_schema_per_project.py

**Q** What does `schema_field_read("Shot", project_entity=<sandbox>)` answer for `visible` and for `sg_status_list` `hidden_values`, compared with no project?

| call | answer |
|---|---|
| `schema_field_read("Shot")` | 100 fields, `visible` `value` true on all |
| `schema_field_read("Shot", project_entity=<sandbox>)` | 100 fields, `visible` `value` false on 12 |
| `visible` on `code`, either scope | `{"value": true, "editable": false}` |
| `visible` on a field hidden in the project | `{"value": false, "editable": true}` |
| `sg_status_list` `hidden_values`, no project | `{"value": [], "editable": false}` |
| the same, with the project | `{"value": ["awd", "bid", "to"], "editable": false}` |
| `schema_field_read("Shot", "sg_status_list", project_entity=<sandbox>)` | the same `hidden_values` as the full read |
| `valid_values` | identical in both scopes |
| `project_entity` id 999999999 | no error; reads as no project |

Between the two scopes only `visible` and `sg_status_list` `properties.hidden_values` differ.
`visible.editable` differs per field.

**Same as REST:** `visible` is per project and all true with no project (finding 115). `hidden_values` is the only status property that varies; `valid_values` is identical (finding 009). An unknown project id is not an error (finding 115).
**Differs from REST:** nothing.
**Mock:** accepts `project_entity` and ignores it: `hidden_values` reads `[]`, `visible` reads the site-wide value. Must change: store `visible` and `hidden_values` per project and answer them when `project_entity` is given.
