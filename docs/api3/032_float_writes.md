# 032 float_writes

re-asks: field_types/float
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/032_float_writes.py

**Q** Is a float write of `2` (int), `"2.5"` (str) or `1.23456789` accepted? What is stored, returned, and of which Python type?

On `Version.sg_movie_aspect_ratio`, create and update alike:

| sent | answer | read |
|---|---|---|
| `2` | Fault `API update() Version.sg_movie_aspect_ratio expected [BigDecimal, Float, NilClass] data type(s) but got Integer:\n2` | unchanged |
| `"2.5"` | Fault `... but got String:\n"2.5"` | unchanged |
| `"abc"` | Fault `... but got String:\n"abc"` | unchanged |
| `True` | Fault `... but got TrueClass:\ntrue` | unchanged |
| `1.23456789` | accepted, returns `1.234568` | `1.234568`, `float` |
| `2.0` | accepted, returns `2.0` | `2.0`, `float` |
| `None` | accepted, returns `None` | `None` |

On create the Fault starts `API create()`. A refused create makes no row. A new row reads `None`.

**Same as REST:** an int is refused. The value is rounded to 6 decimals.
**Differs from REST:** api3 refuses a numeric string; REST accepts it, and lists `[String, BigDecimal, Float, NilClass]`. api3 reads a Python `float`; REST reads a JSON string (`"1.234568"`).
**Mock:** raises `ShotgunError` with REST's class list. It accepts `"2.5"` and stores `2.5`. It answers `"abc"` with `Invalid data for 'float' data type`. It must refuse every string with the api3 class Fault, and raise `Fault`. Rounding and the float read match.
