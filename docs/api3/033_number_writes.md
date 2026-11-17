# 033 number_writes

re-asks: field_types/number
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/033_number_writes.py

**Q** What does a number field answer to `2**31`, `True` and `"7"`?

On `Version.frame_count`:

| sent | update | create |
|---|---|---|
| `2**31` | Fault `API update() CRUD ERROR #5: Update failed for [Version.frame_count]: Invalid statement.` | Fault `API create() CRUD ERROR #6: Create failed for [Version]: PG::NumericValueOutOfRange: ERROR:  integer out of range\n`; no row made |
| `2**31 - 1` | accepted, reads `2147483647` (`int`) | accepted |
| `True` | Fault `API update() Version.frame_count expected [Integer, NilClass] data type(s) but got TrueClass:\ntrue` | the same, `API create()`; no row made |
| `"7"` | Fault `... but got String:\n"7"` | the same; no row made |
| `7.0` | Fault `... but got Float:\n7.0` | the same; no row made |
| `None` | accepted, reads `None` | accepted |

A new row reads `None`.

**Same as REST:** signed 32-bit. The out-of-range text after the prefix is REST's, on both verbs. `True` and floats are refused.
**Differs from REST:** api3 prefixes the range error with `API update() CRUD ERROR #5: ` and `API create() CRUD ERROR #6: `. api3 refuses `"7"`; REST lists `[String, Integer, NilClass]` and accepts an integer string.
**Mock:** raises `ShotgunError` with REST's range text and no prefix. It accepts `"7"` and stores `7`. It answers `"7.5"` with `Invalid data for 'number' data type`. It must add the prefixes, refuse every string with the api3 class Fault (`[Integer, NilClass]`), and raise `Fault`.
