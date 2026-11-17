# 043 text_search_shape

re-asks: finding 046, finding 053, finding 063
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project read
probe: probes/043_text_search_shape.py

**Q** What structure does `text_search()` return for one and several entity types, with and without a filter per type?

The client translates each `entity_types` value with the same filter translation as `find`, to
`{"logical_operator": "and", "conditions": [...]}`, and sends
`{"text", "entity_types", "project_ids", "max_results"}` to the RPC method
`query_display_name_cache`. `project_ids=None` is sent as `[]`. `limit` is sent as `max_results`.
It returns `_parse_records(results)[0]`: the `results` dict, with `&lt;` replaced by `<` in its
top-level string values only.

## The answer

```
{"matches": [{"id": <id>, "type": "Version", "name": "<name>", "project_id": <id>,
              "links": ["Shot", "<name>"], "status": "rev", "image": "<url>"},
             {"id": <id>, "type": "Shot", "name": "<name>", "project_id": <id>,
              "links": ["", ""], "status": "wtg", "image": None}],
 "terms": ["sbx"]}
```

| key | value |
|---|---|
| `id`, `project_id` | int |
| `type` | the entity type |
| `name` | the row's display name |
| `links` | `[linked type, linked name]`, or `["", ""]` when the row links to nothing |
| `status` | the status code, or `None` on a type with no status field |
| `image` | a thumbnail URL, or `None` |
| `terms` | the text split on whitespace, lowercased |

Version and Task rows link to their `entity`. Shot and Asset rows have `["", ""]`.

## Calls

| call | answer |
|---|---|
| `{"Shot": []}`, `project_ids` the sandbox | the Shot rows that match |
| `{"Shot": [["project", "is", <project>]]}`, no `project_ids` | the same rows |
| `{"Shot": [], "Asset": [], "Version": []}` | rows of all three types in one `matches` list |
| a filter on one type | narrows that type only |
| a tuple of filters | accepted, as a list |
| two conditions | both apply, as `and` |
| a filter no row passes | `{"matches": [], "terms": ["sbx"]}` |
| a text no row holds | `{"matches": [], "terms": ["zzznotaword"]}` |

## limit

Text `sbx` over Shot, Asset, Version and Task, 43 rows match:

| `limit` | rows |
|---|---|
| `None` | 25 |
| `0` | 0 |
| `1` | 1 |
| `25` | 25 |
| `26` | 26 |
| `100`, `1000` | 43 |

## Order

Rows whose own name holds every word come first, shortest name first. Rows matched only through
their link come after them, shortest name first. Types are mixed. Over 43 rows: Shot (8 characters),
Asset (9), 33 Versions (13 to 30), then 7 Tasks (3 to 7) and one Version (8), all matched through
their link. Ties of equal length were not ordered here.

**Same as REST:** `name`, `status` and `links` as a pair of strings (finding 046). One call covers
several types, with a filter per type (finding 063). 25 rows by default (finding 053). Rows are
shortest name first, across types (finding 053).

**Differs from REST:**
- Over api3 a row is flat, with `project_id` and `image`, under `matches`, next to `terms`. Over
  REST it is `{id, type, attributes: {name, links, status}, links: {self}}` under `data` (finding 046).
- `limit` raises the count past 25 over api3. Over REST `page.size` stops at 25 (finding 053).
- Over api3 link-only matches come after own-name matches. Finding 053 has no link-only row in its order sample.

**Mock:** `sg_mockgun.Shotgun` has no `text_search` method: `AttributeError`. `sg-mockgun serve`
answers Fault `Error: API method "query_display_name_cache" is not permitted.`. To change: add
`text_search` returning `{"matches", "terms"}` with the row keys above, `max_results` default 25,
and the order above.
