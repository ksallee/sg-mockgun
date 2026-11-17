"""api3 048: activity_stream_read on a Shot and a Version: structure, limit, min_id, max_id, bad inputs."""
import _lib


def summary(answer):
    """Envelope keys, counts and ids of an activity_stream_read answer, or the raised error."""
    if "ok" not in answer:
        return answer
    r = answer["ok"]
    if not isinstance(r, dict):
        return {"ok_type": type(r).__name__, "ok": r}
    ups = r.get("updates") or []
    return {
        "keys": sorted(r),
        "entity_type": r.get("entity_type"),
        "updates": len(ups),
        "ids": [u.get("id") for u in ups][:8],
        "earliest_update_id": r.get("earliest_update_id"),
        "latest_update_id": r.get("latest_update_id"),
    }


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    version = sg.find_one("Version", [["entity", "type_is", "Shot"]], ["entity"],
                          order=[{"field_name": "id", "direction": "desc"}])
    shot_id, version_id = version["entity"]["id"], version["id"]
    project_id = sg.find_one("Version", [["id", "is", version_id]], ["project"])["project"]["id"]
    ask = lambda *a, **k: summary(_lib.ask(sg.activity_stream_read, *a, **k))
    full = sg.activity_stream_read("Shot", shot_id, limit=500)
    ups = full["updates"]
    by_type = {}
    for u in ups:
        by_type.setdefault(u.get("update_type"), u)
    mid = ups[len(ups) // 2]["id"] if ups else 1
    answers = {
        "shot_default": ask("Shot", shot_id),
        "shot_limit_500_envelope": summary({"ok": full}),
        "update_types": sorted(by_type),
        "update_keys_by_type": {t: sorted(u) for t, u in by_type.items()},
        "meta_keys_by_type": {t: sorted(u.get("meta") or {}) for t, u in by_type.items()},
        "primary_entity_keys": sorted(ups[0].get("primary_entity") or {}) if ups else None,
        "created_by_keys": sorted(ups[0].get("created_by") or {}) if ups else None,
        "created_at_python_type": type(ups[0].get("created_at")).__name__ if ups else None,
        "read_values": sorted({str(u.get("read")) for u in ups}),
        "ids_descending": all(ups[i]["id"] > ups[i + 1]["id"] for i in range(len(ups) - 1)),
        "limit_3": ask("Shot", shot_id, limit=3),
        "limit_0": ask("Shot", shot_id, limit=0),
        "limit_501": ask("Shot", shot_id, limit=501),
        "limit_negative": ask("Shot", shot_id, limit=-1),
        "max_id_mid_limit_3": ask("Shot", shot_id, max_id=mid, limit=3),
        "min_id_mid": ask("Shot", shot_id, min_id=mid, limit=500),
        "mid": mid,
        "min_id_above_newest": ask("Shot", shot_id, min_id=(ups[0]["id"] if ups else 0) + 10**7),
        "entity_fields_version": summary(_lib.ask(sg.activity_stream_read, "Shot", shot_id, limit=500,
                                                  entity_fields={"Version": ["sg_status_list", "entity"], "Task": ["content"]})),
        "entity_fields_widened_keys": sorted({k for u in sg.activity_stream_read("Shot", shot_id, limit=500,
                                                entity_fields={"Version": ["sg_status_list", "entity"]})["updates"]
                                              if (u.get("primary_entity") or {}).get("type") == "Version"
                                              for k in u["primary_entity"]}),
        "entity_fields_unknown_field": ask("Shot", shot_id, limit=3, entity_fields={"Shot": ["sg_not_a_field"]}),
        "version": ask("Version", version_id),
        "project_default": ask("Project", project_id),
        "project_limit_0": ask("Project", project_id, limit=0),
        "project_limit_500": ask("Project", project_id, limit=500),
        "project_limit_501": ask("Project", project_id, limit=501),
        "project_limit_2000": ask("Project", project_id, limit=2000),
        "missing_shot": _lib.ask(sg.activity_stream_read, "Shot", 999999999),
        "missing_version": _lib.ask(sg.activity_stream_read, "Version", 999999999),
        "unknown_type": _lib.ask(sg.activity_stream_read, "Bogus", 1),
        "plural_type": _lib.ask(sg.activity_stream_read, "shots", shot_id),
        "id_string": _lib.ask(sg.activity_stream_read, "Shot", "abc"),
        "id_zero": _lib.ask(sg.activity_stream_read, "Shot", 0),
        "entity_fields_list": _lib.ask(sg.activity_stream_read, "Shot", shot_id, entity_fields=["code"]),
        "raw_missing_shot_rpc": _lib.ask(sg._call_rpc, "activity_stream",
                                         {"type": "Shot", "id": 999999999, "max_id": None, "min_id": None,
                                          "limit": None, "entity_fields": {}}),
    }
    _lib.emit("048 activity_stream_read", answers, env, sg)


if __name__ == "__main__":
    main()
