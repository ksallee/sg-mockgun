# 026 find_link_name

re-asks: finding 060
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/026_find_link_name.py

**Q** Does `find` return `name` in entity link dicts, single and multi entity, and is it the target's `cached_display_name`?

Up to 20 rows per link field, filtered `[field, "type_is", <target>]`.

| field | target | data type | links | dict keys | `name` == `cached_display_name` |
|---|---|---|---|---|---|
| Version.created_by, Note.created_by | ApiUser | entity | 20, 20 | id, name, type | 20, 20 |
| Version.user | HumanUser | entity | 20 | id, name, type | 20 |
| Task.task_assignees | HumanUser | multi_entity | 20 | id, name, type | 20 |
| Task.step | Step | entity | 20 | id, name, type | 20 |
| PublishedFile.published_file_type | PublishedFileType | entity | 20 | id, name, type | 20 |
| Version.sg_task | Task | entity | 20 | id, name, type | 20 |
| Note.tasks | Task | multi_entity | 21 | id, name, **template_task_id**, type | 21 |
| Version.notes | Note | multi_entity | 24 | id, name, type | 16 |
| Reply.entity | Note | entity | 20 | id, name, type | 16 |
| PublishedFile.version | Version | entity | 20 | id, name, type | 20 |
| Playlist.versions | Version | multi_entity | 11 | id, name, type | 11 |
| Version.playlists | Playlist | multi_entity | 11 | id, name, type | 11 |
| Version.project | Project | entity | 20 | id, name, type | 20 |
| Version.entity | Shot | entity | 20 | id, name, type | 20 |
| Task.entity | Asset | entity | 20 | id, name, type | 20 |
| HumanUser.department | Department | entity | 2 | id, name, type | 2 |
| Shot.sg_sequence | Sequence | entity | 20 | id, name, type | 20 |

`name` was never null.

Not readable on this site:

| target | reason |
|---|---|
| ClientUser, Tag, Delivery | 0 rows on the site |
| Group | 4 rows, none linked from `Note.addressings_to` or `HumanUser.groups` |

## Note: HTML escaping

The 8 Note links that differ have an apostrophe. The link `name` is plain text. The stored `cached_display_name` is HTML-escaped, as `&#39;` or `&#x27;`.

| | value |
|---|---|
| `subject` | `<user>'s Note on Django` |
| `content` | `looks good to me!` |
| link `name` | `<user>'s Note on Django - looks good to me!` |
| `cached_display_name` | `<user>&#x27;s Note on Django - looks good to me!` |

A Note's display name is `<subject> - <content>`.

## Note.tasks

Task elements of `Note.tasks` have a fourth key, `template_task_id`. Over 51 elements, 38 were null and 13 were an integer id.

**Same as REST:** every link dict has `id`, `name`, `type`; `name` is the target's display name, single and multi entity (finding 060).
**Differs from REST:** finding 060 does not record the HTML escaping of `cached_display_name`, the `<subject> - <content>` form, or `template_task_id` in `Note.tasks`.
**Mock:** link dicts have `id`, `name`, `type` with `<subject> - <content>` for a Note, which matches. `Note.tasks` elements lack `template_task_id`. Reading the field `cached_display_name` on a Note with an apostrophe must return the escaped form; the mock does not model that.
