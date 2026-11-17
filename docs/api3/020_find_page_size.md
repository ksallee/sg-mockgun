# 020 find_page_size

re-asks: finding 082, finding 006
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/020_find_page_size.py

**Q** How many rows does `find` return with `page=1` and no `limit`, what does `limit=0` return, and which part is the client?

EventLogEntry, `created_at` in the last 30 days: 5649 to 5670 rows over the run. Other sessions were writing events.

## Client side, from `shotgun_api3.Shotgun.find`

- Page size is `server_info["api_max_entities_per_page"]`, else 500. This site sends 5000.
- `limit` or `page` below 0, or not an int: `ValueError`, before any request.
- `limit` up to the page size sets `entities_per_page` to `limit`, and turns `page=0` into `page=1`: one request.
- `page` not 0: one request for that page.
- `page=0` and `limit` 0 or above the page size: the client loops, page by page, until `paging_info.has_next_page` is false, then cuts to `limit`.
- `limit=0` is falsy: no limit.

| call | answer |
|---|---|
| `server_info["api_max_entities_per_page"]` | `5000` |
| `find(..., page=1)` | 5000 rows |
| `find(..., page=2)` | the remainder, 650 rows |
| `find(...)` | every row, 5657 |
| `find(..., limit=0)` | every row, 5657 |
| `find(..., limit=0, page=1)` | 5000 rows |
| `find(..., limit=10)` | 10 rows |
| `find(..., limit=501)` | 501 rows |
| `find(..., limit=-1)` | `ValueError: limit parameter must be a positive integer` |
| `find(..., page=-1)` | `ValueError: page parameter must be a positive integer` |

## Server side, raw `_call_rpc("read", params)`

| `paging` | answer |
|---|---|
| absent | Fault `API read() invalid/missing hash 'paging':` + the request |
| `{"current_page": 1}` | Fault `API read() invalid/missing integer 'paging' 'entities_per_page':` + `{"current_page" => 1}` |
| `entities_per_page` 0 | Fault `API read() CRUD ERROR #10: Read failed for entity type [EventLogEntry]` |
| `entities_per_page` 500, 501 | that many rows |
| `entities_per_page` 5000 | 5000 rows |
| `entities_per_page` 5001 | Fault `API read() 'paging' 'entities_per_page' > 5000 (maximum):` + `{"entities_per_page" => 5001, "current_page" => 1}` |
| `current_page` 0 | Fault `API read() CRUD ERROR #10: Read failed for entity type [EventLogEntry]` |

`paging_info` in the answer:

| flag sent | `paging_info` keys |
|---|---|
| `return_paging_info: true` | `page_count`, `current_page`, `entities_per_page`, `entity_count` |
| `return_paging_info_without_counts: true` (what this client sends) | `has_next_page`, `current_page`, `entities_per_page` |

**Same as REST:** the cap is 5000 rows a page and 5001 is refused (finding 082).
**Differs from REST:** REST defaults to 500 rows a page when `page[size]` is omitted. The api3 server has no default: `entities_per_page` is required, and the client fills 5000 from `server_info`. So `find(page=1)` returns 5000 rows, not 500. api3 has a total (`entity_count`) on request; REST has none (finding 006). `entities_per_page` 0 is a CRUD ERROR, not a parameter error.
**Mock:** `find` uses a page of 500. `page=1` on 1203 rows returns 500; it must return 5000 (or `server_info["api_max_entities_per_page"]` if the mock reports one). `limit=0` returns every row, which matches.
