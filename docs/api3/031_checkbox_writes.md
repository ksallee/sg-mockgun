# 031 checkbox_writes

re-asks: field_types/checkbox
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/031_checkbox_writes.py

**Q** What does an untouched checkbox on a new row read? What do a None write and a `"true"` write answer?

On `Version.flagged`:

| call | answer |
|---|---|
| `create` without `flagged` | return has no `flagged` key; a read gives `False` (bool) |
| `update(..., {"flagged": None})` | Fault `API update() Version.flagged expected [FalseClass, TrueClass] data type(s) but got NilClass:\nnil` |
| `update(..., {"flagged": "true"})` | Fault `... expected [FalseClass, TrueClass] data type(s) but got String:\n"true"` |
| `"false"`, `"True"`, `"yes"`, `"1"` | the same Fault, `String:\n"<as sent>"` |
| `1`, `0` | the same Fault, `Integer:\n1`, `Integer:\n0` |
| `True` | `{"type": "Version", "id": <id>, "flagged": True}` |
| `create(..., {"flagged": None})` | Fault `API create() Version.flagged expected [FalseClass, TrueClass] data type(s) but got NilClass:\nnil`; no row made |
| `create(..., {"flagged": "true"})` | Fault `API create() ... but got String:\n"true"`; no row made |

A refused write leaves the value unchanged. The Fault has a newline between the class and the value.

**Same as REST:** a new row reads `False`. None is refused on create and update.
**Differs from REST:** api3 accepts only `True` and `False`. REST accepts `"true"` and `"false"`, and words its list `[String, FalseClass, TrueClass]`. REST answers `"yes"` with `Invalid data for 'checkbox' data type`; api3 gives the class Fault.
**Mock:** raises `ShotgunError`, not `Fault`, with REST's `[String, FalseClass, TrueClass]` and a space before the value. It accepts `"true"` and `"false"` on create and update. It must refuse every string with the api3 class Fault, and raise `Fault`.
