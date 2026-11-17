# 058 share_thumbnail

re-asks: none
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, sandbox project written
probe: probes/058_share_thumbnail.py

**Q** What does `share_thumbnail` return between two Versions, and what does the target's `image` read after?

The method posts a form to `/upload/share_thumbnail`. A body starting `1:` gives the id, `2` raises `ShotgunThumbnailNotReady`, anything else `ShotgunError`. Setup: Versions A, B, C, D; `upload_thumbnail` on A returns `<n>` (api3 055).

| call | answer |
|---|---|
| `share_thumbnail([B], source_entity=A)`, A still transient | `ShotgunThumbnailNotReady` `Unable to share thumbnail: 2` + newline + `source_entity image is a transient thumbnail that cannot be shared. Try again later, when the final thumbnail is available` + newline |
| B's `image` after | `null` |
| the same call once A's `image` is final, 34.6 s and 44.1 s in two runs | `<n>`, the id `upload_thumbnail` returned |
| B's `image` after | a storage URL with the same path as A's, `<stem>_t.jpg`, and a different query |
| `share_thumbnail([C, D], thumbnail_path=png)` | `ShotgunThumbnailNotReady`, the same message |
| C's `image`, D's `image` after | `<site>/images/status/transient/thumbnail_pending.png`, `null` |
| `share_thumbnail([B], source_entity=D)`, D has no image | `None` |
| B's `image` after | `null` |
| `share_thumbnail([{"type": "Version", "id": 999999999}], source_entity=A)` | `ShotgunError` `Unable to share thumbnail: 0` + newline + `Couldn't find Version with 'id'=999999999 in 'entities' parameter` + newline |

With `thumbnail_path`, the client uploads the thumbnail to the first entity, then shares from it straight away. The source is still transient, so the share is refused and the first entity keeps the uploaded thumbnail. It cannot succeed on a site that transcodes.

Sharing from an entity with no image returns `None` and clears the target's `image`.

**Same as REST:** nothing to compare. The corpus has no thumbnail share.
**Differs from REST:** not measured over REST.
**Mock:** missing: `AttributeError`. Needed: copy the target's `image` from the source and return the id the source's `upload_thumbnail` returned. Raise `ShotgunThumbnailNotReady` while the source reads the transient placeholder. Return `None` and set the target's `image` to `None` for a source with no image. Raise the `ShotgunError` above for a missing target.
