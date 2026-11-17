# 072 dependency_cascade

re-asks: findings 087, 092, 093, 100
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/072_dependency_cascade.py

**Q** Does an upstream date write move the downstream Task? Which writes pin it? Does a pinned one set
`dependency_violation`? Does a `duration` write pin?

Two Tasks `up` and `dn`, both created 2026-03-02..03-03 (Mon..Tue), `duration` 960 set by the server.
Then `create("TaskDependency", {"task": dn, "dependent_task": up, "dependency_type": "finish-to-start-next-day"})`.
Each row is one `update`, then a read of both.

| write | up | dn | dn pinned | dn violation |
|---|---|---|---|---|
| edge created | 03-02..03-03 | 03-04..03-05 | False | False |
| up `due_date` 03-05 | 03-02..03-05, dur 1920 | 03-06..03-09 | False | False |
| up `due_date` 03-02 | 03-02..03-02, dur 480 | 03-03..03-04 | False | False |
| dn `duration` 1920 | | 03-03..03-06, dur 1920 | False | False |
| up `due_date` 03-04 | 03-02..03-04 | 03-05..03-10 | False | False |
| dn `due_date` 03-13 | | 03-05..03-13, dur 3360 | False | False |
| up `due_date` 03-03 | 03-02..03-03 | 03-04..03-12 | False | False |
| up `duration` 2880 | 03-02..03-09 | 03-10..03-18 | False | False |
| dn `start_date` 03-04 | | 03-04..03-12 | True | True |
| up `due_date` 03-10 | 03-02..03-10 | held | True | True |
| up `due_date` 03-02 | 03-02..03-02 | held | True | False |
| up `due_date` 03-10 | 03-02..03-10 | held | True | True |
| dn `pinned` False | | 03-11..03-19 | False | False |
| dn `pinned` True | | held | True | False |
| up `due_date` 03-12 | 03-02..03-12 | held | True | True |
| dn `dependency_violation` False | | | | Fault `API update() Task.dependency_violation is read only:` + `{"field_name" => "dependency_violation", "value" => false}` |

`update` returns `{"type", "id", <sent field>}`. `create("TaskDependency", ...)` returns the sent fields,
the Tasks as `{"id", "name", "type"}`.

**Same as REST:** A new edge moves the unpinned downstream Task (092). An upstream date or `duration` write
moves it later and earlier, `duration` held (087, 100). A `duration` write and a `due_date` write on `dn`
do not pin it; a `start_date` write does (093, 100). A pinned Task keeps its dates, and
`dependency_violation` is True while the edge is broken and False once satisfied. `pinned` False
reschedules at once.
**Differs from REST:** nothing. `dependency_violation` is read only: REST did not record a write to it.
**Mock:** No scheduling. A TaskDependency create moves nothing. `upstream_tasks` stays `[]`. An upstream
write moves nothing. `start_date` does not set `pinned`. `duration` stays `None` on a dated Task.
`dependency_violation` is writable and stays False. To change: derive `duration` from the dates on a
working-day calendar; reschedule unpinned downstream Tasks on an edge create and on an upstream
`start_date`, `due_date` or `duration` write; pin on a `start_date` write to a dependent; compute
`dependency_violation`; refuse its write with the Fault above.
