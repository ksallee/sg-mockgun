# sg-mockgun

Mockgun, the in-memory Flow Production Tracking mock that ships inside
[shotgun_api3](https://github.com/shotgunsoftware/python-api), taken out on its own and extended
with behaviour recorded by [sg-groundtruth](https://github.com/ksallee/sg-groundtruth).

Status: `0.1.0`. Mockgun as vendored from shotgun_api3 3.10.5, upstream tests passing. Nothing
added yet.

## Why

Upstream mockgun covers find, create, update, delete, revive and batch against a pickled schema. It
raises `NotImplementedError` on `schema_field_create`, `schema_field_update` and
`schema_field_delete`, and has no event log. A live site refuses a data type change, keeps a
deleted field's name taken and records every write in the event log. Code tested on mockgun never
meets those answers.

## Planned

Each behaviour comes from a corpus entry, never a guess.

- `schema_field_create`, `schema_field_update`, `schema_field_delete`, `schema_field_revive`, with
  the refusals the site answers with.
- `EventLogEntry` records for every write.
- A clean current schema: a site's stock fields, decided by `visible.editable` (sg-groundtruth
  finding 056), plus every field upstream's test schema carries.

## Use

    pip install sg-mockgun

    from sg_mockgun import Shotgun
    Shotgun.set_schema_paths("schema.pickle", "schema_entity.pickle")
    sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")

## Develop

    uv sync
    uv run pytest

## License

BSD-3-Clause, as upstream. `src/sg_mockgun/` started as `shotgun_api3/lib/mockgun` from
shotgun_api3 3.10.5, Copyright (c) 2009-2011 Shotgun Software Inc. `tests/test_upstream_mockgun.py`
and `tests/fixtures/upstream/` are upstream's tests and test schema, with import paths changed.
