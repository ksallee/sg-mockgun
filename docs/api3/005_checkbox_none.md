# 005 checkbox_none

re-asks: field_types/checkbox
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/005_checkbox_none.py

**Q** Is checkbox `is None` refused or answered?

On `Version.flagged`, 1350 Versions.

| call | answer |
|---|---|
| `is None` | Fault `API read() Version.flagged expected [FalseClass, TrueClass] data type(s) but got NilClass:\nnil` |
| `is_not None` | the same Fault |
| `is True` | 0 rows |
| `is False` | 1350 rows |
| `is_not True` | 1350 rows |
| `is_not False` | 0 rows |
| `in [None]` | Fault, the 001 shape A refusal for `in`, `Valid relations: ["is", "is_not"]` |

**Same as REST:** `is None` and `is_not None` are refused. `false` is the only off state.
**Differs from REST:** the accepted classes are `[FalseClass, TrueClass]`. REST names `[String, FalseClass, TrueClass]`.
A newline follows the colon.
**Mock:** raises `ShotgunError` with `[String, FalseClass, TrueClass]` and a space before `nil`. Must change:
`Fault`, `[FalseClass, TrueClass]`, newline before `nil`.
