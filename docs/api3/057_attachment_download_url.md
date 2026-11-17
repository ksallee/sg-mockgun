# 057 attachment_download_url

re-asks: none, client source
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/057_attachment_download_url.py

**Q** What does `get_attachment_download_url` return for each shape?

The method sends no request. It builds the URL from `config.server`.

| argument | answer |
|---|---|
| `42` | `https://<site>/file_serve/attachment/42` |
| `{"type": "Attachment", "id": 42}` | the same |
| a dict with `url` | that `url`, unchanged |
| `{"link_type": "local", "url": "file:///tmp/x.txt", ...}` | `file:///tmp/x.txt` |
| `{"type": "Version", "id": 42}` | `ValueError` `Missing 'url' key in Attachment dict` |
| `{"id": 42}` | the same |
| `None` | `None` |
| `0` | `UnboundLocalError` `cannot access local variable 'url' where it is not associated with a value` |
| `"42"` | `TypeError` `Unable to determine download url. Expected dict, int, or NoneType. Instead got <class 'str'>` |

A dict with `url` wins over `type` and `id`. Id `0` is falsy, so no URL is built and the local is unset.

**Same as REST:** nothing to compare. The method is client code.
**Differs from REST:** REST has no such method. Its download is `?alt=original` on the field path (finding 048).
**Mock:** missing: `AttributeError`. Needed: the method copied from the client, with `config.server` from the mock's base URL. The `UnboundLocalError` on `0` is the client's and stays.
