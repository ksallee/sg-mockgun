# sg-mockgun

Mockgun, the in-memory Flow Production Tracking mock that ships inside
[shotgun_api3](https://github.com/shotgunsoftware/python-api), taken out on its own and extended
with behaviour recorded by [sg-groundtruth](https://github.com/ksallee/sg-groundtruth).

Status: `0.1.0`. Mockgun as vendored from shotgun_api3 3.10.5, upstream tests passing, plus a clean
current schema.

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

## Develop

    uv sync
    uv run pytest

## License

BSD-3-Clause, as upstream. `src/sg_mockgun/` started as `shotgun_api3/lib/mockgun` from
shotgun_api3 3.10.5, Copyright (c) 2009-2011 Shotgun Software Inc. `tests/test_upstream_mockgun.py`
and `tests/fixtures/upstream/` are upstream's tests and test schema, with import paths changed.
