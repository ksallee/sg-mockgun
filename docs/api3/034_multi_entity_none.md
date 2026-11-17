# 034 multi_entity_none

re-asks: field_types/multi_entity
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/034_multi_entity_none.py

**Q** What Fault does a None write to a multi_entity field raise?

On `Shot.shots`:

| call | answer |
|---|---|
| a new row | reads `[]` |
| `update(..., {"shots": None})` | Fault `API update() Shot.shots expected [Array] data type(s) but got NilClass:\nnil`; links unchanged |
| `update(..., {"shots": []})` | `{"type": "Shot", "id": <id>, "shots": []}`; links cleared |
| `create(..., {"shots": None})` | Fault `API create() Shot.shots expected [Array] data type(s) but got NilClass:\nnil`; no row made |

**Same as REST:** None is refused. `[]` clears. A new row reads an empty list.
**Differs from REST:** api3 lists `[Array]`; REST lists `[Array, Hash]`.
**Mock:** raises `ShotgunError` with `[Array, Hash]` and a space before `nil`. It must say `[Array]`, put a newline before `nil`, and raise `Fault`.
