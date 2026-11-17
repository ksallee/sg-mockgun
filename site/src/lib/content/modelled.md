Each area lists what sg-mockgun does and the [api3 answers](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/README.md) it follows. A gap is
listed under "Not modelled". Per-call results are in the [coverage table](https://github.com/ksallee/sg-mockgun/blob/main/docs/coverage.md).

Upstream mockgun covers `find`, `create`, `update`, `delete`, `revive` and `batch` against
a pickled schema. sg-mockgun keeps that surface and its tests, and changes its answers to the site's.

## Filters

Answers [001](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/001_unknown_relation.md) to [006](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/006_calculated_filter.md) and
[010](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/010_entity_unset_rows.md) to [015](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/015_entity_in_empty.md).

- The relations each data type accepts, and the Fault for one it refuses.
- Entity and multi_entity operators, including rows whose link is unset.
- Dotted paths through links. A mismatched link reads null. An unknown path is refused.
- Relative date operators.
- Text and list `is` match case-insensitively.
- A refused filter is refused before the scan, even when another filter matches no row.

## find options

Answers [020](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/020_find_page_size.md) to [027](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/027_find_retired_link.md).

- `limit`, `page` and the page size.
- `order` with several keys, on entity and dotted fields, and where None sorts.
- `retired_only` and `include_archived_projects`.
- `additional_filter_presets` with `LATEST`.
- Entity links have `name`, the target's display name. A link to a retired row reads null.

## Writes per data type

Answers [030](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/030_text_empty_and_spaces.md) to [039](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/039_unknown_field_write.md).

- Text, checkbox, float, number, multi_entity, color, timecode, jsonb, image, serializable, password, currency and footage writes: what is stored and what is refused.
- uuid, calculated, summary and pivot_column are read only.
- An unknown field in a create or an update is refused.
- `create` returns the fields sent. `created_at`, `updated_at`, `created_by`, `updated_by` and `cached_display_name` are set.

## Records

Answers [027](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/027_find_retired_link.md) and [060](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/060_create_contract.md) to
[065](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/065_task_delete_version.md).

- A create with no fields is refused. A Shot, Version, Asset, Sequence, Task, Playlist, PublishedFile, Note or Delivery create without `project` is refused.
- An omitted identity field reads `New <Type> <id>`. An empty one is refused and spends an id. `code` is not unique.
- A status outside `valid_values` is refused. `""` stores `None`.
- `update` returns the row.
- `batch` is atomic. A failing request raises a Fault naming its index, and the ids it handed out stay spent.
- A delete nulls entity fields that link to the row and retires the Versions whose `entity` it is. A revive puts both back.

Hooks:

- `sg.require_project = False` lets a create skip the `project` check.
- `sg.set_project_schema(project, entity_type, field, visible=..., hidden_values=...)` sets what `schema_field_read(..., project_entity=project)` reads.

## Task Templates and scheduling

Answers [070](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/070_task_template_on_create.md) to [074](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/074_template_task_events.md).

A create or a changed `task_template` applies the template from the TaskTemplate and its template
Tasks in the mock. Seed them with `create` or `load`.

- Missing template Tasks are created with `template_task` set. Linked Tasks are re-synced. Edges are rewired. No Task is removed.
- `duration` counts working days at 480 minutes. Downstream Tasks reschedule on an edge or an upstream date write. A `start_date` write pins a dependent. `dependency_violation` is read only.
- Deleting a Task retires its TaskDependency rows. Reviving it restores them.

`sg.set_work_week([True] * 5 + [False] * 2)` sets the working days, Monday first (default Mon to Fri).

Not modelled: event rows for rescheduled dates and re-synced fields, the dependency loop, duplicate
and type refusals.

## summarize, text_search and info

Answers [040](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/040_summarize_types.md) to [046](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/046_info.md).

- `summarize` with each summary type, grouping, and the site's Faults.
- `text_search` result shape, matching and Faults.
- `info()` returns the site's payload. `sg.set_info(**values)` changes keys of it.

## Attention, navigation and site reads

Answers [047](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/047_note_thread_read.md) to [052](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/052_export_page.md).

`note_thread_read`, `activity_stream_read`, `followers`, `following`, `nav_expand`,
`nav_search_string`, `nav_search_entity`, `preferences_read`, `work_schedule_read`,
`user_subscriptions_read` and `export_page` answer in process and over the [HTTP server](/docs/server/).
Activity stream rows are the `create` rows of the event log. Site data the mock cannot know has a
default and a setter:

- `sg.set_following(user, entities)`: what `user` follows. Default: nothing.
- `sg.set_preferences(values)`: preferences. Default: 17 keys of the recorded types.
- `sg.set_work_schedule(week=None, exceptions=None)`: seven booleans, Monday first, and rules per `YYYY-MM-DD`. Default: Monday to Friday, `STUDIO_WORK_WEEK`.
- `sg.set_user_subscriptions(subscriptions)`: keyed by HumanUser id as a string. Default: `{}`.

`export_page` refuses every page, as a site with no exportable page does.

## Media

Answers [053](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/053_upload_field.md) to [058](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3/058_share_thumbnail.md).

- `upload` creates an Attachment, sets a File/Link field to its `this_file`, and returns its id. `tag_list` creates missing Tags.
- The file's bytes are kept in memory, per instance. `download_attachment` returns them after the source file is gone. They pickle and snapshot with the records.
- A refused upload raises `ShotgunError` with the site's reason. No row is made.
- A thumbnail reads `/images/status/transient/thumbnail_pending.png` until `sg.finalize_thumbnails()`. `share_thumbnail` from a transient source raises `ShotgunThumbnailNotReady`.

Not modelled: upload events beyond the Attachment create, and the HTTP server's upload routes.

## Event log

Answers in [api3-probe-2026-11-12](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3-probe-2026-11-12.md), sg-groundtruth findings 025 and 049.

Each create, update, delete, revive and schema field write adds `EventLogEntry` rows shaped as the
site writes them, queryable with `find`:

- A create logs `Shotgun_<Type>_New`, then one `_Change` per field it set, with `in_create: true`.
- An update logs one `_Change` per field whose value changed, `meta.old_value` and `meta.new_value`.
- A delete logs a `retirement_date` change and `_Retirement`, and drops the `entity` link from earlier rows for that entity. `meta.entity_id` keeps the trail. A revive logs the reverse and `_Revival`.
- Field create, rename and delete log `Shotgun_DisplayColumn_*` rows.

`sg.generate_event_log_entries = False` turns logging off, as the ApiUser flag does on a site
(default on here, off on a site). `sg.set_clock(fn)` makes timestamps deterministic.

Not modelled: server-set defaults logged on create, the internal `properties` row a rename also
writes, and event ids that a site reserves ahead and commits late (finding 025).

## Schema field writes

Answers in [api3-probe-2026-11-12](https://github.com/ksallee/sg-mockgun/blob/main/docs/api3-probe-2026-11-12.md).

`schema_field_create`, `schema_field_update` and `schema_field_delete` answer with
`shotgun_api3.Fault` and the site's words:

- The code is `sg_` + the lowercased display name, non-alphanumerics to `_`. `sg_foo` becomes `sg_sg_foo`.
- A display name already taken by a live field is suffixed: `_1`, `_2`. No error is raised.
- A deleted field's code stays taken. Creating it again, at any type, is refused. api3 has no revive; see [REST field revive](/docs/server/#rest-field-revive).
- `data_type` cannot be updated. Only `name`, `visible`, `description`, `summary_default`, `custom_metadata` and `unique` can.
- `query`, `summary`, `color` and `image` cannot be created. `calculated` fails as it does with no formula. `entity` and `multi_entity` need one `valid_types`. `checkbox` needs a boolean default.
- Schema writes are per instance.

Not recorded over api3: a `valid_types` with several types uses the REST wording, and a
`calculated` create with a formula is unmeasured. The code says so.

## Bundled schemas

`sg_mockgun.schemas.paths()` returns a schema pulled from a Flow PT 8.91 site: 95 entity types,
1471 fields. It has `visible`, `calculated`, `summary` and `jsonb` fields, which upstream's
test schema predates.

It lists only what any site ships. `sg_mockgun.clean.clean_schema` keeps a field when:

- the site cannot hide it (`visible.editable` false, sg-groundtruth finding 056),
- upstream's test schema has it, or
- its name has no `sg_` prefix, since custom fields get one (finding 019).

Custom entities the site enabled are dropped with their connection entities and links to them.
[`tools/pull_schema.py`](https://github.com/ksallee/sg-mockgun/blob/main/tools/pull_schema.py) pulls and cleans a schema from any site, read-only.

`schemas.paths("upstream_3_10_5")` is Autodesk's test schema from shotgun_api3 3.10.5, as published
in its repository under BSD-3: 77 entity types, 1035 fields, no `visible` key.
