# 035 color_timecode_jsonb_image

re-asks: field_types/color, field_types/timecode, field_types/jsonb, field_types/image
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/035_color_timecode_jsonb_image.py

**Q** What do color, timecode, jsonb and image fields take?

`<help>` stands for the text the site appends to every `Task.color` refusal: `Unsupported format for Task color field. The Task color can not be nil, the expected format is r,g,b where the values of r,g and b are in the range 0-255. The value of the color can also be set using the legacy color strings which are; Blue, Orange, Pink, Red, Green, Purple, Grey and Black. The value can also be set to the value pipeline_step to indicate that the Gantt bar should render using the color of the Task's Pipeline Step.`

## color, `Task.color`

| call | answer |
|---|---|
| a new row | reads `"pipeline_step"` |
| update `"255,0,0"` | stored `"255,0,0"` |
| update `"pipeline_step"` | stored `"pipeline_step"` |
| update `"red"` | stored `"253,1,0"` |
| update `"#ff0000"` | Fault `API update() CRUD ERROR #5: Update failed for [Task.color]:  (task.rb) Value is not a valid color token: [#ff0000]<help>` |
| update `""` | Fault `API update() CRUD ERROR #5: Update failed for [Task.color]:  (task.rb) The value is not a valid color expression: []<help>` |
| update `None` | Fault `API update() CRUD ERROR #5: Update failed for [Task.color]:  (task.rb) Value cannot be nil for Task.color.<help>` |
| create `"red"` | stored `"253,1,0"` |
| create `None` | Fault `API create() CRUD ERROR #6: Invalid field value, update failed [5 - Update failed for [Task.color]:  (task.rb) Value cannot be nil for Task.color.<help>]`; no row made |

Two spaces follow `[Task.color]:`. No space separates the reason from `<help>`.

## timecode, `Sequence.sg_timecode`

| call | answer |
|---|---|
| a new row | reads `None` |
| update `3600000`, `-1` | stored, `int` |
| update `"3600000"`, `"01:00:00:00"` | Fault `API update() Sequence.sg_timecode expected [Integer, NilClass] data type(s) but got String:\n"<as sent>"` |
| update `1.5` | Fault `... but got Float:\n1.5` |
| update `2**31` | Fault `API update() CRUD ERROR #5: Update failed for [Sequence.sg_timecode]: Invalid statement.` |
| update `None` | stored `None` |
| create `2**31` | Fault `API create() CRUD ERROR #6: Create failed for [Sequence]: PG::NumericValueOutOfRange: ERROR:  integer out of range\n`; no row made |

## jsonb, `Note.meta`

Notes were created with `project`, `subject` and `content` only, addressed to no one.

| call | answer |
|---|---|
| create `{"a": {"b": [1, 2]}, "n": None}` | stored and read back identical, `dict` |
| create `[{"x": 1}, 2]` | stored and read back identical, `list` |
| create `"x"` | stored, reads `"x"` (`str`) |
| update `{"a": 1}` | Fault `API update() Note.meta is editable on create only:\n{"field_name" => "meta", "value" => {"a" => 1}}` |
| update `None` | Fault `API update() Note.meta is editable on create only:\n{"field_name" => "meta", "value" => nil}` |

## image, `Version.image`

The api3 client handles `image` before the server sees it. `create` pops `image` from the body, creates the row, then uploads a non-empty value as a file. `update` does the same for a non-None value.

| call | answer |
|---|---|
| a new row | reads `None` |
| update `"https://example.com/a.png"` | `ShotgunError` `Path must be a valid file, got '<cwd>/https:/example.com/a.png'`; nothing sent |
| update `"/tmp/a.png"` (no such file) | `ShotgunError` `Path must be a valid file, got '/tmp/a.png'` |
| update `None` | sent; returns `{"type": "Version", "id": <id>, "image": None}` |
| create `"https://example.com/a.png"` | the same `ShotgunError`, raised after the row is made: one row exists |
| create `None` | `image` dropped from the body; the row is made |

**Same as REST:** color accepts r,g,b, `pipeline_step` and legacy names expanded; refuses None; a new Task reads `pipeline_step`. Timecode takes an integer, stores negatives, is signed 32-bit. `Note.meta` is create-only and stores dicts and lists unchanged. Image takes None.
**Differs from REST:** color and the 32-bit errors carry the `API <verb>() CRUD ERROR #5: ` or `#6: ` prefix, and color adds ` (task.rb) ` and `<help>`. `Note.meta` accepts a string on create over api3; REST refuses a String. The update Fault appends the Ruby hash of the request. An image string never reaches the server over api3; REST refuses it with a class error.
**Mock:** color: a new Task reads `None`, it must read `"pipeline_step"`. `None` is accepted on update and create; it must raise the nil Fault. Messages lack the prefix, ` (task.rb) ` and `<help>`; `""` gives `Value is not a valid color token: []`, it must give `The value is not a valid color expression: []`. Timecode: the bundled schema has no `Sequence.sg_timecode`; `writes.check_value` gives REST's class wording with a space before the value and no range prefix. jsonb: a string on create is refused with REST's class list; it must be stored. The create-only Fault lacks `:\n{"field_name" => ...}`. Image: a string is refused with REST's class error and no row; it must raise `ShotgunError` `Path must be a valid file, got '<abspath>'`, and on create after making the row. Every Fault is raised as `ShotgunError`; the site raises `Fault`, except the client-side image error.
