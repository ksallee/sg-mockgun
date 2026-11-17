# 065 task_delete_version

re-asks: finding 089
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/065_task_delete_version.py

**Q** Deleting a Task that a Version links to in `sg_task`: is `sg_task` nulled? Does revive restore it?

| step | `Version.sg_task` | `find("Version", [["sg_task", "is", task]])` | `find_one("Task", id)` |
|---|---|---|---|
| before | `{"id": <task>, "name": "...", "type": "Task"}` | 1 | the Task |
| `delete("Task", <task>)` answers `True` | `None` | 0 | `None` |
| `revive("Task", <task>)` answers `True` | the Task link again | 1 | the Task |

**Same as REST:** delete nulls `Version.sg_task`; revive restores it (finding 089).
**Differs from REST:** nothing.
**Mock:** keeps `sg_task` pointing at the deleted Task, and `find` on `sg_task` still matches it. Must change: on delete, null each entity field that points at the row and record it; on revive, restore it. Multi-entity fields are unmeasured here.
