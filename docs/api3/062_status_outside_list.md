# 062 status_outside_list

re-asks: finding 094, finding 009, recipe 002
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/062_status_outside_list.py

**Q** What does `sg_status_list` set to a value outside the list answer, on create and on update?

| call | answer |
|---|---|
| `create("Shot", {..., "sg_status_list": "zz_bad"})` | Fault `API create() CRUD ERROR #6: Invalid field value, update failed [5 - Update failed for [Shot.sg_status_list]: 'zz_bad' is not a valid status. Valid statuses: 'wtg', 'ip', 'fin', 'rev', 'apr', 'hld', 'omt', 'awd', 'bid', 'to'.]`; no row made |
| `update("Shot", <id>, {"sg_status_list": "zz_bad"})` | Fault `API update() CRUD ERROR #5: Update failed for [Shot.sg_status_list]: 'zz_bad' is not a valid status. Valid statuses: 'wtg', 'ip', 'fin', 'rev', 'apr', 'hld', 'omt', 'awd', 'bid', 'to'.`; value unchanged |
| Version, create and update | the same two Faults, `[Version.sg_status_list]` and the Version list |
| `update(t, <id>, {"sg_status_list": ""})` | `{"type": t, "id": <id>, "sg_status_list": null}`; reads `None` |
| `update(t, <id>, {"sg_status_list": None})` | the same |
| `update` to a value in the project's `hidden_values` (`awd` on Shot, `pass` on Version) | accepted; reads the hidden value |

Create says `CRUD ERROR #6: Invalid field value, update failed [5 - ...]`. Update says `CRUD ERROR #5:` and the inner message alone.
`Valid statuses` lists every `valid_values` entry, hidden ones included.
A Shot created with no status reads `wtg`. A Version reads `rev`.

**Same as REST:** the inner message `'zz_bad' is not a valid status. Valid statuses: ...` (finding 094, recipe 002).
**Differs from REST:** the `API create() CRUD ERROR #6:` and `API update() CRUD ERROR #5:` prefixes are api3 wording. Hidden values and `""` were not measured over REST.
**Mock:** stores `zz_bad` on create and update, and stores `""` as `""`. `update` returns a list holding the row, where the site returns the row. Must change: validate against `valid_values` (not `hidden_values`) with the Faults above; store `""` as `None`; return a dict from `update`.
