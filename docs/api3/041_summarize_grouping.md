# 041 summarize_grouping

re-asks: finding 020, finding 079
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project read
probe: probes/041_summarize_grouping.py

**Q** What structure does `summarize()` return with zero, one, two and three groupings, and what does each grouping type produce?

The client sends `grouping` as given, and only when it is not `None`. It raises
`ValueError("summarize() 'grouping' parameter must be a list or None")` for anything else.

## Nesting

| `grouping` | answer |
|---|---|
| not passed | `{"summaries": {...}, "groups": []}` |
| `[]` | `{"summaries": {...}, "groups": None}` |
| one entry | `groups` is a list of `{"group_name", "group_value", "summaries"}` |
| two entries | each first-level group also has `groups`, a list of second-level groups |
| three entries | three levels. The leaf level has no `groups` key |

A parent's `summaries` count equals the sum of its children's, at every level measured. Each group's
`summaries` has every summary field requested, as the top level does. Groups with no rows are not
returned.

```
{"summaries": {"id": N},
 "groups": [{"group_name": "<name>",
             "group_value": {"type": "Asset", "id": <id>, "name": "<name>", "valid": "valid"},
             "summaries": {"id": n},
             "groups": [{"group_name": "wtg", "group_value": "wtg", "summaries": {"id": n1}},
                        {"group_name": "ip", "group_value": "ip", "summaries": {"id": n2}}]}]}
```

## Each entry

A grouping entry is `{"field", "type", "direction"}`. `direction` is required:

| entry | answer |
|---|---|
| no `direction` key | Fault `API summarize() invalid/missing string 'direction':` + the entry + `Valid direction values:["asc", "desc"]` |
| `"direction": "up"` | the same Fault |
| `"direction": "desc"` | the `asc` order reversed |

`field` takes a dotted path: `entity.Shot.sg_sequence` groups Tasks by their Shot's Sequence.

## group_name and group_value per grouping

| field (data type) | type | `group_name` | `group_value` |
|---|---|---|---|
| entity (`step`, `entity`, dotted) | `exact` | the entity's name | `{"type", "id", "name", "valid": "valid"}` |
| entity | `entitytype` | `"Shot"` | `"Shot"` |
| status_list | `exact` | `"wtg"` | `"wtg"` |
| checkbox | `exact` | `"[ ]"`, `"[x]"` | `"f"`, `"t"` |
| text | `firstletter` | `"A"` | `"A"` |
| number (`id`) | `tens`, `hundreds`, `thousands`, `tensofthousands`, `hundredsofthousands`, `millions` | the bucket floor, int | the same int |
| date | `exact` | `"Mar 04 26"` | `"2026-03-04"` |
| date, date_time | `day` | `"March 04, 2026"` | `"2026-03-04"` |
| date, date_time | `week` | `"March 01, 2026 to March 07, 2026"` | `"2026-03-01"`, the Sunday |
| date, date_time | `month` | `"March 2026"` | `"2026-03-01"` |
| date, date_time | `quarter` | `"Q1 2026"` | `"2026-01-01"` |
| date, date_time | `year` | `"2026"` | `"2026-01-01"` |
| date, date_time | `clustered_date` | `"long_ago"`, `"last_few_months"`, `"last_few_weeks"` | the same string |
| duration | `oneday` | `"0 day"`, `"1 day"`, `"3 days"` | `"0.0"`, `"480.0"`, `"1440.0"`, minutes as a string |
| duration | `fivedays` | `"0 day"`, `"5 days"` | `"0.0"`, `"2400.0"` |
| any, no value set | any | `""` | `None` |

A duration bucket is a floor over 480-minute days: 1800 minutes is `"3 days"` under `oneday` and
`"0 day"` under `fivedays`.

## Order

- `asc` on a status_list follows the field's status order, not the alphabet: `wtg, ip, fin, apr, hld, rev, omt, ready`.
- `asc` on dates, numbers and text is ascending. `entitytype` is alphabetical.
- The empty group `""` / `None` comes last under `asc`.
- Ties between entity groups of equal name were not measured.

**Same as REST:** one level of `groups` per grouping entry, the leaf without `groups`, parent counts
equal to the sum of children (finding 079). `group_value` is the full entity dict on an entity
grouping, and the empty group is `""` / `None` (finding 020). The 17 grouping type names match.

**Differs from REST:** nothing measured. Finding 079 did not record `direction` being required or the
`group_name` formats per date bucket.

**Mock:** no `summarize` method on `sg_mockgun.Shotgun`; `sg-mockgun serve` answers Fault
`Error: API method "summarize" is not permitted.`. To change: add grouping with the nesting and the
`group_name`/`group_value` formats above, `direction` required, the empty group last, `groups: None`
for `grouping=[]`, and status order from the field's `valid_values`.
