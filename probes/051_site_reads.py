"""api3 051: preferences_read, work_schedule_read and user_subscriptions_read. Structure only, no writes."""
import collections

import _lib


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    prefs = sg.preferences_read()
    week = sg.work_schedule_read("2026-03-02", "2026-03-15")
    subs = sg.user_subscriptions_read()
    some = sorted(prefs)[:2]
    project = sg.find_one("Project", [], ["id"])
    user = sg.find_one("HumanUser", [], ["id"])
    answers = {
        "preferences_type": type(prefs).__name__,
        "preferences_keys": sorted(prefs),
        "preferences_value_types": {k: type(v).__name__ for k, v in sorted(prefs.items())},
        "preferences_named": _lib.ask(lambda: sorted(sg.preferences_read(some))),
        "preferences_unknown_name": _lib.ask(sg.preferences_read, ["zzprobe_not_a_pref"]),
        "preferences_string_arg": _lib.ask(lambda: sorted(sg.preferences_read("format_date_fields"))),
        "work_schedule_type": type(week).__name__,
        "work_schedule_len": len(week),
        "work_schedule_keys_first_last": [min(week), max(week)] if isinstance(week, dict) else None,
        "work_schedule_rule_keys": sorted({tuple(sorted(v)) for v in week.values()}) if isinstance(week, dict) else None,
        "work_schedule_rows": {k: week[k] for k in sorted(week)[:7]} if isinstance(week, dict) else week,
        "work_schedule_reasons": dict(collections.Counter(v.get("reason") for v in week.values())),
        "ws_missing_project": _lib.ask(lambda: collections.Counter(v["reason"] for v in sg.work_schedule_read(
            "2026-03-02", "2026-03-08", project={"type": "Project", "id": 999999999}).values())),
        "ws_missing_user": _lib.ask(lambda: collections.Counter(v["reason"] for v in sg.work_schedule_read(
            "2026-03-02", "2026-03-08", user={"type": "HumanUser", "id": 999999999}).values())),
        "ws_project": _lib.ask(lambda: collections.Counter(v["reason"] for v in sg.work_schedule_read(
            "2026-03-02", "2026-03-08", project={"type": "Project", "id": project["id"]}).values())),
        "ws_user": _lib.ask(lambda: collections.Counter(v["reason"] for v in sg.work_schedule_read(
            "2026-03-02", "2026-03-08", user={"type": "HumanUser", "id": user["id"]}).values())),
        "ws_reversed": _lib.ask(sg.work_schedule_read, "2026-03-15", "2026-03-02"),
        "ws_bad_format": _lib.ask(sg.work_schedule_read, "03/02/2026", "03/15/2026"),
        "ws_not_a_date": _lib.ask(sg.work_schedule_read, "nope", "2026-03-15"),
        "ws_date_object": _lib.ask(sg.work_schedule_read, __import__("datetime").date(2026, 3, 2), "2026-03-15"),
        "ws_730_days_len": _lib.ask(lambda: len(sg.work_schedule_read("2026-01-01", "2027-12-31"))),
        "subscriptions_type": type(subs).__name__,
        "subscriptions_len": len(subs),
        "subscriptions_key_types": sorted({type(k).__name__ for k in subs}) if isinstance(subs, dict) else None,
        "subscriptions_value_types": sorted({type(v).__name__ for v in subs.values()}) if isinstance(subs, dict) else None,
        "subscriptions_values": sorted({str(v) for v in subs.values()}) if isinstance(subs, dict) else None,
        "subscriptions_keys_are_user_ids": all(str(k).isdigit() for k in subs) if isinstance(subs, dict) else None,
    }
    _lib.emit("051 site reads", answers, env, sg)


if __name__ == "__main__":
    main()
