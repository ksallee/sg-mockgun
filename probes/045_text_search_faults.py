"""api3 045: the errors text_search() raises for a short or empty text, an unknown type and bad filters."""
import _lib


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    pid = [project["id"]]

    def ts(text, entity_types, **kw):
        """The error, or the terms and the match count per type."""
        kw.setdefault("project_ids", pid)
        r = _lib.ask(sg.text_search, text, entity_types, **kw)
        if "ok" not in r:
            return r
        per_type = {}
        for m in r["ok"]["matches"]:
            per_type[m["type"]] = per_type.get(m["type"], 0) + 1
        return {"terms": r["ok"]["terms"], "per_type": per_type}

    shot = {"Shot": []}
    answers = {
        "text ''": ts("", shot),
        "text '   '": ts("   ", shot),
        "text 'ab'": ts("ab", shot),
        "text 'ab cd'": ts("ab cd", shot),
        "text 'abc d'": ts("abc d", shot),
        "text ' ab '": ts(" ab ", shot),
        "text None": ts(None, shot),
        "text 123": ts(123, shot),
        "entity_types {}": ts("sbx", {}),
        "entity_types NotAType": ts("sbx", {"NotAType": []}),
        "entity_types NotAType with Shot": ts("sbx", {"Shot": [], "NotAType": []}),
        "entity_types a list": ts("sbx", ["Shot"]),
        "entity_types value a dict": ts("sbx", {"Shot": {"logical_operator": "and", "conditions": []}}),
        "entity_types value None": ts("sbx", {"Shot": None}),
        "filter field not on type": ts("sbx", {"Shot": [["sg_not_a_field", "is", "x"]]}),
        "filter operator nope": ts("sbx", {"Shot": [["code", "nope", "x"]]}),
        "filter not a triple": ts("sbx", {"Shot": [["code"]]}),
        "project_ids [0]": ts("sbx", shot, project_ids=[0]),
        "project_ids []": ts("sbx", shot, project_ids=[]),
        "project_ids None, Asset": ts("char", {"Asset": []}, project_ids=None),
        "project_ids sandbox, Asset": ts("char", {"Asset": []}),
        "project_ids a bare id": ts("sbx", shot, project_ids=project["id"]),
        "limit -1": ts("sbx", shot, limit=-1),
        "limit 'ten'": ts("sbx", shot, limit="ten"),
    }
    _lib.emit("045_text_search_faults", answers, env, sg)


if __name__ == "__main__":
    main()
