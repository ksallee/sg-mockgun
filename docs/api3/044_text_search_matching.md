# 044 text_search_matching

re-asks: finding 053, finding 063
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project read
probe: probes/044_text_search_matching.py

**Q** What is a `text_search()` word matched against: case, prefix or substring, several words, links?

Over the sandbox's Shots and Assets, `limit=100`. Shot names follow `sqNNN_shNNN`, plus `shNNN` and
`demo_NN_<word>`. One Asset is `env_kitchen`.

| text | `terms` | matched |
|---|---|---|
| `sq010`, `SQ010`, `Sq010` | `["sq010"]` | the 8 `sq010_*` Shots, the same each time |
| `010` | `["010"]` | every name holding `010`, at the start, middle or end |
| `h01`, `q01`, `itche` | as sent | names holding it inside a word |
| `0_s`, `_sh0`, `sq010_sh020` | as sent | `_` is a character of the word, not a separator |
| `sq010 sh020`, `sh020 sq010`, `sq010  sh020` | `["sq010", "sh020"]` | `sq010_sh020` alone, whatever the word order |
| `  sq010  ` | `["sq010"]` | as `sq010` |
| `sq010 kitchen`, `sq010 zzznotaword` | both words | nothing: every word must match |
| `sq010 x` | `["sq010", "x"]` | nothing: a one-letter word still has to match |
| `KITCHEN` | `["kitchen"]` | `env_kitchen` |
| `demo 01` | `["demo", "01"]` | `demo_01_roto` |
| `demo-01` | `["demo-01"]` | nothing: `-` is not `_` |
| `sq0*`, `sq0%` | as sent | nothing: no wildcard |
| `flickers`, `banister`, `matte painting` (words only in `description`) | as sent | nothing |

A row matches on the name it links to:

| text | types | matched |
|---|---|---|
| `sbx_charA` | Version, Task | 1 Version whose name holds it, and 4 Tasks whose names do not, all with `links` `["Asset", "sbx_charA"]` |
| `charA` | Task | the same 4 Tasks |

**Same as REST:** every word is a case-insensitive substring of the name or of the linked row's
name. `_` is part of a word. `description` is not searched. Word order does not matter (finding 053).

**Differs from REST:** nothing in the matching. The minimum text length differs, see 045.

**Mock:** no `text_search` method; `sg-mockgun serve` answers Fault `Error: API method
"query_display_name_cache" is not permitted.`. To change: split `text` on whitespace, lowercase the
words for `terms`, and match a row when each word is a substring of its lowercased name or of its
linked row's lowercased name.
