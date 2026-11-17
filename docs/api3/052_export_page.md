# 052 export_page

re-asks: finding 048, finding 072
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/052_export_page.py

**Q** What does `export_page` answer on pages the script can read?

The method sends RPC `export_page` with `{format, page_id, layout_name}` and returns the RPC answer, a string on success. No page on the site is marked exportable, so no success was seen.

| call | answer |
|---|---|
| `export_page(<page>, "csv")` on 20 pages, `detail`, `canvas`, `focus`, `home` | Fault `Export for Page id=<page> not available` on all 20 |
| `layout_name="layout_0"`, `layout_name="zzprobe_052_not_a_view"` | the same Fault |
| format `"json"`, `"bogus"` | the same Fault |
| format `None` | Fault `API export_page() 'format' missing:` + `{"format" => nil, "page_id" => <page>, "layout_name" => nil}` |
| `export_page(999999999, "csv")` | Fault `Trying to perform export for retired Page id=999999999` |
| `export_page(0, "csv")`, `export_page("abc", "csv")` | Fault `API export_page() invalid 'page_id':` + the params |
| `export_page(None, "csv")` | Fault `API export_page() 'page_id' missing:` + the params |

Skipped: `update_project_last_accessed`. It writes a Project's last-accessed stamp for a user.

**Same as REST:** the not-available message and the retired-page message, word for word. Format and layout name are not checked before the exportable check.
**Differs from REST:** a non-numeric or zero `page_id` is refused as invalid, where REST reads `abc` as `id=0` and answers the retired-page 422. A missing format is a Fault, where REST drops the route.
**Mock:** `sg_mockgun.Shotgun` has no `export_page`: `AttributeError`. Over the wire, Fault `Error: API method "export_page" is not permitted.` Needed: `export_page` answering Fault `Export for Page id=<id> not available` for a Page row, the retired-page Fault for a missing id, and the three parameter Faults.
