# 004 case

re-asks: field_types/text, field_types/list
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/004_case.py

**Q** Do text `is` and list `is` match a value whose case was changed?

`<code>` is a Shot code read first, lower case.

| call | rows |
|---|---|
| `Shot code is <code>` | 1 |
| `Shot code is <code>.upper()` | 1 |
| `Shot code is <code>.swapcase()` | 1 |
| `Shot code in [<code>.upper()]` | 1 |
| `Shot code starts_with <first 4>.upper()` | 300, as lower case |
| `Note sg_note_type is "Internal"` | 4076 |
| `Note sg_note_type is "INTERNAL"`, `"internal"` | 4076 |
| `Note sg_note_type in ["INTERNAL"]` | 4076 |
| `Version sg_status_list is "rev"` | 367 |
| `Version sg_status_list is "REV"` | 367 |

Text, list and status_list match case-insensitively for `is`, `in` and `starts_with`.

**Same as REST:** text and list filters are case-insensitive.
**Differs from REST:** nothing.
**Mock:** case-insensitive for text, list and status_list. No change.
