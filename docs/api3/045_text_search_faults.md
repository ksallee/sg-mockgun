# 045 text_search_faults

re-asks: finding 046, finding 053, finding 063
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project read
probe: probes/045_text_search_faults.py

**Q** What does `text_search()` raise for a short or empty text, an unknown type and bad filters?

`<request>` is the request the server echoes, as
`{"text" => "ab",\n "entity_types" =>\n  {"Shot" => {"logical_operator" => "and", "conditions" => []}},\n "project_ids" => [<id>],\n "max_results" => nil}`.

## text

| `text` | answer |
|---|---|
| `""` | Fault `API query_display_name_cache() query text too short! must be 3 or more characters :\n<request>` |
| `"ab"` | the same Fault |
| `123` (int) | the same Fault |
| `None` | Fault `API query_display_name_cache() 'text' missing:\n<request>` |
| `"   "` | `{"matches": [], "terms": []}` |
| `" ab "` | `{"matches": [], "terms": ["ab"]}` |
| `"ab cd"` | `{"matches": [], "terms": ["ab", "cd"]}` |
| `"abc d"` | `{"matches": [], "terms": ["abc", "d"]}` |

The 3-character check is on the text as sent, spaces included. A word shorter than 3 is accepted
when the whole text is 3 or more.

## entity_types

| `entity_types` | answer |
|---|---|
| `{}` | every entity type is searched: Shot, Asset, Version and Attachment rows came back |
| `{"NotAType": []}` | Fault `API query_display_name_cache() invalid entity type. Found: NotAType` |
| `{"Shot": [], "NotAType": []}` | the same Fault, no rows |
| `["Shot"]` | `ValueError: entity_types parameter must be a dictionary`, raised by the client |
| `{"Shot": {...}}` or `{"Shot": None}` | `ValueError: value of entity_types['Shot'] must be a list or tuple.`, raised by the client |

## Filters

| `entity_types["Shot"]` | answer |
|---|---|
| `[["sg_not_a_field", "is", "x"]]` | no Fault: the condition is ignored and the Shot rows matching the text come back |
| `[["code", "nope", "x"]]` | Fault `Uncaught exception! No condition node type matches <nope> for column Shot a.code` |
| `[["code"]]` | `IndexError: list index out of range`, raised by the client's filter translation |

## project_ids and limit

| argument | answer |
|---|---|
| `project_ids=[0]` | `{"matches": [], ...}` |
| `project_ids=[]` | every project is searched |
| `project_ids=<id>`, a bare int | Fault `Uncaught exception! undefined method 'collect' for an instance of Integer` |
| `limit=-1` | Fault `Uncaught exception! PG::InvalidRowCountInLimitClause: ERROR:  LIMIT must not be negative` + the SQL |
| `limit="ten"` | `{"matches": [], ...}` |

**Same as REST:** an unknown type fails the call, with no rows for the other types (finding 063).
Whitespace splits words.

**Differs from REST:**
- Over api3 the text must be 3 characters or more. Over REST `""` is 400 `text must be filled` and a
  one-letter text is legal (findings 046, 053).
- An unknown type is `invalid entity type. Found: NotAType` over api3. Over REST it is 400
  `entity_types must use valid entity names as keys` (finding 063).
- A filter field the type lacks is ignored over api3. Over REST it is 400
  `API _text_search() Shot.content doesn't exist.` (finding 063).
- An unknown operator is an uncaught exception over api3. Over REST the 400 lists the valid
  relations (finding 063).
- `entity_types={}` searches every type over api3. Finding 046 records only a missing `entity_types`, as 400.

**Mock:** no `text_search` method; `sg-mockgun serve` answers Fault `Error: API method
"query_display_name_cache" is not permitted.`. To change: raise the text-length Fault, the `'text'
missing` Fault and the `invalid entity type` Fault with these messages. Ignore a filter on a field
the type lacks. Treat `entity_types={}` as every type.
