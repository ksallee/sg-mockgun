## Install

```sh
pip install sg-mockgun
```

Requires Python 3.9 or later. `shotgun-api3` 3.10.5 or later is the only dependency.

## Start a mock site

```python
from sg_mockgun import Shotgun, schemas

Shotgun.set_schema_paths(*schemas.paths())
sg = Shotgun("https://mock.example.com", script_name="x", api_key="y")
```

`schemas.paths()` returns the bundled Flow PT 8.91 schema. `schemas.paths("upstream_3_10_5")`
returns the test schema from shotgun_api3 3.10.5. See [What is modelled](/docs/modelled/#bundled-schemas).

## Migrate from shotgun_api3's mockgun

Replace the import:

```python
# from shotgun_api3.lib import mockgun
import sg_mockgun as mockgun
```

The package exports `Shotgun`, `generate_schema`, `MockgunError` and the submodules `mockgun`,
`schema` and `errors`, as upstream does. The constructor signature is upstream's.

## Differences from upstream

- `Shotgun` and `MockgunError` are new classes. A `mock.patch` target or an `except` clause naming `shotgun_api3.lib.mockgun` misses them.
- `set_schema_paths` is per class. Calling it on upstream's `Shotgun` does not configure sg-mockgun's.
- The event log is on by default. Set `sg.generate_event_log_entries = False` to turn it off.
- `schema_field_create`, `schema_field_update` and `schema_field_delete` write to the schema instead of raising `NotImplementedError`.
- Each instance deep-copies the schema. A schema write on one instance does not reach another.
- `from sg_mockgun import mockgun` returns the submodule, which has no `generate_schema`.
- A refused filter or write raises `shotgun_api3.Fault` with the site's wording where an api3 answer is recorded. Upstream raised `ShotgunError` or accepted the value.
- A create without `project` on a Shot, Version, Asset, Sequence, Task, Playlist, PublishedFile, Note or Delivery is refused. Set `sg.require_project = False` to skip the check.

## Site values

- `sg.set_info(**values)` changes keys of the payload `info()`, `server_info` and `server_caps` read.
- `server_info` and `server_caps` take an assigned value, as upstream mockgun's callers assign them. `server_caps` follows an assigned `server_info`.
- A naive `datetime` in a write or a filter is local time, as the client sends it.
- `sg.set_clock(fn)` makes timestamps deterministic.
- A mock instance pickles.
