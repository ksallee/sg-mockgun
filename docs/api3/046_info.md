# 046 info

re-asks: finding 051, finding 027
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/046_info.py

**Q** What does `info()` return, and what do `connect()`, `server_info` and `server_caps` do with it?

The client sends the RPC method `info` with no params and no auth (`include_auth_params=False`), and
returns the `results` dict unchanged.

## The payload

Strings are replaced by `<str>`. Booleans and numbers are as printed.

```
{"analytics_site_id": <str>,
 "analytics_site_name": <str>,
 "api_max_entities_per_page": 5000,
 "authentication_app_session_launcher_enabled": True,
 "full_version": [8, 91, 0, 10264],
 "s3_direct_uploads_enabled": True,
 "s3_enabled_upload_types": {"*": ["*"]},
 "s3_uploads_enabled": True,
 "shotgunlocalhost_browser_integration_enabled": True,
 "unified_login_flow_enabled": True,
 "user_authentication_method": "oxygen",
 "version": [8, 91, 0]}
```

## What the client does with it

| call | answer |
|---|---|
| `Shotgun(...)`, `connect=True` | calls `info()` once, through `server_caps` |
| `sg.server_caps` | `ServerCapabilities(host, info())`, cached per host. Raises `ShotgunError` when `version` is missing |
| `sg.server_caps.version` | `(8, 91, 0)`, a tuple of the first three items of `version` |
| `sg.server_caps.is_dev` | `False`. `True` only when `version[3] == "Dev"` |
| `sg.server_info` | the `info()` dict, equal to a fresh `info()` |
| `sg.connect()` | opens the connection, calls `info()`, returns `None` |
| `info()` with a wrong script name and key | the same payload: no auth is sent |
| `connect()` with a wrong script name and key | `None`, no error |
| `find_one` with a wrong script name and key | `AuthenticationFault: Can't authenticate script '<script>'` |

The client reads these keys:

| key | read by |
|---|---|
| `version` | `server_caps`: every version gate, and the JSON support check (needs 2.4.0 or later) |
| `api_max_entities_per_page` | `find` paging: records per page, `500` when absent |
| `s3_enabled_upload_types`, `s3_direct_uploads_enabled` | `upload`: whether a file goes to S3 directly |

**Same as REST:** nothing to compare. REST has no `info` call. `GET /` reports `api_version` of the
prefix, not the site version (finding 051).

**Differs from REST:** not comparable. `info()` answers without credentials. The corpus does not
record whether REST `GET /` answers without a token.

**Mock:** `sg_mockgun.Shotgun` has no `info`, `connect`, `server_info` or `server_caps`:
`AttributeError`. `sg-mockgun serve` answers `info` with
`{"version": [8, 91, 0], "s3_uploads_enabled": False, "totango_site_id": None}`. To change: add
`info()` returning the keys above, `full_version` with four items, and `api_max_entities_per_page`
5000 so a client pages as on the site. Add `connect()` returning `None`, and `server_info` and
`server_caps` built from `info()`. `serve` should answer `info` without checking credentials and
drop `totango_site_id`, which the site does not send.
