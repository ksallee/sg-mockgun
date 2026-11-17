# 012 dotted_through_links

re-asks: field_types/entity, finding 016
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/010_filter_links.py

**Q** Does a dotted filter through a link to another type match rows whose link is unset or of the other type?

Versions as in 010: `v_shot`, `v_asset`, `v_none`. Notes as in 011: `n_shot`, `n_asset`, `n_none`. The
Shot is in a Sequence.

| call | answer |
|---|---|
| `["entity.Shot.code", "is", None]` | `v_asset v_none` |
| `["entity.Shot.code", "is_not", None]` | `v_shot` |
| `["entity.Shot.code", "is_not", "x"]` | `v_asset v_none v_shot` |
| `["entity.Shot.code", "not_in", ["x"]]` | `v_asset v_none v_shot` |
| `["entity.Shot.code", "not_contains", "x"]` | `v_asset v_none v_shot` |
| `["entity.Asset.code", "is", None]` | `v_none v_shot` |
| `["note_links.Shot.code", "is", None]` | `n_asset n_none` |
| `["note_links.Shot.code", "is_not", None]` | `n_shot` |
| `["note_links.Shot.code", "is_not", "x"]` | `n_asset n_none n_shot` |
| `["note_links.Shot.sg_sequence.Sequence.code", "is_not", None]` | `n_shot` |
| `["note_links.Shot.sg_sequence.Sequence.code", "is", None]` | `n_asset n_none` |

A dotted path reads null on a row that links another type or nothing. `is None` and every negating operator
match that row. Through multi_entity the rule is the same.

**Same as REST:** dotted filters through entity and multi_entity are evaluated, two hops included.
`entity.Shot.code` reads null on a Version that links an Asset.
**Differs from REST:** nothing. REST measured `note_links.Shot.sg_sequence.Sequence.code is_not null`
only on a project where every Note links a Shot.
**Mock:** the entity rows match the site. Through `note_links` the mock does not count a Note with no Shot
link as null: `note_links.Shot.code is None` returns `[]`, `is_not "x"` returns `n_shot`, and
`note_links.Shot.sg_sequence.Sequence.code is None` returns `[]`. Each must match `n_asset` and `n_none`
as above.
