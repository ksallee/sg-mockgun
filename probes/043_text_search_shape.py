"""api3 043: the structure text_search() returns for one and several entity types, with and without a filter."""
import _lib


def outline(answer, keep=3):
    """The answer with names and ids replaced: keys, value types, the links pair and the per-type counts."""
    if "ok" not in answer:
        return answer
    result = answer["ok"]
    matches = result.get("matches") or []
    rows = []
    for m in matches[:keep]:
        links = m.get("links")
        rows.append({
            "keys": sorted(m),
            "types": {k: type(v).__name__ for k, v in sorted(m.items())},
            "type": m.get("type"),
            "status": m.get("status"),
            "links": [links[0], "<name>" if links[1] else ""] if isinstance(links, list) and len(links) == 2 else links,
        })
    per_type = {}
    for m in matches:
        per_type[m["type"]] = per_type.get(m["type"], 0) + 1
    return {"keys": sorted(result), "terms": result.get("terms"), "match_count": len(matches),
            "per_type": per_type, "first": rows}


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    pid = [project["id"]]
    on_project = [["project", "is", project]]

    def ts(text, entity_types, **kw):
        return outline(_lib.ask(sg.text_search, text, entity_types, **kw))

    answers = {
        "one type, no filter, project_ids": ts("sbx", {"Shot": []}, project_ids=pid),
        "one type, filter, no project_ids": ts("sbx", {"Shot": on_project}),
        "three types, no filter": ts("sbx", {"Shot": [], "Asset": [], "Version": []}, project_ids=pid),
        "three types, filter on one": ts("sbx", {"Shot": [["code", "is", "sbx_0020"]], "Asset": [], "Version": []},
                                         project_ids=pid),
        "Task, links to its entity": ts("sbx", {"Task": []}, project_ids=pid),
        "two words": ts("sbx 0020", {"Shot": [], "Version": []}, project_ids=pid),
        "filter matches nothing": ts("sbx", {"Shot": [["id", "is", 0]]}, project_ids=pid),
        "text matches nothing": ts("zzznotaword", {"Shot": []}, project_ids=pid),
        "tuple filter": ts("sbx", {"Shot": tuple(on_project)}),
        "two conditions": ts("sbx", {"Shot": on_project + [["code", "starts_with", "sbx_00"]]}),
    }
    # How many rows come back with and without limit (REST pages at 25, finding 053).
    for limit in (None, 0, 1, 25, 26, 100, 1000):
        answers["limit %s" % limit] = {k: v for k, v in ts(
            "sbx", {"Shot": [], "Asset": [], "Version": [], "Task": []}, project_ids=pid, limit=limit).items()
            if k in ("match_count", "per_type", "raised", "message")}
    # Order (finding 053: shortest name first, across types). Each row: type, name length, whether its
    # own name holds the text, the linked type.
    raw = _lib.ask(sg.text_search, "sbx", {"Shot": [], "Asset": [], "Version": [], "Task": []},
                   project_ids=pid, limit=100)
    if "ok" in raw:
        answers["order"] = ["%s %d %s %s" % (m["type"], len(m["name"]), "own" if "sbx" in m["name"].lower() else "link",
                                             m["links"][0] or "-") for m in raw["ok"]["matches"]]
    _lib.emit("043_text_search_shape", answers, env, sg)


if __name__ == "__main__":
    main()
