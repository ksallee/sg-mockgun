# 038 create_return_and_defaults

re-asks: finding 024, field_types/number, field_types/percent, field_types/date, field_types/timecode, field_types/password
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/038_create_return_and_defaults.py

**Q** What does `create` return with no `return_fields`? Who are `created_by` and `updated_by` for a script? Is `created_at` accepted on create and refused on update? What do unset fields read on a new row?

## Create return

| call | answer |
|---|---|
| `create("Version", {"project": <project>, "code": c})` | `{"type": "Version", "id": <id>, "code": c, "project": {"type": "Project", "id": <project>, "name": <sandbox>}}` |
| same, `return_fields=["created_at", "updated_at", "created_by", "updated_by", "cached_display_name"]` | the four keys above plus the five asked for |

With no `return_fields` the return has the fields sent, `type` and `id`. An entity link gains `name`. `created_at`, `updated_at`, `created_by`, `updated_by` and `cached_display_name` are absent.

## Server-set fields

| field | value |
|---|---|
| `created_at`, `updated_at` | `datetime` with `tzinfo` `shotgun_api3.lib.sgtimezone.LocalTimezone`; equal on a new row |
| `created_by`, `updated_by` | `{"type": "ApiUser", "id": <id>, "name": <script name>}`; equal, the script's own ApiUser |
| `cached_display_name` | the `code` |

## `created_at` and `updated_at`

| call | answer |
|---|---|
| create with `created_at: datetime(2020, 1, 2, 3, 4, 5)` (naive) | accepted; returns and reads `2020-01-02 03:04:05` local time |
| `update(..., {"created_at": datetime(...)})` | Fault `API update() Version.created_at is editable on create only:\n{"field_name" => "created_at", "value" => "2020-01-02T<hh>:04:05Z"}` |
| `update(..., {"updated_at": datetime(...)})` | Fault `API update() Version.updated_at is editable on create only:\n{"field_name" => "updated_at", "value" => "..."}` |

The client sends a naive datetime as local time converted to UTC. The Fault prints the UTC value.

## Defaults on a new row

| field | type | reads |
|---|---|---|
| `Version.frame_count`, `Shot.sg_cut_order` | number | `None` |
| `Version.sg_movie_aspect_ratio` | float | `None` |
| `Shot.sg___complete` | percent | `None` |
| `Shot.sg_turnover_date`, `Task.start_date`, `Task.due_date` | date | `None` |
| `Task.duration` | duration | `None` |
| `Sequence.sg_timecode` | timecode | `None` |
| `Version.flagged` | checkbox | `False` |
| `Task.color` | color | `"pipeline_step"` |

`password` is on `HumanUser` and `ClientUser` only. A new row needs a user create, which a probe may not do. Existing rows read `"*******"` (037).

**Same as REST:** `created_at` and `updated_at` are editable on create only, with the same sentence. Unset number, float, percent, date, duration and timecode read null; checkbox reads false; Task color reads `pipeline_step`.
**Differs from REST:** a REST create returns the fields sent plus the server-set ones (`created_at`, `updated_at`, `cached_display_name`) and every relationship. An api3 create returns only the fields sent, `type` and `id`, unless `return_fields` asks. The update Fault appends the Ruby hash of the request.
**Mock:** the create return matches. With `return_fields` it returns only `type`, `id` and the fields asked; it must add the fields sent. `created_at`, `updated_at`, `created_by`, `updated_by` and `cached_display_name` read `None`; they must be set, `created_by` and `updated_by` to an ApiUser for the script. An update of `created_at` or `updated_at` is accepted and returns a string; it must raise the Fault. `Task.color` reads `None`; it must read `"pipeline_step"`. The bundled schema has no `sg___complete`, `sg_turnover_date`, `sg_cut_order` or `sg_timecode`; other defaults match.
