# 021 find_retired_only

re-asks: finding 040, finding 060
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/021_find_retired_only.py

**Q** Does `retired_only=True` return only retired rows?

Two Versions in the sandbox, `<active>` and `<retired>`. Each find filters `["id", "in", [<active>, <retired>]]`.

| step | `find(...)` | `find(..., retired_only=True)` |
|---|---|---|
| both active | both | `[]` |
| `delete("Version", <retired>)` returns `True` | `[<active>]` | `[<retired>]` |
| `revive("Version", <retired>)` returns `True` | both | `[]` |
| both deleted at cleanup | `[]` | both |

| call | answer |
|---|---|
| `find("Version", [["project", "is", <sandbox>]], retired_only=True)` | 5832 rows, none of them found by a default `find` on their ids |
| `find_one(..., ["code", "project", "retirement_date"], retired_only=True)` on the retired row | `{type, id, code, project}`. `retirement_date` is absent from the dict. |
| filter `["retirement_date", "is_not", None]`, with or without `retired_only` | Fault `API read() Version.retirement_date doesn't exist:` + `{"path" => "retirement_date", "relation" => "is_not", "values" => [nil]}` |
| `summarize` count on the retired row's id | `{"id": 0}` |

The client sends `return_only: "retired"` for `retired_only=True`, else `"active"`.

**Same as REST:** a retired row is out of a default read and in `options[return_only]=retired` (finding 060).
**Differs from REST:** nothing measured.
**Mock:** matches for find. `retired_only=True` returns only retired rows. Mock raises `KeyError: 'retirement_date'` for a filter on `retirement_date`; it must raise the Fault above. The mock has no `summarize`.
