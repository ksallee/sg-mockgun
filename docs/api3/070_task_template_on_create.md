# 070 task_template_on_create

re-asks: finding 083
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/070_task_template_on_create.py

**Q** Does `create("Shot", {..., "task_template": T})` make T's Tasks and TaskDependency rows in the
same call? What does `create` return?

T is an existing site template, read only: 5 undated tasks (Layout, Animation, Light, Comp, Previs),
5 edges, no assignees. Animation has `duration` 3360.

| call | answer |
|---|---|
| `create("Shot", {"project", "code", "task_template": T})` | 1.0 s. Returns `{"project", "code", "task_template", "type", "id"}`: the sent fields only, no `tasks` key |
| same, `return_fields=["tasks", "task_template"]` | Returns `"tasks": []` plus the sent fields `project`, `code` |
| `find("Task", [["entity", "is", shot]], ...)` straight after | 5 Tasks |
| the same 5 s later | 5 Tasks |
| `find_one("Shot", ..., ["tasks"])` | 5 links |
| each generated Task | `template_task` links to its template task. `task_template` is `None`. `project` is the sandbox. `pinned` False. Animation `duration` 3360 |
| `find("TaskDependency", [["task", "in", tasks]], ...)` | 5 rows, same `dependency_type` and `offset_days` as T's (one `start-to-start`, one `offset_days` 1) |
| `batch([{"request_type": "create", "entity_type": "Shot", "data": {..., "task_template": T}}])` | Returns the sent fields. 5 Tasks, 5 edges |

**Same as REST:** The Tasks and edges exist when `create` returns. Each Task copies T's fields, has
`template_task` set and `task_template` null. The `tasks` field in the create response is empty
although the Tasks exist. `batch` applies the template as `create` does.
**Differs from REST:** nothing. The api3 response omits `tasks` unless asked, as for any unsent field.
`return_fields` adds the sent fields to the response.
**Mock:** `create` stores `task_template` and makes no Task and no TaskDependency. `find` on the Shot's
Tasks returns `[]`. `return_fields=["tasks"]` returns only `tasks`, `type`, `id`: live also returns the
sent fields. To change: on create with `task_template`, copy each template Task (fields of finding 083,
`template_task` set, `task_template` null, `project` and `entity` from the new row) and each TaskDependency
between them; keep `tasks` `[]` in the create response; apply inside `batch` too.
