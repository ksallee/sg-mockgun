# sg-mockgun

Mockgun, the in-memory Flow Production Tracking mock that ships inside
[shotgun_api3](https://github.com/shotgunsoftware/python-api), taken out on its own and extended
with behaviour recorded by [sg-groundtruth](https://github.com/ksallee/sg-groundtruth).

Status: `0.1.0`. Mockgun as vendored from shotgun_api3 3.10.5, upstream tests passing, plus a clean
current schema, schema field writes, an event log, and an HTTP server a real client connects to.

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

## Bundled schema

`sg_mockgun.schemas.paths()` returns a schema pulled from a Flow PT 8.91 site on 2026-11-12: 95
entity types, 1471 fields. Upstream's test schema predates `visible`, `calculated`, `summary` and
`jsonb` fields; this one has them.

It holds only what any site ships. `sg_mockgun.clean.clean_schema` keeps a field when the site cannot
hide it (`visible.editable` false, sg-groundtruth finding 056), when upstream's test schema has it, or
when its name carries no `sg_` prefix, since every custom field gets one (finding 019). Custom
entities the site enabled are dropped with their connection entities and every link to them.

`tools/pull_schema.py` pulls and cleans a schema from any site, read-only.

## Use

    pip install sg-mockgun

    from sg_mockgun import Shotgun, schemas
    Shotgun.set_schema_paths(*schemas.paths())
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")

## Serve

    sg-mockgun serve --host 0.0.0.0 --port 8080

    import shotgun_api3
    sg = shotgun_api3.Shotgun("http://localhost:8080", script_name="any", api_key="any")

One mockgun instance behind the api3 JSON protocol: `info`, `read` with paging, `create`, `update`,
`delete`, `revive`, `batch` and the `schema_*` calls. Any script name and key are accepted, and the
script name is the event log's user. Faults come back in the site's `exception` envelope; any other
method answers `Error: API method "<name>" is not permitted.`, as a site does. Calls are serialised
under one lock. State lives in memory; `sg_mockgun.server.make_server(mock)` serves an instance you
have seeded yourself.

## Develop

    uv sync
    uv run pytest

## License

BSD-3-Clause, as upstream. `src/sg_mockgun/` started as `shotgun_api3/lib/mockgun` from
shotgun_api3 3.10.5, Copyright (c) 2009-2011 Shotgun Software Inc. `tests/test_upstream_mockgun.py`
and `tests/fixtures/upstream/` are upstream's tests and test schema, with import paths changed.
