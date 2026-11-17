# 006 calculated_filter

re-asks: field_types/calculated, finding 017
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/006_calculated_filter.py

**Q** Is a filter on a calculated field applied over api3?

`Task.workload` on one project's 1900 Tasks, 11 distinct values. The value tested is 3000, held by 533 Tasks
counted client-side. 673 Tasks have a larger value.

| filter | rows |
|---|---|
| `workload is 3000` | 533 |
| `workload is_not 3000` | 1367 |
| `workload greater_than 3000` | 673 |
| `workload between [3000, 3000]` | 533 |
| `workload in [3000]` | 533 |
| `workload is 123456789` | 0 |
| `workload is None` | 0 |
| order by `workload` desc | rows |

`in [None]` and `not_in [None]` raise Fault `API read() CRUD ERROR #10: Read failed for entity type [Task]` (002).

Every count matches the client-side count. The filter is applied.

**Same as REST:** nothing for filters.
**Differs from REST:** REST answers `cannot be used in a filter` for every relation on `Task.workload`
(field_types/calculated). api3 filters it with the number vocabulary. The REST answer is worth re-asking on this site.
**Mock:** refuses every relation on calculated (`UNFILTERABLE`). Must change: accept the relations of the
formula's result type and compare against the computed value; `in [None]` raises the CRUD error.
