# 051 preferences_read, work_schedule_read, user_subscriptions_read

re-asks: finding 047
measured: Flow PT 8.91.0, shotgun_api3 3.10.5, read only
probe: probes/051_site_reads.py

**Q** What do the three site reads return? No preference, work schedule or subscription write is sent.

| method | RPC and params | returns |
|---|---|---|
| `preferences_read(prefs=None)` | `preferences_read`, `{"prefs": prefs or []}` | the RPC answer, a dict |
| `work_schedule_read(start, end, project=None, user=None)` | `work_schedule_read`, `{start_date, end_date, project, user}` | the RPC answer, a dict. Non-string dates raise `ShotgunError` before the call. |
| `user_subscriptions_read()` | `user_subscriptions_read`, `None` | the RPC answer, a dict. The docstring says a list. |

| call | answer |
|---|---|
| `preferences_read()` | dict of 17: `creative_review_settings, date_component_order, duration_units, enable_rv_integration, enable_shotgun_review_for_rv, format_currency_fields_decimal_options, format_currency_fields_display_dollar_sign, format_currency_fields_negative_options, format_date_fields, format_float_fields, format_float_fields_rounding, format_footage_fields, format_number_fields, format_time_hour_fields, hours_per_day, support_local_storage, view_master_settings` |
| value types | `bool`: `enable_rv_integration, enable_shotgun_review_for_rv, format_currency_fields_display_dollar_sign, support_local_storage`. `float`: `hours_per_day`. `str`: the rest. |
| `preferences_read(["creative_review_settings", "date_component_order"])` | those two keys only |
| `preferences_read(["zzprobe_not_a_pref"])` | `{}` |
| `preferences_read("format_date_fields")` | Fault `API preferences_read() 'prefs' must be an array.` |
| `work_schedule_read("2026-03-02", "2026-03-15")` | dict of 14, keyed `YYYY-MM-DD`, each `{working, description, reason}` |
| a weekday, a weekend day | `{"working": true, "description": null, "reason": "STUDIO_WORK_WEEK"}`, `working` false on Saturday and Sunday |
| a 730-day window | 730 keys |
| `project=` or `user=` with id 999999999 | 7 rows, `STUDIO_WORK_WEEK`, no error |
| `project=` or `user=` that exists | 7 rows, `STUDIO_WORK_WEEK` |
| end before start | Fault `API work_schedule_read() 'end_date' must be greater than or equal to 'start_date':` + the params |
| `"03/02/2026"` or `"nope"` | Fault `API work_schedule_read() invalid format for 'start_date'. Valid format 'YYYY-MM-DD':` + the params |
| a `datetime.date` | `ShotgunError: The start_date and end_date arguments must be strings in YYYY-MM-DD format` (client side) |
| `user_subscriptions_read()` | dict of 17. Keys are HumanUser ids as strings. Values `"not_for_resale"` or `None`. |

The params in a Fault print as a Ruby hash, one key per line: `{"start_date" => "2026-03-15",\n "end_date" => "2026-03-02",\n "project" => nil,\n "user" => nil}`.

**Same as REST:** the subscription answer is a bare hash keyed by user id string. A work-schedule scope id that does not exist answers the studio default. No paging on a long window. Reversed and badly formatted dates are refused.
**Differs from REST:** `work_schedule_read` returns a dict keyed by date, where REST returns a JSON:API `data` list. A bad date is a Fault with the params, where REST has two error shapes. REST has no preferences read in finding 047.
**Mock:** `sg_mockgun.Shotgun` has none of the three: `AttributeError`. Over the wire, Fault `Error: API method "preferences_read" is not permitted.` Needed: a seeded preferences dict filtered by `prefs`, a work week from Monday to Friday with `STUDIO_WORK_WEEK` and the two Faults, and a subscriptions dict keyed by user id strings.
