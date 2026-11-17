# 025 find_order_none

re-asks: finding 026
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/025_find_order_none.py

**Q** Where does None sort, ascending and descending?

Four Versions in the sandbox, created in this order:

| row | `description` | `frame_count` | `sg_status_list` | `entity` |
|---|---|---|---|---|
| b | `"b"` | 5 | `rev` | a Shot |
| none | None | None | None | None |
| a | `"a"` | 1 | `na` | None |
| empty | `""`, read back as None | 0 | `apr` | None |

`description: ""` is stored as None.

| `order` | asc | desc |
|---|---|---|
| `description` (text) | a, b, none, empty | b, a, none, empty |
| `frame_count` (number) | empty, a, b, none | b, a, empty, none |
| `sg_status_list` (status_list) | a, b, empty, none | empty, b, a, none |
| `entity` (entity) | b, none, a, empty | b, none, a, empty |
| `entity.Shot.code` (dotted) | b, none, a, empty | b, none, a, empty |

- None sorts last in both directions.
- Rows tied on None keep id ascending in both directions.
- 0 is a value: it sorts before 1 ascending.

**Same as REST:** id ascending is the tiebreak (finding 026).
**Differs from REST:** REST has no entry on None in a sort.
**Mock:**
- text, number and status_list put None first ascending, and keep it last descending only by reversal. It must put None last in both directions, ties by id ascending.
- `entity` raises `TypeError` comparing None and dict.
- A text field written `""` reads back `None`, which matches.
