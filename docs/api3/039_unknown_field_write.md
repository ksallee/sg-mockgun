# 039 unknown_field_write

re-asks: finding 028 (an unknown name in a filter), finding 024 (dotted paths on a write)
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/039_unknown_field_write.py

**Q** Is an unknown field name in a create body or an update body refused or ignored?

| call | answer |
|---|---|
| `create("Version", {..., "sg_not_a_field": "x"})` | Fault `API create() Version.sg_not_a_field doesn't exist:\n{"field_name" => "sg_not_a_field", "value" => "x"}`; no row made |
| `update("Version", <id>, {"description": "changed", "sg_not_a_field": "x"})` | Fault `API update() Version.sg_not_a_field doesn't exist:\n{"field_name" => "sg_not_a_field", "value" => "x"}`; `description` unchanged |
| `update("Version", <id>, {"entity.Shot.description": "via dotted"})` | `{"type": "Version", "id": <id>, "entity.Shot.description": "via dotted"}`; the linked Shot's `description` reads `"via dotted"` |

An unknown name refuses the whole write. A dotted name in an update writes the field on the linked row.

**Same as REST:** an unknown name is refused, as in a filter (`doesn't exist`).
**Differs from REST:** no corpus entry covers an unknown or dotted name in a REST write body. This is a gap for sg-groundtruth.
**Mock:** raises `ShotgunError` `sg_not_a_field is not a valid field for entity Version` on both verbs. It must raise `Fault` `API <verb>() <T>.<f> doesn't exist:\n{"field_name" => "<f>", "value" => <ruby inspect>}`. A dotted name in an update raises `KeyError: 'entity.Shot.description'`; it must write the linked row and return the dotted key.

Incident: the first run wrote `{"project.Project.name": "x"}` to a sandbox Version. It renamed the sandbox project to `x`. The name was restored in the same session, about one minute later. Two `Shotgun_Project_Change` event log rows record the rename and the restore. The probe now writes through a sandbox Shot.
