# 060 create_contract

re-asks: finding 012, entity_types/Shot, entity_types/Version
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/060_create_contract.py

**Q** Is `project` required on a Shot or Version create? Is `code` required, and is it unique?

| call | answer |
|---|---|
| `create("Shot", {"code": "x"})` | Fault `API create() missing 'project' attribute:` + `[{"field_name" => "code", "value" => "x"}]` |
| `create("Version", {"code": "x"})` | the same Fault, for Version |
| `create("Shot", {})` | Fault `API create() invalid/missing array 'fields':` + `{"type" => "Shot", "fields" => [], "return_fields" => ["id"]}` |
| `create("Version", {})` | the same Fault, `"type" => "Version"` |
| `create("Shot", {"project": <sandbox>})` | `{"id": <id>, "project": {...}, "type": "Shot"}`; `code` reads `"New Shot <id>"` |
| `create("Version", {"project": <sandbox>})` | `code` reads `"New Version <id>"` |
| `create(t, {"project": ..., "code": ""})` | Fault `API create() CRUD ERROR #6: Create failed for [Shot]: Cannot set identifier field to empty. (Shot)` |
| `create(t, {"project": ..., "code": None})` | the same Fault as `""` |
| two creates with the same `code` | two rows, two ids; `find` on the code returns both |
| `schema_field_read(t, "code")` | `mandatory` `{"value": true, "editable": false}`, `unique` `{"value": false, "editable": false}` |
| `schema_field_read(t, "project")` | `mandatory` `{"value": false, "editable": false}` |

The answer is the same for Shot and Version, with the type name substituted.
The create answer echoes `project` and the fields sent. It has no `code` key when `code` was not sent.
A refused create on `code` `""` or `None` consumed an id: the next row's id skipped two.

**Same as REST:** `project` is required and flagged `mandatory: false`. `code` is optional, flagged `mandatory: true`, and not unique. An omitted `code` becomes `New <Type> <id>`. `""` is refused with the same CRUD message (finding 012).
**Differs from REST:** `{}` is refused for an empty field list before the project check (`invalid/missing array 'fields'`), where REST answers `missing 'project' attribute`. Over REST `None` on Shot was not measured.
**Mock:** creates every case. No `project` check, no empty-`fields` check, `code` stays `None` instead of `New Shot <id>`, and `""` is stored as `None`. Must change: raise the three Faults above, and generate `New <Type> <id>` for an omitted identity field.
