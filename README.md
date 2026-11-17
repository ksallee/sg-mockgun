# sg-mockgun

Mockgun, the in-memory Flow Production Tracking mock that ships inside
[shotgun_api3](https://github.com/shotgunsoftware/python-api), taken out on its own and extended
with behaviour recorded by [sg-groundtruth](https://github.com/ksallee/sg-groundtruth).

Status: `0.1.0`. Mockgun as vendored from shotgun_api3 3.10.5, upstream tests passing, plus a clean
current schema, schema field writes, an event log, and an HTTP server a real client connects to.

[Coverage](docs/coverage.md): each api3 call the conformance suite checks, with its result on the mock and on a live site.

## Why

Upstream mockgun covers find, create, update, delete, revive and batch against a pickled schema. It
raises `NotImplementedError` on `schema_field_create`, `schema_field_update` and
`schema_field_delete`, and has no event log. A live site refuses a data type change, keeps a
deleted field's name taken and records every write in the event log. Code tested on mockgun never
meets those answers.

## Event log

Every create, update, delete, revive and schema field write adds `EventLogEntry` rows shaped as the
site writes them (`docs/api3-probe-2026-11-12.md`, findings 025 and 049), queryable with `find`:

- A create logs `Shotgun_<Type>_New`, then one `_Change` per field it set, with `in_create: true`.
- An update logs one `_Change` per field whose value changed, `meta.old_value` and `meta.new_value`.
- A delete logs a `retirement_date` change and `_Retirement`, and drops the `entity` link from every
  earlier row for that entity; `meta.entity_id` keeps the trail. A revive logs the reverse and `_Revival`.
- Field create, rename and delete log `Shotgun_DisplayColumn_*` rows.

`sg.generate_event_log_entries = False` turns logging off, as the ApiUser flag does on a site (default
on here, off on a site). `sg.set_clock(fn)` makes timestamps deterministic.

Not modelled: server-set defaults logged on create, the internal `properties` row a rename also
writes, and event ids that a site reserves ahead and commits late (finding 025).

## Task Templates and scheduling

A create or a changed `task_template` applies the template from the TaskTemplate and its template
Tasks in the mock (`docs/api3/070` to `074`). Seed them with `create` or `load`.

- Missing template Tasks are created with `template_task` set. Linked Tasks are re-synced. Edges are
  rewired. No Task is removed.
- `duration` counts working days at 480 minutes. Downstream Tasks reschedule on an edge or an
  upstream date write. A `start_date` write pins a dependent. `dependency_violation` is read only.
- Deleting a Task retires its TaskDependency rows. Reviving it restores them.

`sg.set_work_week([True] * 5 + [False] * 2)` sets the working days, Monday first (default Mon to Fri).

Not modelled: event rows for rescheduled dates and re-synced fields, the dependency loop, duplicate
and type refusals.

## Schema field writes

`schema_field_create`, `schema_field_update` and `schema_field_delete` answer as a Flow PT 8.91 site
answered over api3 (`docs/api3-probe-2026-11-12.md`), with `shotgun_api3.Fault` and the site's words:

- The code is `sg_` + the lowercased display name, non-alphanumerics to `_`. `sg_foo` becomes `sg_sg_foo`.
- A display name already taken by a live field is silently suffixed: `_1`, `_2`.
- A deleted field's code stays taken. Creating it again, at any type, is refused, and api3 has no revive.
- `data_type` cannot be updated. Only `name`, `visible`, `description`, `summary_default`,
  `custom_metadata` and `unique` can.
- `query`, `summary`, `color` and `image` cannot be created. `calculated` fails as it does with no
  formula. `entity` and `multi_entity` need one `valid_types`; `checkbox` needs a boolean default.
- Schema writes are per instance.

Two answers are not recorded over api3 and say so in the code: a `valid_types` with several types
uses the REST wording, and a `calculated` create carrying a formula is unmeasured.

## Media

`upload`, `upload_thumbnail`, `upload_filmstrip_thumbnail`, `share_thumbnail`, `download_attachment`
and `get_attachment_download_url` answer as api3 answers 053 to 058 in `docs/api3/`:

- `upload` creates an Attachment, sets a File/Link field to its `this_file`, and returns its id.
  `tag_list` creates missing Tags.
- The file's bytes are kept in memory, per instance. `download_attachment` returns them after the
  source file is gone. They pickle and snapshot with the records.
- A refused upload raises `ShotgunError` with the site's reason. No row is made.
- A thumbnail reads `/images/status/transient/thumbnail_pending.png` until `sg.finalize_thumbnails()`.
  `share_thumbnail` from a transient source raises `ShotgunThumbnailNotReady`.
- Upload events beyond the Attachment create, and the HTTP server's upload routes, are not modelled.

## Attention, navigation and site reads

`note_thread_read`, `activity_stream_read`, `followers`, `following`, `nav_expand`,
`nav_search_string`, `nav_search_entity`, `preferences_read`, `work_schedule_read`,
`user_subscriptions_read` and `export_page` answer as recorded in `docs/api3/047` to `052`, in process
and over `sg-mockgun serve`. Activity stream rows are the `create` rows of the event log. Site data
the mock cannot know has a default and a setter:

- `sg.set_following(user, entities)`: what `user` follows. Default: nothing.
- `sg.set_preferences(values)`: preferences. Default: 17 keys of the recorded types.
- `sg.set_work_schedule(week=None, exceptions=None)`: seven booleans, Monday first, and rules per
  `YYYY-MM-DD`. Default: Monday to Friday, `STUDIO_WORK_WEEK`.
- `sg.set_user_subscriptions(subscriptions)`: keyed by HumanUser id as a string. Default: `{}`.

`export_page` refuses every page, as a site with no exportable page does.

## Bundled schema

`sg_mockgun.schemas.paths()` returns a schema pulled from a Flow PT 8.91 site on 2026-11-12: 95
entity types, 1471 fields. Upstream's test schema predates `visible`, `calculated`, `summary` and
`jsonb` fields; this one has them.

It holds only what any site ships. `sg_mockgun.clean.clean_schema` keeps a field when the site cannot
hide it (`visible.editable` false, sg-groundtruth finding 056), when upstream's test schema has it, or
when its name carries no `sg_` prefix, since every custom field gets one (finding 019). Custom
entities the site enabled are dropped with their connection entities and every link to them.

`tools/pull_schema.py` pulls and cleans a schema from any site, read-only.

`schemas.paths("upstream_3_10_5")` is Autodesk's own test schema from shotgun_api3 3.10.5, as
published in its repository under BSD-3. Older (77 entity types, 1035 fields, no `visible` key), but
it ships with the client's own licence and covers the common production entities.

## Use

    pip install sg-mockgun

    from sg_mockgun import Shotgun, schemas
    Shotgun.set_schema_paths(*schemas.paths())
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")

## Testing with pytest

Installing sg-mockgun registers a pytest plugin. The `sg` fixture is a fresh instance per test on
the bundled schema, with a clock that starts at 2026-01-01 00:00 UTC and advances one second per
write.

    def test_publish(sg):
        sg.load("tests/seed.json")
        state = sg.snapshot()
        sg.create("Version", {"code": "v001", "entity": {"type": "Shot", "id": 1001}})
        sg.restore(state)

A seed file lists records per entity type, each with an explicit `id`:

    {
      "Project": [{"id": 70, "name": "Demo"}],
      "Shot": [{"id": 1001, "code": "sh010", "project": {"type": "Project", "id": 70}}]
    }

- A link is `{"type", "id"}` and points at a record in the seed or already loaded.
- A `date_time` value is an ISO 8601 string.
- Seeding writes no event log rows.
- A refused seed adds no records.
- The next `create` takes the highest seeded id plus one.

`sg.snapshot()` copies the records and the schema. `sg.restore(state)` puts them back, as often as
needed.

## Migrate from shotgun_api3's mockgun

Replace the import:

    # from shotgun_api3.lib import mockgun
    import sg_mockgun as mockgun

The package exports `Shotgun`, `generate_schema`, `MockgunError` and the submodules `mockgun`,
`schema` and `errors`, as upstream does. The constructor signature is upstream's.

Differences from upstream:

- `Shotgun` and `MockgunError` are new classes. A `mock.patch` target or an `except` clause naming `shotgun_api3.lib.mockgun` misses them.
- `set_schema_paths` is per class. Calling it on upstream's `Shotgun` does not configure sg-mockgun's.
- The event log is on by default. Set `sg.generate_event_log_entries = False` to turn it off.
- `schema_field_create`, `schema_field_update` and `schema_field_delete` write to the schema instead of raising `NotImplementedError`.
- Each instance deep-copies the schema. A schema write on one instance does not reach another.
- `from sg_mockgun import mockgun` returns the submodule, which has no `generate_schema`.

## Serve

    sg-mockgun serve --host 0.0.0.0 --port 8080
    sg-mockgun serve --seed tests/seed.json

    import shotgun_api3
    sg = shotgun_api3.Shotgun("http://localhost:8080", script_name="any", api_key="any")

One mockgun instance behind the api3 JSON protocol: `info`, `read` with paging, `create`, `update`,
`delete`, `revive`, `batch` and the `schema_*` calls. Any script name and key are accepted, and the
script name is the event log's user. Faults come back in the site's `exception` envelope; any other
method answers `Error: API method "<name>" is not permitted.`, as a site does. Calls are serialised
under one lock.

Next to api3 it serves the two REST routes a site needs to revive a trashed field, which api3
cannot do: `POST /api/v1/auth/access_token` (`client_credentials` with the script name and key,
`session_token` from `sg.get_session_token()`, `refresh_token`; form-encoded only) and
`POST /api/v1/schema/<Type>/fields/<field>` with `revive` true, in the body or the query. The field
comes back at its original type. Answers from sg-groundtruth finding 040 and its endpoint cards;
any other REST path is a 404. In-process, `sg.revive_field(entity_type, code)` does the same.

State lives in memory; `sg_mockgun.server.make_server(mock)` serves an instance you
have seeded yourself.

## Develop

    uv sync
    uv run pytest

## License

BSD-3-Clause, as upstream. `src/sg_mockgun/` started as `shotgun_api3/lib/mockgun` from
shotgun_api3 3.10.5, Copyright (c) 2009-2011 Shotgun Software Inc. `tests/test_upstream_mockgun.py`
and `tests/fixtures/upstream/` are upstream's tests and test schema, with import paths changed.
