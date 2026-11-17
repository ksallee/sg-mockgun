# 030 text_empty_and_spaces

re-asks: field_types/text
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/030_text_empty_and_spaces.py

**Q** What does a text field store and return for `""` and `"  x  "`?

On `Shot.description`:

| call | answer |
|---|---|
| `create("Shot", {..., "description": ""})` | returns `"description": None`; reads `None` |
| `create("Shot", {..., "description": "  x  "})` | returns `"description": "x"`; reads `"x"` |
| `update(..., {"description": "  x  "})` | `{"type": "Shot", "id": <id>, "description": "x"}`; reads `"x"` |
| `update(..., {"description": "   "})` | `{..., "description": None}`; reads `None` |
| `update(..., {"description": ""})` over `"y"` | `{..., "description": None}`; reads `None` |
| `find` with `["description", "is", ""]` | 1 row: the null one |
| `find` with `["description", "is", None]` | 1 row: the same one |

`update` returns a dict: `type`, `id` and the fields sent, with the stored value.

**Same as REST:** `""` stores null. Both ends are stripped. Whitespace only stores null. `is ""` and `is None` match the same rows.
**Differs from REST:** nothing on the value. The update return is the fields sent, not the whole record (finding 024).
**Mock:** stores and returns the same values. Two differences. `update` returns a list holding one dict; it must return the dict. `["description", "is", ""]` matches 0 rows; it must match the null rows.
