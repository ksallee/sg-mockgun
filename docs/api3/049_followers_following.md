# 049 followers and following

re-asks: finding 043, finding 066
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/049_followers_following.py

**Q** What do `followers` and `following` return? No follow or unfollow is sent.

`followers` sends RPC `followers` with `{"entity"}`. `following` sends RPC `following` with `{"user"}`, plus `project` and `entity_type` when given. Both return the RPC answer unparsed: a list of dicts.

| call | answer |
|---|---|
| `following(<user>)` | list of 896, `{'Note': 707, 'Task': 189}`, each row `{id, type}` |
| `following(<user>, entity_type="Task")` | 189 |
| `following(<user>, project=<p>)` | 865 |
| `following(<user>, project=<p>, entity_type="Task")` | 158 |
| `following(<user>, entity_type="tasks")` | Fault `API following() invalid/missing 'type' string:` + `"tasks"` + `Valid types:` + every entity type and connection entity, one per line |
| `following(<user>, entity_type="Bogus")` | the same Fault with `"Bogus"` |
| `following(<user>, project={"type": "Project", "id": 999999999})` | Fault `API following() project not found: Project 999999999` |
| `following({"type": "HumanUser", "id": 999999999})` | Fault `API following() user not found: HumanUser 999999999` |
| `following({"type": "ApiUser", ...})` | Fault `API following() invalid user type. Must be HumanUser. Found: ApiUser` |
| `following({"type": "Shot", ...})` | Fault `API following() invalid user type. Must be HumanUser. Found: Shot` |
| `followers(<task>)` | list, each row `{id, name, status, type, uuid, valid}`. `status` `act`, `valid` `valid`, `uuid` a string. |
| `followers({"type": "Shot", "id": 999999999})` | Fault `API followers() entity not found: Shot` |
| `followers({"type": "Bogus", "id": 1})` | Fault `API followers() invalid/missing entity hash string 'type':` + `{"type" => "Bogus", "id" => 1}` + `Valid entity types:` + the list |
| `followers({"type": "shots", "id": 1})` | the same Fault with `"shots"` |
| `followers({"type": "Shot"})` | Fault `API followers() invalid/missing entity hash integer 'id':` + `{"type" => "Shot"}` |

**Same as REST:** neither list pages. `following` rows are type and id only, no name and no follow date. REST also measured 896 rows for one user.
**Differs from REST:** `following` takes the CamelCase type only: `"tasks"` is a Fault, where REST accepts `notes` and `Note`. `followers` rows add `status`, `valid` and `uuid` and have no `links`. Errors are named Faults where REST answers 404.
**Mock:** `sg_mockgun.Shotgun` has no `followers`, `following`, `follow` or `unfollow`: `AttributeError`. Over the wire, Fault `Error: API method "followers" is not permitted.` Needed: a follow table, `following` with the `project` and `entity_type` filters, `followers` rows with the six keys, and the Faults above.
