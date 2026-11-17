# 050 nav_expand and nav_search

re-asks: finding 064
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/050_nav_expand_search.py

**Q** What do `nav_expand`, `nav_search_string` and `nav_search_entity` return, does the `__none__` bucket repeat, and what does a bad path answer?

`nav_expand` sends RPC `nav_expand` with `{path, seed_entity_field, entity_fields}`. Both search methods send RPC `nav_search` with `{root_path, seed_entity_field, search_criteria}`, where `search_criteria` is `{"search_string": ...}` or `{"entity": ...}`. All three return the RPC answer unparsed.

`nav_expand` answers one node: `{label, ref, path, parent_path, target_entities, has_children, children}`. `ref` is `{kind, value}`. `target_entities` is `{"type": "Version", "additional_filter_presets": [{"preset_name": "NAV_ENTRIES", "path": <path>, "seed": {"type": "Version", "field": "entity"}}]}`. A child has the same keys minus `children`, and minus `parent_path` below the project level.

| call | answer |
|---|---|
| `nav_expand("/")` | label `root`, kind `root`, one child per project, kind `entity`, value `{type: Project, id}` |
| `nav_expand("/Project/<p>")` | 2 children: `Assets` and `Shots`, kind `entity_type` |
| `nav_expand("/Project/<p>/Shot")`, 15 Sequences | 30 children, a Sequence then the bucket, 15 times. 16 distinct paths. Each bucket copy serialises identically. Two calls are byte-identical. |
| bucket child | `{"label": "Shots with no Sequence", "ref": {"kind": "entity_type", "value": "Shot"}, "path": "/Project/<p>/Shot/sg_sequence/Sequence/__none__", ...}` |
| `nav_expand(".../Sequence/<seq>")` | one child per Shot, kind `entity`, path `.../Sequence/<seq>/id/<shot>`, `has_children` false |
| `nav_expand(".../Sequence/__none__")`, nothing unsequenced | 1 child `{"label": "No Shots", "ref": {"kind": "empty", "value": null}, "has_children": false}` |
| `nav_expand(".../Shot/sg_sequence/__none__")` | answers, label `Shots with no __none__`, same `No Shots` child |
| `nav_expand("/Project/<p>/Asset")` | 13 children, kind `list`, path `.../Asset/sg_asset_type/<value>` |
| `entity_fields={"Shot": ["sg_status_list"]}` | added inside `ref.value`: `{"type": "Shot", "id": <shot>, "sg_status_list": "ip"}` |
| `seed_entity_field="Shot.code"` | Fault `Entity type provided is not part of the tree: Shot` |
| `nav_expand("")` | the root |
| `nav_expand("Project/<p>")` | answers, every `path` in the answer without the leading `/` |
| `nav_expand("/Project/999999999")` | Fault `Unexpected result looking for project: 999999999: 0 found.` |
| `nav_expand("/Project/999999999/Shot")` | answers, one `No Shots` child |
| `nav_expand("/Project/<p>/Bogus")`, `".../shots"` | Fault `Entity type provided is not part of the tree: Bogus` (or `shots`) |
| `nav_expand("/Project/<p>/Shot/sg_not_a_field/Sequence/1")` | Fault `Unexpected field name in path: sg_not_a_field (expecting sg_sequence)` |
| `nav_expand("/nope/nope/nope")` | Fault `Only 'Project' nav paths are currently supported: /nope/nope/nope` |
| `nav_search_string("/Project/<p>", <shot code>)` | list of `{label, incremental_path, path_label, ref: {id, type}, project_id}`. `incremental_path` lists each node path from the project down. `path_label` `Shots > <seq>`. |
| `nav_search_string(..., "a")` | 28 rows. Entity-type nodes match too: `{"label": "Assets", "path_label": "", "ref": {"id": null, "type": null}, ...}` |
| no match | `[]` |
| `nav_search_entity("/Project/<p>", <shot>)` | the same row as the string search |
| `nav_search_entity(..., {"type": "Shot", "id": 999999999})` | `[]` |
| `nav_search_entity(..., {"type": "Bogus", "id": 1})` | no Fault: `{"status": "failed", "description": "undefined method '[]' for nil"}` |
| `nav_search_string("/Project/999999999", "abc")` | no Fault: `{"status": "failed", "description": "undefined method 'select!' for nil"}` |
| `nav_search_string("/Project/<p>/Shot", ...)`, `("/nope", ...)` | no Fault: `{"status": "failed", "description": "Unsupported or invalid root_path provided. Only paths with the format '/Project/<project_id>' are currently supported."}` |

**Same as REST:** node keys, the `__none__` bucket repeated once per Sequence and byte-identical, `No Shots` with kind `empty`, both bucket spellings answering, the list-field grouping on Asset.
**Differs from REST:** nothing on the measured paths. REST error answers for bad paths were not recorded in finding 064. A failed search is a dict with `status` `failed`, not a Fault.
**Mock:** `sg_mockgun.Shotgun` has no `nav_expand`, `nav_search_string` or `nav_search_entity`: `AttributeError`. Over the wire, Fault `Error: API method "nav_expand" is not permitted.` Needed: the project tree, Shots grouped by `sg_sequence` with the repeated bucket, Assets grouped by `sg_asset_type`, `entity_fields` into `ref.value`, the search row shape, and the `{status, description}` failure dict.
