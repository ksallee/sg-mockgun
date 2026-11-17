# 037 serializable_password_currency_footage

re-asks: field_types/serializable, field_types/password
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/037_serializable_password_currency_footage.py

**Q** Is a write to `Task.splits` stored? Does the site have a stock password, currency or footage field, and what does a write take?

## `Task.splits`

On a Task with `start_date` 2026-01-05 and `due_date` 2026-01-09:

| update value | answer | read |
|---|---|---|
| `[{"start": "2026-01-05", "end": "2026-01-06"}]` | returns `"splits": None` | `None` |
| `[]` | returns `None` | `None` |
| `[{"start": "2026-01-05", "end": "2026-01-06"}, {"start": "2026-01-08", "end": "2026-01-09"}]` | returns the list | the list, unchanged, `list` |
| `{"a": 1}` | Fault `API update() CRUD ERROR #5: Update failed for [Task.splits]: no implicit conversion of String into Integer` | unchanged |
| `"hello"` | Fault `API update() Task.splits expected [Hash,\n ActiveSupport::HashWithIndifferentAccess,\n ActionDispatch::Http::Parameters,\n ActionController::Parameters,\n Array,\n NilClass] data type(s) but got String:\n"hello"` | unchanged |
| `None` | returns `None` | `None` |
| create with the one-hash list | row made, returns `"splits": None` | `None` |

A new Task reads `None`. A list of one split is accepted and stores null. A list of two splits with `start` and `end` is stored.

## Password, currency, footage

A scan of every field of every entity type:

| type | fields |
|---|---|
| `password` | `HumanUser.password_proxy` (`editable: false`), `ClientUser.password_proxy` (`editable: true`) |
| `currency` | none |
| `footage` | none |

`HumanUser.password_proxy` reads `"*******"` on the 3 rows read. Both password fields are on user entities; a write is a user write, so none was sent. Currency and footage writes need a schema field create, which this probe may not do.

**Same as REST:** a one-hash list and `[]` are accepted and store null. A dict fails with `no implicit conversion of String into Integer`. A string is a class error. The password mask is `"*******"`.
**Differs from REST:** a two-split list with `start` and `end` keys is stored over api3. The REST card sent other keys and saw a two-hash list fail with `undefined method '<' for nil`; it never sent `start` and `end`, so the cause can be the keys and not the client. api3 prefixes the dict error with `API update() CRUD ERROR #5: `. The class list here has `ActionController::Parameters`.
**Mock:** refuses every list with `Task.splits is of type <class 'list'>, but data serializable is not of type <class 'dict'>` (upstream mockgun), and stores `{"a": 1}`. It must accept a list: a list of fewer than two splits stores None, two `start`/`end` splits are stored, a dict raises the `no implicit conversion` Fault, and a string raises the class Fault above.

Skipped: writes to `ClientUser.password_proxy` (a user write). Currency and footage writes (no stock field; needs a schema field create).
