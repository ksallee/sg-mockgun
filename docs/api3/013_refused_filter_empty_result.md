# 013 refused_filter_empty_result

re-asks: finding 017, finding 016
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/010_filter_links.py

**Q** Is a refused filter still refused when another filter already matches no row?

Each filter is ANDed with `["id", "is", 0]`, which matches no row.

| call | answer |
|---|---|
| `find("Version", [["id", "is", 0]])` | `[]` |
| `+ ["entity", "bogus_op", "x"]` | Fault `API read() Version.entity's 'entity' data type doesn't support 'bogus_op' 'relation':\n{"path" => "entity", "relation" => "bogus_op", "values" => ["x"]}\nValid relations:\n["is",\n "is_not",\n ...\n "not_in"]` |
| `+ ["zz_nope", "is", "x"]` | Fault `API read() Version.zz_nope doesn't exist:\n{"path" => "zz_nope", "relation" => "is", "values" => ["x"]}` |
| `+ ["entity", "name_is", None]` | Fault `API read() Version.entity expected [String] data type(s) but got NilClass:\nnil` |
| Note `+ ["note_links.Booking.code", "is", "x"]` | Fault `API read() Note.note_links.Booking.code doesn't exist:\n{"path" => "note_links.Booking.code", "relation" => "is", "values" => ["x"]}` |
| Note `+ ["note_links", "bogus_op", "x"]` | Fault `API read() Note.note_links's 'multi_entity' data type doesn't support 'bogus_op' 'relation':` + the condition + the nine relations |
| Note, `filter_operator="any"`, `id is 0` or `note_links.Booking.code is x` | the same `doesn't exist` Fault |

The site validates every condition before it reads a row.

**Same as REST:** the messages, with `read()` in place of `summarize()` for the Booking path (finding 016).
**Differs from REST:** nothing. REST did not measure a refused filter beside an empty match.
**Mock:** dev validates conditions before the scan. It raises for `bogus_op` on entity and multi_entity,
for `name_is None` and for the Booking path, in the AND and the `any` case. Two gaps remain. An unknown
plain field, `["zz_nope", "is", "x"]`, returns `[]` and must raise `Fault` `API read() Version.zz_nope doesn't
exist:` + the condition. Each refusal is `ShotgunError` with shorter text (no condition hash, `. Valid
relations:` on one line, `Note.note_links.Booking.code doesn't exist.` without `API read()`); it must be
`Fault` with the site text.
