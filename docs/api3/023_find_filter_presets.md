# 023 find_filter_presets

re-asks: none (no corpus entry)
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read-only
probe: probes/023_find_filter_presets.py

**Q** What does `additional_filter_presets` with `LATEST` return, and what is the Fault for a bad preset?

## Which rows LATEST keeps

| type | `latest_by` | rule | rows |
|---|---|---|---|
| PublishedFile | `ENTITIES_CREATED_AT` | newest `created_at` per (`entity`, `task`, `published_file_type`, `name`). A row with any of the four null is dropped. | 69 of 235, matched the rule row for row |
| Version | `ENTITIES_CREATED_AT` | newest `created_at` per `entity`. A row with null `entity` is dropped. | 146 of 1356 |
| Version | `BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT` | per `entity`, highest `sg_task.Task.step` `list_order`, then newest `created_at`. Null `entity` is dropped. | 146 of 1356 |

- On Version, both rules matched every group but one. In that group two rows had the same `created_at`. The server kept the lower id.
- LATEST combines with filters and `limit`.

## Faults

| call | answer |
|---|---|
| PublishedFile, `latest_by` `BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT` | Fault `API read() CRUD ERROR #10: Read failed for entity type [PublishedFile]` |
| PublishedFile or Version, `latest_by` `ENTITY_CREATED_AT`, `CREATED_AT` or `NOPE` | the same CRUD ERROR #10, with the type |
| `{"preset_name": "LATEST"}`, no `latest_by` | the same CRUD ERROR #10 |
| `{"preset_name": "NOPE"}` | Fault `API read() Invalid additional filter preset provided: ` + newline + the request |
| Shot, LATEST `ENTITIES_CREATED_AT` | Fault `API read() Invalid additional filter preset provided: ` + the request |
| `["LATEST"]` | Fault `API read() invalid additional filter preset format. It must be a hash:` + the request |

The request in a Fault is printed as a Ruby hash, with `"additional_filter_presets" => [...]`.

The question's preset, `BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT` on PublishedFile, is refused. That value is for Version only.

**Same as REST:** not measured over REST.
**Differs from REST:** not measured over REST.
**Mock:** raises `ShotgunError: additional_filter_presets is not modelled by sg-mockgun (sg-mockgun#39).` It must apply the three rules above, and raise the Faults above for other values and types.
