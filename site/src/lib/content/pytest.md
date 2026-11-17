Installing sg-mockgun registers a pytest plugin. No configuration is needed.

## The `sg` fixture

`sg` is a fresh instance per test on the bundled schema. Its clock starts at 2026-01-01 00:00 UTC
and advances one second per write.

```python
def test_publish(sg):
    sg.load("tests/seed.json")
    state = sg.snapshot()
    sg.create("Version", {"code": "v001", "entity": {"type": "Shot", "id": 1001}})
    sg.restore(state)
```

## Seed files

A seed file lists records per entity type, each with an explicit `id`:

```json
{
  "Project": [{"id": 70, "name": "Demo"}],
  "Shot": [{"id": 1001, "code": "sh010", "project": {"type": "Project", "id": 70}}]
}
```

- A link is `{"type", "id"}` and points at a record in the seed or already loaded.
- A `date_time` value is an ISO 8601 string.
- Seeding writes no event log rows.
- A refused seed adds no records.
- The next `create` takes the highest seeded id plus one.

## Snapshot and restore

`sg.snapshot()` copies the records and the schema. `sg.restore(state)` puts them back, as often as
needed.

## Without the fixture

`sg_mockgun.pytest_plugin.make_sg()` returns the same instance the fixture returns. Use it in a
fixture with a wider scope.
