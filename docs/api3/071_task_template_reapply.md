# 071 task_template_reapply

re-asks: findings 084, 102
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/071_task_template_reapply.py

**Q** What does `update("Shot", id, {"task_template": ...})` do on a Shot that already has Tasks: add the
missing ones, re-sync the linked ones?

U is an existing site template, read only: Model@Model, Comp@Comp, edge Comp on Model
`finish-to-start-next-day`. T is the 5-task template of api3 070.

Setup: Shot created with U (2 Tasks, 1 edge). Then Comp renamed `renamed` and set `ip`, the edge deleted,
the generated Model deleted, and a hand-made Task `Model`@Model added (no `template_task`).

| call | returns | Tasks after | edges after |
|---|---|---|---|
| `update(..., {"task_template": U})`, the stored value | `{"type", "id", "task_template": U}` | unchanged: `renamed` ip, hand-made Model | none |
| `update(..., {"task_template": None})` | `{"type", "id", "task_template": None}` | unchanged | none |
| `update(..., {"task_template": U})` | `{"type", "id", "task_template": U}` | `renamed` back to `Comp`, status `ip` kept. A second `Model` made, `template_task` set. The hand-made Model kept | Comp on the new Model, `finish-to-start-next-day`, new id |
| `update(..., {"task_template": T})` | `{"type", "id", "task_template": T}` | U's 3 Tasks kept. T's 5 Tasks made | U's edge kept. T's 5 edges made |
| `update(..., {"task_template": U, "task_template_mode": "replace"})` | Fault `API update() Shot.task_template_mode doesn't exist:` + `{"field_name" => "task_template_mode", "value" => "replace"}` | `task_template` still T, nothing applied | |

**Same as REST:** The apply runs only when the value changes: the stored value again does nothing.
The match key is `template_task`: a missing template Task is re-created, even beside a hand-made Task of
the same `content` and `step`. A linked Task is re-synced: `content` overwritten, `sg_status_list` kept.
An edge between linked Tasks is re-created. No Task is removed. There is no mode key.
**Differs from REST:** nothing.
**Mock:** `update` stores `task_template` and makes, re-syncs and wires nothing. `update` returns a list
`[{...}]`: live returns a dict. `task_template_mode` raises `ShotgunError: task_template_mode is not a valid
field for entity Shot`: live raises Fault `API update() Shot.task_template_mode doesn't exist:` + the
request. To change: on a changed `task_template` value, create each template Task no Task on the entity
links to by `template_task`, re-sync the linked ones (finding 102 table), reset the edges between them;
return a dict from `update`.
