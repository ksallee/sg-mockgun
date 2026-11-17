# 014 relative_date_time

re-asks: field_types/date_time, field_types/date
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/010_filter_links.py

**Q** What does api3 send for the relative date operators, which values does the site accept, and how does it refuse a bad one?

**Sent.** `_translate_filters_simple` sends `values = sg_filter[2:]`, unwrapped when that is one list or tuple:

| filter | `values` sent |
|---|---|
| `["created_at", "in_last", 1, "DAY"]` | `[1, "DAY"]` |
| `["created_at", "in_last", [1, "DAY"]]` | `[1, "DAY"]` |
| `["created_at", "in_last", 1]` | `[1]` |
| `["created_at", "in_calendar_day", 0]` | `[0]` |
| `["created_at", "in_calendar_day", [0]]` | `[0]` |

The client checks no relation, unit or count.

**Answered.** On `Version.created_at`, three rows created seconds before:

| filter | answer |
|---|---|
| `in_last 1, "DAY"` or `in_last [1, "DAY"]` | 3 rows |
| `not_in_last [1, "DAY"]` | 0 |
| `in_next [1, "DAY"]` | 0 |
| `not_in_next [1, "DAY"]` | 3 |
| `in_last [1, "HOUR"]`, `"WEEK"`, `"MONTH"`, `"YEAR"` | 3 each |
| `in_last [0, "DAY"]` | 0, no Fault |
| `in_calendar_day 0` or `[0]` | 3 |
| `in_calendar_day -1`, `in_calendar_day 1` | 0 |
| `in_calendar_week 0`, `in_calendar_month 0`, `in_calendar_year 0` | 3 each |
| `in_calendar_year -1` | 0 |
| `in_last [1, "MINUTE"]` | Fault `API read() 'in_last' 'relation' doesn't support the 'MINUTE' time unit:\n[1, "MINUTE"]\nValid time units: ["HOUR", "DAY", "WEEK", "MONTH", "YEAR"]` |
| `in_last [1, "day"]` | the same Fault for `'day'` |
| `in_last [-1, "DAY"]` | Fault `API read() 'in_last' 'relation' expects at a positive Integer time unit:\n[-1, "DAY"]` |
| `in_last [1.5, "DAY"]` | Fault `API read() Version.created_at expected Integer data type(s) but got Float (1.5):\n[1.5, "DAY"]` |
| `in_last ["1", "DAY"]` | Fault `API read() Version.created_at expected Integer data type(s) but got String (1):\n["1", "DAY"]` |
| `in_last ["DAY", 1]` | Fault `API read() Version.created_at expected Integer data type(s) but got String (DAY):\n["DAY", 1]` |
| `in_last 1` | Fault `API read() 'in_last' 'relation' expects a 2-element array:\n[1]` |
| `in_calendar_day [0, "DAY"]` | Fault `API read() 'in_calendar_day' 'relation' expects a 1-element array:\n[0, "DAY"]` |
| `in_calendar_day "0"` | Fault `API read() Version.created_at expected Integer data type(s) but got String (0):\n["0"]` |
| `in_calendar_day None` | Fault `API read() Version.created_at expected Integer data type(s) but got NilClass ():\n[nil]` |

Units: `HOUR`, `DAY`, `WEEK`, `MONTH`, `YEAR`, uppercase only. `in_next [1, "DAY"]` looks forward from now,
so a row created a moment before does not match.

**Same as REST:** the value shapes, the five units, the unit Fault, the 2-element Fault, the positive
integer Fault, and calendar offsets as a bare signed integer or a 1-element list.
**Differs from REST:** nothing. Not measured over REST: `n = 0` is accepted and matches nothing, and a
non-integer `n` or offset is refused with `expected Integer data type(s)`.
**Mock:** each of the nine relative operators raises `mockgun does not implement the '<relation>' relation
on the 'date_time' data type`. The mock must match them as above and raise each Fault above. The negating
operators must match rows with no date (field_types/date).
