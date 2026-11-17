# 073 task_delete_revive

re-asks: finding 089
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/073_task_delete_revive.py

**Q** Does `delete("Task", up)` retire its TaskDependency rows? Does `revive("Task", up)` restore them?

`up` and `dn` dated 2026-03-02..03-03, edge dn on up `finish-to-start-next-day`. `dn` reads 03-04..03-05.

| call | answer |
|---|---|
| `delete("Task", up)` | `True` |
| then the edge: `find_one` by id | `None` |
| the edge: `find(..., retired_only=True)` | 1 row |
| `dn` | 03-04..03-05 unchanged. `upstream_tasks` `[]`. `find("Task", [["upstream_tasks", "is", up]])` 0 rows |
| `revive("Task", up)` | `True` |
| then the edge | live again, same id. `dn.upstream_tasks` `[up]`, `up.downstream_tasks` `[dn]` |
| `revive("Task", up)` again | `False` |

Calls on the retired edge, after a second `delete("Task", up)`:

| call | answer |
|---|---|
| `update("TaskDependency", edge, {"offset_days": 1})` | `{"type": "TaskDependency", "id": <edge>, "offset_days": 1}`, no error |
| `delete("TaskDependency", edge)` | `False` |
| `revive("TaskDependency", edge)` | `True`. The edge is live with `up` still retired. `dn.upstream_tasks` `[]` |
| `revive("Task", up)` | `True`. `dn` moves to 03-05..03-06, from the `offset_days` 1 written while retired |

**Same as REST:** Deleting a Task retires its TaskDependency rows and unlinks the neighbour. The neighbour's
dates do not move. Revive restores the rows with the same ids and relinks both ends; the chain is
rescheduled from the upstream's dates.
**Differs from REST:** REST did not record writes to a retired edge. Over api3 an `update` on a retired
TaskDependency succeeds and the value applies after revive. A TaskDependency revives alone while its
upstream Task stays retired.
**Mock:** `delete("Task")` retires only the Task: its TaskDependency stays live and `find(...,
retired_only=True)` returns `[]`. `update` on a retired row succeeds, as live. `delete` of a retired row
returns `False` and `revive` returns `True` then `False`, as live. To change: retire a Task's TaskDependency
rows with it, unlink both neighbours, and revive them with the Task.
