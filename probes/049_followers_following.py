"""api3 049: followers on an entity and following for a user. Structure only, no follow or unfollow."""
import collections

import _lib


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    users = sg.find("HumanUser", [["sg_status_list", "is", "act"]], ["id"], limit=10)
    best = max(users, key=lambda u: len(sg.following({"type": "HumanUser", "id": u["id"]})))
    user = {"type": "HumanUser", "id": best["id"]}
    rows = sg.following(user)
    types = collections.Counter(r.get("type") for r in rows)
    target = next((r for r in rows if r.get("type") == "Task"), rows[0] if rows else None)
    task = sg.find_one("Task", [["id", "is", target["id"]]], ["project"]) if target and target["type"] == "Task" else None
    project = task["project"] if task else None
    fol = sg.followers({"type": target["type"], "id": target["id"]}) if target else []
    answers = {
        "following_len": len(rows),
        "following_types": dict(types),
        "following_row_keys": sorted({tuple(sorted(r)) for r in rows}),
        "following_entity_type_Task": len(sg.following(user, entity_type="Task")),
        "following_entity_type_plural": _lib.ask(lambda: len(sg.following(user, entity_type="tasks"))),
        "following_entity_type_bogus": _lib.ask(sg.following, user, entity_type="Bogus"),
        "following_project": _lib.ask(lambda: len(sg.following(user, project=project))) if project else None,
        "following_project_and_type": _lib.ask(lambda: len(sg.following(user, project=project, entity_type="Task"))) if project else None,
        "following_missing_project": _lib.ask(sg.following, user, project={"type": "Project", "id": 999999999}),
        "following_missing_user": _lib.ask(sg.following, {"type": "HumanUser", "id": 999999999}),
        "following_api_user": _lib.ask(sg.following, {"type": "ApiUser", "id": 1}),
        "following_user_as_Shot": _lib.ask(sg.following, {"type": "Shot", "id": 1}),
        "followers_of": target["type"] if target else None,
        "followers_len": len(fol),
        "followers_row_keys": sorted({tuple(sorted(r)) for r in fol}),
        "followers_value_types": {k: type(v).__name__ for k, v in (fol[0].items() if fol else [])},
        "followers_status_valid_values": sorted({(str(r.get("status")), str(r.get("valid"))) for r in fol}),
        "followers_missing_row": _lib.ask(sg.followers, {"type": "Shot", "id": 999999999}),
        "followers_unknown_type": _lib.ask(sg.followers, {"type": "Bogus", "id": 1}),
        "followers_plural_type": _lib.ask(sg.followers, {"type": "shots", "id": 1}),
        "followers_no_id": _lib.ask(sg.followers, {"type": "Shot"}),
    }
    _lib.emit("049 followers and following", answers, env, sg)


if __name__ == "__main__":
    main()
