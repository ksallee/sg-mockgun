# 040 summarize_types

re-asks: finding 020, finding 079, finding 091
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project read
probe: probes/040_summarize_types.py

**Q** What does `summarize()` return for each summary type, with no grouping?

The client sends `{"type", "summaries", "filters"}` to the RPC method `summarize` and returns the
`results` value unchanged. A list `filters` is translated to `{"logical_operator", "conditions"}`
first. A dict `filters` is sent as it is, so it must already be in that wire form.

Every answer is `{"summaries": {<field>: <value>}, "groups": []}`. `N` is a row count.

| field (data type) | summary type | `summaries[field]` | Python type |
|---|---|---|---|
| `id` (number) | `record_count`, `count` | `N` | int |
| `due_date` (date) | `count` | rows with a value | int |
| `content` (text) | `count` | rows with a value | int |
| `entity` (entity), `sg_status_list` (status_list) | `record_count` | `N` | int |
| `est_in_mins` (duration) | `sum`, `maximum`, `minimum` | minutes | int |
| `est_in_mins` (duration) | `average` | minutes, 4 decimals | float |
| `cut_duration` (number), no value set | `sum` | `0` | int |
| `cut_duration` (number), `sg_movie_aspect_ratio` (float), `time_percent_of_est` (percent), no value set | `average` | `0.0` | float |
| `sg_movie_aspect_ratio` (float), no value set | `maximum` | `0.0` | float |
| `due_date` (date) | `earliest`, `latest` | `"YYYY-MM-DD"` | str |
| `created_at` (date_time) | `earliest`, `latest` | `"YYYY-MM-DD HH:MM:SS UTC"` | str |
| `milestone` (checkbox) | `checked`, `unchecked` | rows ticked, rows not ticked | int |
| `sg_status_list` (status_list) | `status_list` | one status code, the roll-up | str |
| `sg_status_list` with `"value": "<status>"` | `status_percentage` | `round(100 * rows in status / N)` | int |
| `sg_status_list` with `"value": "<status>"` | `status_percentage_as_float` | `floor(100 * rows in status / N)` | int |
| `sg_status_list` with a `value` no row has | both | `0` | int |

The date_time string is not converted to a `datetime` by the client. The client converts only
20-character `YYYY-MM-DDTHH:MM:SSZ` strings.

Measured shares, over 588 Tasks: `wtg` 493 gives 84 and 83, `fin` 16 gives 3 and 2, `hld` 5 gives 1 and 0.

| call | answer |
|---|---|
| `id count` + `due_date latest` | `{"summaries": {"id": N, "due_date": "YYYY-MM-DD"}, "groups": []}` |
| `id count` + `id maximum` | Fault `API summarize() duplicate summary request for field 'id':` + `{"field" => "id", "type" => "maximum"}` |
| `id count` + `id count` | Fault `API summarize() duplicate summary request for field 'id':` + `{"field" => "id", "type" => "count"}` |
| `summary_fields=[]` | `{"summaries": {}, "groups": []}` |
| filter matching no row: `id count`, `due_date latest`, `est_in_mins average`, `sg_status_list status_list` | `{"id": 0, "due_date": None, "est_in_mins": 0.0, "sg_status_list": "na"}` |
| `include_archived_projects=False` | same as without |
| `filter_operator="any"` | the list filter is sent as `"logical_operator": "or"` |
| dict filters `{"filter_operator": "all", "filters": [...]}` | Fault `API summarize() invalid/missing filters string 'logical_operator' (general condition):` + the dict |
| `sg_status_list status_percentage`, no `value` | Fault `API summarize() invalid/missing key 'value'. Percentage-based summaries require a valid 'value' key in the 'summaries' hash:` + `{"field" => "sg_status_list", "type" => "status_percentage"}` |
| same, `status_percentage_as_float` | the same Fault, with that type |

Faults for a summary type that does not fit the data type are in 042.

**Same as REST:** the `{"summaries", "groups"}` shape. `count` and `average` of an empty number
field are `0` and `0.0`. `status_list` rolls up to one status code. Two different fields in one
call return both.

**Differs from REST:**
- A second summary on the same field is a Fault over api3. Over REST the last entry wins at 200 (finding 020).
- `status_percentage` and `status_percentage_as_float` need `value` over api3, and return the share
  of rows in that status as an integer. Over REST they ignore `value` and return an integer that is
  no share (finding 079).

**Mock:** `sg_mockgun.Shotgun` has no `summarize` method: `AttributeError`. `sg-mockgun serve`
answers Fault `Error: API method "summarize" is not permitted.`. To change: add `summarize` with the
table above, the duplicate-field Fault and the `value` Fault. Empty numeric summaries are `0` or
`0.0`, empty `earliest`/`latest` are `None`, empty `status_list` is `"na"`.
