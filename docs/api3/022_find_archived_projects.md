# 022 find_archived_projects

re-asks: finding 018
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/022_find_archived_projects.py

**Q** Is any project archived, and what does `include_archived_projects=False` do?

| call | answer |
|---|---|
| `find("Project", [], ["archived"])` | 52 projects, `archived` True on 30 |
| `find("Project", [["archived", "is", True]])` | 30 |
| `find("Project", [], include_archived_projects=False)` | 22 |
| `summarize("Version", count id)` | 1351 |
| `summarize("Version", count id, include_archived_projects=False)` | 1315 |

- `include_archived_projects=False` drops rows whose `project` is archived.
- On `Project` it drops the archived projects themselves.
- The client sends `include_archived_projects: false` only when it is False. The server default is True.

**Same as REST:** `archived` is a checkbox on Project (finding 018).
**Differs from REST:** finding 018 counted 0 archived of 22. This site now has 30 archived of 52. The REST side of this option is unmeasured.
**Mock:** drops rows in an archived project. It keeps archived Project rows: 2 of 2 with one archived. It must drop a Project row whose `archived` is True. The "documented, unprobed" comment in `find` can cite `# api3 022`.
