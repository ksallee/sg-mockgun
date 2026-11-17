# 027 find_retired_link

re-asks: finding 060
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/027_find_retired_link.py

**Q** Does a link to a retired row read null, or drop out of a multi_entity list?

A Version in the sandbox with `sg_task` = a Task, `playlists` = [`doomed`, `kept`], `entity` = an Asset.

| step | `sg_task` | `playlists` | Version |
|---|---|---|---|
| linked | the Task | doomed, kept | found |
| delete the Task and `doomed` | `None` | kept | found |
| revive both | the Task | doomed, kept | found |
| delete the Asset | | | not found by `find`; found with `retired_only=True` |
| revive the Asset | the Task | doomed, kept | found, `entity` = the Asset |

| call, after the deletes | answer |
|---|---|
| `find("Version", [["sg_task", "is", <retired Task>]])` | 0 rows |
| `find("Version", [["playlists", "is", <retired Playlist>]])` | 0 rows |
| `find_one("Playlist", ..., ["versions"], retired_only=True)` on `doomed` | `versions` is `[]` |

- A link to a retired row reads `None` (entity) or drops out of the list (multi_entity).
- The link is kept: a revive brings it back.
- Deleting the Asset in `entity` retires the Version. Reviving the Asset revives the Version.

**Same as REST:** `sg_task` reads null; the Playlist drops out of `playlists`; deleting the entity retires the Version (finding 060).
**Differs from REST:** finding 060 does not record the revive: the links come back and the Version is revived with its entity.
**Mock:**
- A link to a retired row still reads as the link, and stays in a multi_entity list. It must read `None` and drop out, and come back on revive.
- A filter on the retired row's link matches. It must match 0 rows.
- Deleting an entity leaves the Version active. It must retire Versions linked through `entity`, and revive them with it.
