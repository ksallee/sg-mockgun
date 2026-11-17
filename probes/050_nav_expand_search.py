"""api3 050: nav_expand, nav_search_string and nav_search_entity: structure, the __none__ bucket, bad paths."""
import collections
import json

import _lib


def shape(answer, depth=1):
    """Keys of an answer and of its first children, plus the kinds and paths of its children."""
    if "ok" not in answer:
        return answer
    r = answer["ok"]
    if isinstance(r, list):
        return {"list_len": len(r), "first": r[:3]}
    if not isinstance(r, dict):
        return {"ok_type": type(r).__name__, "ok": r}
    kids = r.get("children") or []
    out = {"keys": sorted(r), "top": {k: v for k, v in r.items() if k != "children"}, "children": len(kids)}
    if kids:
        out["child_keys"] = sorted({tuple(sorted(c)) for c in kids})
        out["child_kinds"] = dict(collections.Counter((c.get("ref") or {}).get("kind") for c in kids))
        out["first_children"] = kids[:2]
        paths = [c.get("path") for c in kids]
        out["distinct_paths"] = len(set(paths))
        out["repeated_paths"] = [p for p, n in collections.Counter(paths).items() if n > 1][:3]
        out["repeat_identical"] = all(json.dumps(c, sort_keys=False) == json.dumps(next(d for d in kids if d.get("path") == c.get("path")))
                                      for c in kids)
    return out


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    projects = sg.find("Project", [["is_template", "is", False]], ["id"], limit=50)
    pid = None
    for p in projects:
        if sg.find_one("Shot", [["project", "is", p], ["sg_sequence", "is_not", None]]) and \
                sg.find_one("Sequence", [["project", "is", p]]):
            pid = p["id"]
            break
    shot = sg.find_one("Shot", [["project", "is", {"type": "Project", "id": pid}], ["sg_sequence", "is_not", None]],
                       ["code", "sg_sequence"])
    seq = shot["sg_sequence"]["id"]
    base = "/Project/%d" % pid
    ex = lambda path, **k: shape(_lib.ask(sg.nav_expand, path, **k))
    answers = {
        "root": ex("/"),
        "project": ex(base),
        "project_shot": ex(base + "/Shot"),
        "project_shot_again_identical": json.dumps(sg.nav_expand(base + "/Shot")) == json.dumps(sg.nav_expand(base + "/Shot")),
        "sequence_group": ex(base + "/Shot/sg_sequence/Sequence/%d" % seq),
        "bucket_expand_path": ex(base + "/Shot/sg_sequence/Sequence/__none__"),
        "bucket_search_spelling": ex(base + "/Shot/sg_sequence/__none__"),
        "project_asset": ex(base + "/Asset"),
        "entity_fields": ex(base + "/Shot/sg_sequence/Sequence/%d" % seq, entity_fields={"Shot": ["sg_status_list"]}),
        "seed_entity_field": ex(base + "/Shot", seed_entity_field="Shot.code"),
        "bad_missing_project": ex("/Project/999999999"),
        "bad_missing_project_shot": ex("/Project/999999999/Shot"),
        "bad_unknown_type": ex(base + "/Bogus"),
        "bad_plural": ex(base + "/shots"),
        "bad_no_leading_slash": ex("Project/%d" % pid),
        "bad_empty": ex(""),
        "bad_garbage": ex("/nope/nope/nope"),
        "bad_field": ex(base + "/Shot/sg_not_a_field/Sequence/1"),
        "search_string": shape(_lib.ask(sg.nav_search_string, base, shot["code"])),
        "search_string_shot_root": shape(_lib.ask(sg.nav_search_string, base + "/Shot", shot["code"])),
        "search_string_no_match": shape(_lib.ask(sg.nav_search_string, base, "zzprobe_no_such_name_050")),
        "search_string_short": shape(_lib.ask(sg.nav_search_string, base, "a")),
        "search_entity": shape(_lib.ask(sg.nav_search_entity, base, {"type": "Shot", "id": shot["id"]})),
        "search_entity_missing": shape(_lib.ask(sg.nav_search_entity, base, {"type": "Shot", "id": 999999999})),
        "search_entity_bogus_type": shape(_lib.ask(sg.nav_search_entity, base, {"type": "Bogus", "id": 1})),
        "search_bad_root": shape(_lib.ask(sg.nav_search_string, "/Project/999999999", "abc")),
        "search_garbage_root": shape(_lib.ask(sg.nav_search_string, "/nope", "abc")),
    }
    _lib.emit("050 nav_expand and nav_search", answers, env, sg)


if __name__ == "__main__":
    main()
