`sg-mockgun serve` runs one mock instance behind the api3 JSON protocol. A real `shotgun_api3`
client, or code in another process or language, connects to it.

## Start it

```sh
sg-mockgun serve --host 0.0.0.0 --port 8080
sg-mockgun serve --seed tests/seed.json
```

`--schema` picks a bundled schema (default `fpt_8_91`). `--seed` loads a [seed file](/docs/pytest/#seed-files).

## Connect

```python
import shotgun_api3

sg = shotgun_api3.Shotgun("http://localhost:8080", script_name="any", api_key="any")
```

Any script name and key are accepted. The script name is the event log's user.

## api3 methods

- `info`, `read` with paging, `create`, `update`, `delete`, `revive`, `batch`, `summarize`.
- `query_display_name_cache` (`text_search`).
- The `schema_*` calls.
- `note_thread_read`, `activity_stream_read`, `followers`, `following`, `nav_expand`, `nav_search_string`, `nav_search_entity`, `preferences_read`, `work_schedule_read`, `user_subscriptions_read`, `export_page`.

A Fault comes back in the site's `exception` envelope. Any other method answers
`Error: API method "<name>" is not permitted.`, as a site does. Calls are serialised under one lock.
Upload routes are not served.

## REST field revive

api3 cannot revive a trashed field. The server answers the two REST routes a site uses for it:

- `POST /api/v1/auth/access_token`: `client_credentials` with the script name and key, `session_token` from `sg.get_session_token()`, or `refresh_token`. Form-encoded only.
- `POST /api/v1/schema/<Type>/fields/<field>` with `revive` true, in the body or the query. The field comes back at its original type.

Any other REST path answers 404. Answers follow sg-groundtruth finding 040. In process,
`sg.revive_field(entity_type, code)` does the same.

## Serve your own instance

State is in memory. `sg_mockgun.server.make_server(mock)` serves an instance seeded in code.
