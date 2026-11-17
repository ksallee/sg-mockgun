# 063 batch

re-asks: recipe 002, finding 028, finding 113
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/063_batch.py

**Q** Is `batch` atomic when a later request fails? In what order are results? Does a batch create missing `project` return an id?

Each failing batch was `[create Shot, update <base> description "after", <bad>]`.

| `<bad>` | answer | after |
|---|---|---|
| update Shot id 0 | Fault `API batch() request with index 2 failed.  All requests rolled back.` + newline + `API update() CRUD ERROR #3: Entity of type [Shot] with id=0 does not exist.` | 0 rows created; description `before` |
| update Shot id 999999999 | the same, `id=999999999` | the same |
| delete Shot id 999999999 | the same, `API delete() CRUD ERROR #3: ...` | the same |
| create Shot `sg_status_list` `zz_bad` | the same prefix + the create Fault of 062 | the same |

| call | answer |
|---|---|
| `batch([update, create, update, create])` | 4 results in request order: `{"type", "id", "description"}`, `{"id", "project", "code", "type"}`, update, create |
| `batch([delete Shot <id>])` | `[true]` |
| `create(t, {"code": "x"})`, Shot and Version | Fault `API create() missing 'project' attribute:` + the fields |
| `batch([create t {"code": "x"}])`, Shot and Version | Fault `API batch() request with index 0 failed.  All requests rolled back.` + newline + `API create() missing 'project' attribute:` + the fields; no id returned |

The Fault names the failing request by index, then the single call's Fault. The prefix has two spaces after `failed.`.
Rolled-back creates consumed ids: the next committed Shot's id skipped seven.

**Same as REST:** atomic; one failing request rolls back the others. Results are one per request, in request order.
**Differs from REST:** a batch create missing `project` is refused over api3. Over REST it answers 200 with an id for an unreadable row (recipe 002). A batch delete answers `true`; REST answers a row with `did_delete`. The Fault is wrapped in the `API batch() request with index N failed.` prefix.
**Mock:** not atomic: the create before a failing update stays (1 row made), and the error is `ShotgunError: No entity of type Shot exists with id 0`. A batch create without `project` succeeds. A batch delete answers `[True]`. Must change: roll back on any failure and raise the Fault above with the index prefix; apply the single-create checks of 060 inside a batch.
