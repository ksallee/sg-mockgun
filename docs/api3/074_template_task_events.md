# 074 template_task_events

re-asks: findings 090, 049
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/070_task_template_on_create.py

**Q** Which EventLogEntry rows does a `create` with `task_template` write? Is there a `template_task`
change row with `in_create`?

The event log is on for this script: rows were written. One Shot created with T (5 tasks, 5 edges), read
back with `find("EventLogEntry", ...)` filtered to its rows.

| rows for | event_type and attribute_name |
|---|---|
| the Shot, 11 | `Shotgun_Shot_New`; `Shotgun_Shot_Change` `code`, `sg_latest_vendor_status`, `sg_status_list`, `sg_shot_type`, `task_template`, each `in_create` True; `tasks` x5, `in_create` True |
| the 5 Tasks, 51 | per Task `Shotgun_Task_New` and `Shotgun_Task_Change` `color`, `content`, `entity`, `sg_sort_order`, `sg_status_list`, `step`, `template_task`; `duration` on the one Task with a duration; one `upstream_tasks` or `downstream_tasks` row per edge end |
| the 5 edges, 17 | per edge `Shotgun_TaskDependency_New`, `Change` `task`, `Change` `dependent_task`; plus `dependency_type` on the `start-to-start` edge and `offset_days` on the edge with `offset_days` 1 |

A `template_task` row:

```
event_type "Shotgun_Task_Change", attribute_name "template_task", entity {"id", "name": "Comp", "type": "Task"}
user {"id", "name": "<script> 1.0", "type": "ApiUser"}, session_uuid null
meta {"type": "attribute_change", "attribute_name": "template_task", "entity_type": "Task", "entity_id": <task>,
      "in_create": true, "field_data_type": "entity", "old_value": null,
      "new_value": {"name": "Comp", "type": "Task", "id": <template task>, "valid": "valid", "status": "wtg", "uuid": "<uuid>"}}
```

`find("EventLogEntry", [["attribute_name", "is", "template_task"], ["entity", "in", <the 5 Tasks>]])`
returns 5 rows.

**Same as REST:** A generated Task logs as a hand-made one plus a `template_task` row with `in_create` true,
credited to the ApiUser, `session_uuid` null. The Shot logs `task_template` and one `tasks` row per Task.
Each edge logs `_New`, `task`, `dependent_task`.
**Differs from REST:** nothing. 090 lists 3 rows per edge for default edges; a non-default
`dependency_type` or `offset_days` adds one row each. The Shot's `task_template` row has `in_create` True
on create.
**Mock:** No template apply, so no Task, TaskDependency or `tasks` rows. The Shot's create logs `_New` and
one Change per sent field. To change: when the apply lands (api3 070), log each generated Task, edge and
Shot `tasks` change as above, `in_create` True, credited to the caller.
