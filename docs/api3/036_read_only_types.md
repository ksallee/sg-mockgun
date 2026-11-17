# 036 read_only_types

re-asks: field_types/uuid, field_types/calculated, field_types/summary, field_types/pivot_column
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/036_read_only_types.py

**Q** What do writes to uuid, calculated, summary and pivot_column fields answer, on create and update?

| field | call | answer |
|---|---|---|
| `EventLogEntry.session_uuid` | update a sandbox row's entry with a canonical uuid | Fault `API update() EventLogEntry.session_uuid is read only:\n{"field_name" => "session_uuid",\n "value" => "3f2504e0-4f89-11d3-9a0c-0305e82c3301"}` |
| same | update `None` | Fault `API update() EventLogEntry.session_uuid is read only:\n{"field_name" => "session_uuid", "value" => nil}` |
| same | `create("EventLogEntry", {project, event_type, description, session_uuid})` | Fault `API create() EventLogEntry.session_uuid is read only:\n{"field_name" => "session_uuid",\n "value" => "3f2504e0-..."}`; no row made |
| `Task.workload` (calculated) | update `5` | Fault `API update() Task.workload is read only:\n{"field_name" => "workload", "value" => 5}` |
| same | update `None` | the same, `"value" => nil` |
| same | create with `workload: 5` | Fault `API create() Task.workload is read only:\n{...}`; no row made |
| `Shot.open_notes_count` (summary, `editable: false`) | update `3` | Fault `API update() Shot.open_notes_count is read only:\n{"field_name" => "open_notes_count", "value" => 3}` |
| `Asset.sg_latest_version` (summary, `editable: true`) | update `None` | Fault `API update() of data type 'summary' not supported in API` |
| same | create with `None` | Fault `API create() of data type 'summary' not supported in API`; no row made |
| `Shot.step_0` (pivot_column) | update `None` | Fault `API update() Shot.step_0 is read only:\n{"field_name" => "step_0", "value" => nil}` |
| same | create with `None` | Fault `API create() Shot.step_0 is read only:\n{...}`; no row made |

The appended hash is Ruby pretty-print: a hash wider than the line breaks after the first pair, with one space of indent. A refused update leaves the value unchanged. New rows read `workload` `None`, `open_notes_count` `0`, `sg_latest_version` `None`, `step_0` `None`.

**Same as REST:** every write is refused on create and update, whatever the value, and the whole request fails.
**Differs from REST:** api3 appends `:\n<Ruby hash of the request>` to `is read only`; REST ends at `is read only.`. An editable summary field gives `of data type 'summary' not supported in API` over api3.
**Mock:** `API <verb>() <T>.<f> is read only.`, as `ShotgunError`. It must drop the full stop, append `:\n{"field_name" => "<f>", "value" => <ruby inspect>}` with the pretty-print wrap, and raise `Fault`. A new Shot reads `open_notes_count` `None`; it must read `0`. The bundled schema has no editable summary field, so the `not supported` wording is unreachable today; a site schema with one needs it.
