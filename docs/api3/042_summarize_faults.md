# 042 summarize_faults

re-asks: finding 020, finding 079
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project read
probe: probes/042_summarize_faults.py

**Q** What does `summarize()` raise for a bad summary type, a bad field, a bad grouping and bad arguments?

Each is `shotgun_api3.Fault` unless the table says otherwise. `<id>` is the sandbox project id the
filter names.

## Summary fields

| call on Task | answer |
|---|---|
| `{"field": "id", "type": "nope"}` | `API summarize() summary type 'nope' not valid for field Task.id with data type 'number'\nValid summary types:\n[:record_count, :count, :sum, :maximum, :minimum, :average]` |
| `{"field": "id"}` | `API summarize() invalid/missing key 'type' in 'summaries' hash:\n{"field" => "id"}` |
| `{"type": "count"}` | `API summarize() invalid/missing key 'field' in 'summaries' hash:\n{"type" => "count"}` |
| `{"field": "sg_not_a_field", "type": "count"}` | `API summarize() Task.sg_not_a_field doesn't exist:\n{"field" => "sg_not_a_field", "type" => "count"}` |
| `{"field": "entity.Shot.code", "type": "count"}` | no Fault: `{"summaries": {"entity.Shot.code": N}, "groups": []}` |
| `summary_fields` a dict, not a list | `Uncaught exception! no implicit conversion of String into Integer` |
| `{"field": "entity", "type": "count"}` | `Uncaught exception! Summary type not supported: entity count` |
| `{"field": "task_assignees", "type": "count"}` (multi_entity) | `Uncaught exception! undefined method 'process_summary_deep' for an instance of ShotgunHasManyAssociationField` |

A summary type that does not fit the data type raises
`API summarize() summary type '<type>' not valid for field <Type>.<field> with data type '<data type>'\nValid summary types:\n<list>`.
The list per data type:

| data type | valid summary types, as printed |
|---|---|
| number, percent | `[:record_count, :count, :sum, :maximum, :minimum, :average]` |
| date, date_time | `[:record_count, :count, :earliest, :latest]` |
| text | `[:record_count, :count]` |
| checkbox | `[:record_count, :checked, :unchecked]` |
| status_list | `[:record_count, :status_list, :status_percentage, :status_percentage_as_float]` |

`percentage` was refused on checkbox and on percent. No field measured accepts it.

## Entity type and filters

| call | answer |
|---|---|
| entity type `NotAType` | `API summarize() invalid/missing string entity 'type':\n` + the request, with filters in wire form + `\nValid entity types:\n` + every entity type, one per line |
| filter `["sg_not_a_field", "is", 1]` | `API summarize() Task.sg_not_a_field doesn't exist:\n{"path" => "sg_not_a_field", "relation" => "is", "values" => [1]}` |

The request inside the `NotAType` Fault is printed as
`{"type" => "NotAType", "summaries" => [...], "filters" => {"logical_operator" => "and", "conditions" => [{"path" => "project", "relation" => "is", "values" => [{"id" => <id>, "type" => "Project"}]}]}}`.

## Grouping

| entry on Task | answer |
|---|---|
| `{"field": "sg_status_list", "type": "nope", ...}` | `API summarize() grouping option 'nope' not valid for field Task.sg_status_list with data type 'status_list'\nValid grouping types:\n[:exact]` |
| `{"field": "sg_not_a_field", "type": "exact", "direction": "asc"}` | `API summarize() Task.sg_not_a_field doesn't exist:\n{"field" => "sg_not_a_field", "type" => "exact", "direction" => "asc"}` |
| `"direction": "up"` or no `direction` | `API summarize() invalid/missing string 'direction':\n<entry>\nValid direction values:["asc", "desc"]` |
| `grouping` a dict | `ValueError: summarize() 'grouping' parameter must be a list or None`, raised by the client |

A grouping type that does not fit the data type raises
`API summarize() grouping option '<type>' not valid for field <Type>.<field> with data type '<data type>'\nValid grouping types:\n<list>`.
A list longer than 80 characters prints one entry per line. The list per data type:

| data type | valid grouping types |
|---|---|
| number, percent | `exact, tens, hundreds, thousands, tensofthousands, hundredsofthousands, millions` |
| date, date_time | `exact, day, week, month, quarter, year, clustered_date` |
| duration | `exact, oneday, fivedays` |
| text, list | `exact, firstletter` |
| entity, multi_entity | `exact, entitytype, firstletter` |
| checkbox, status_list | `exact` |

**Same as REST:** a field the type lacks names `<Type>.<field> doesn't exist`. The summary and
grouping type names are the REST enums.

**Differs from REST:**
- An unknown summary type is checked against the field's data type over api3, and the Fault lists the
  types that data type allows. Over REST it is 400 `Request Parameters invalid.` with the full enum
  (finding 020).
- An unknown grouping type lists the types for the field's data type over api3. Over REST the 400
  lists all 17 (finding 079).

**Mock:** no `summarize` method; `sg-mockgun serve` answers Fault `Error: API method "summarize" is
not permitted.`. To change: raise these Faults with these messages, keyed on the field's data type.
The three `Uncaught exception!` cases are site bugs. The mock can raise the same text or a plain
Fault.
