# 001 unknown_relation

re-asks: finding 017, field_types/*
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/001_unknown_relation.py

**Q** What does `find` raise for a relation that does not exist, on one stock field of each data type?

`find(<type>, [[<field>, "definitely_not_an_operator", "x"]], ["id"], limit=1)`. Every call raises
`shotgun_api3.Fault`. Two message shapes.

Shape A, 19 types. The sent filter and the valid list are Ruby `pp` output: a line wraps past 80 columns.

```
API read() Shot.code's 'text' data type doesn't support 'definitely_not_an_operator' 'relation':
{"path" => "code",
 "relation" => "definitely_not_an_operator",
 "values" => ["x"]}
Valid relations:
["contains",
 "not_contains",
 "is",
 "is_not",
 "starts_with",
 "ends_with",
 "in",
 "not_in"]
```

A short hash or list stays on one line: `{"path" => "frame_count", "relation" => "not_between", "values" => [1]}`
and `["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]`.

Shape B, 4 types. No `Valid relations`.

```
API read() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter:
{"path" => "sg_uploaded_movie",
 "relation" => "definitely_not_an_operator",
 "values" => ["x"]}
```

| field | data type | shape | Valid relations |
|---|---|---|---|
| Shot.code | text | A | contains, not_contains, is, is_not, starts_with, ends_with, in, not_in |
| Version.frame_count | number | A | is, is_not, greater_than, less_than, between, in, not_in |
| Version.sg_movie_aspect_ratio | float | A | same as number |
| Shot.sg___complete | percent | A | same as number |
| Shot.sg_bid___total | duration | A | same as number |
| Sequence.sg_timecode | timecode | A | same as number |
| Shot.sg_client_turnover_date | date | A | is, is_not, greater_than, less_than, in_last, not_in_last, in_next, not_in_next, in_calendar_week, in_calendar_month, in_calendar_day, in_calendar_year, between, in, not_in |
| Version.created_at | date_time | A | same as date |
| Version.flagged | checkbox | A | is, is_not |
| Note.sg_note_type | list | A | is, is_not, in, not_in |
| Version.sg_status_list | status_list | A | is, is_not, in, not_in |
| Version.entity | entity | A | is, is_not, name_contains, name_not_contains, name_is, type_is, type_is_not, in, not_in |
| Version.tasks | multi_entity | A | same as entity |
| Step.entity_type | entity_type | A | is, is_not, in, not_in |
| Task.color | color | A | is, is_not, in, not_in |
| Icon.uuid | uuid | A | is, is_not, in, not_in |
| Version.image | image | A | is, is_not |
| Note.meta | jsonb | A | is, is_not, contains, not_contains |
| Shot.step_0 | pivot_column | A | is, is_not |
| Task.workload | calculated | A | same as number |
| Version.sg_uploaded_movie | url | B | none |
| HumanUser.password_proxy | password | B | none |
| Task.splits | serializable | B | none |
| Shot.open_notes_count | summary | B | none |

**Same as REST:** the text of the message up to the first colon is the REST `title`. The `Valid relations`
lists match the REST lists for 19 types, order included. url, password, serializable and summary answer
`cannot be used in a filter`.
**Differs from REST:**
- api3 has one message: the title, `:`, newline, the sent filter, newline, `Valid relations:`, newline, the list.
  REST splits it into `title` (ending in `.` for shape B) and `source`. The REST `Value:` label is absent.
- Hash and list are Ruby `pp` output, wrapped at 80 columns, not one line.
- `values` echoes the value sent (`["x"]`). REST echoed `[nil]` on the shape B types.
- `Task.workload` (calculated) answers shape A with the number list. REST answered `cannot be used in a filter`. See 006.

**Mock:** raises `ShotgunError`, not `Fault`. Message is one line, `. Valid relations: [...]`, without the sent
filter. Shape B ends in `.` with no filter. `entity` and `multi_entity` raise
`mockgun does not implement the 'definitely_not_an_operator' relation on the 'entity' data type`.
`calculated` answers shape B. Must change: raise `Fault`; build the api3 text with the sent filter and a
`pp`-style inspect at 80 columns; add the entity and multi_entity lists; move `calculated` out of `UNFILTERABLE`.
