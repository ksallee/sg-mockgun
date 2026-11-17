# 061 project_create_empty

re-asks: finding 011, entity_types/Project
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, a refused Project create sent, no row made
probe: probes/061_project_create_empty.py

**Q** What does `create("Project", {})` answer?

| call | answer |
|---|---|
| `create("Project", {})` | Fault `API create() invalid/missing array 'fields':` + `{"type" => "Project", "fields" => [], "return_fields" => ["id"]}` |
| Project count, before and after | unchanged |

The refusal is the empty field list check, the same as 060 for Shot and Version. A Project create with fields but no `name` stays unmeasured: it can create a Project.

**Same as REST:** nothing to compare. Finding 011 never sent a body without `name`.
**Differs from REST:** unmeasured over REST.
**Mock:** `create("Project", {})` returns `{"type": "Project", "id": <id>}`. Must change: raise the Fault above for an empty `data` on any type.
