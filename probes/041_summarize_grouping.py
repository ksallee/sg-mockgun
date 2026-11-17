"""api3 041: the nested structure summarize() returns for zero to three groupings, and each grouping type."""
import _lib


def outline(answer, keep=2):
    """The answer with entity names and ids replaced, and each level cut to its first `keep` groups."""
    if "ok" not in answer:
        return answer
    result = answer["ok"]

    def value(v):
        if isinstance(v, dict) and "id" in v:
            return dict(v, id="<id>", name="<name>" if "name" in v else v.get("name"))
        return v

    def level(groups):
        out = []
        for g in groups[:keep]:
            entity = isinstance(g.get("group_value"), dict)
            item = {"keys": sorted(g), "group_name": "<name>" if entity else g.get("group_name"),
                    "group_value": value(g.get("group_value")), "summaries": g.get("summaries")}
            if "groups" in g:
                item["groups"] = level(g["groups"])
                item["children"] = len(g["groups"])
                item["children_sum"] = sum(c["summaries"].get("id", 0) for c in g["groups"])
            out.append(item)
        return out

    groups = result.get("groups")
    if not isinstance(groups, list):
        return {"keys": sorted(result), "summaries": result.get("summaries"), "groups": groups}
    return {"keys": sorted(result), "summaries": result.get("summaries"), "group_count": len(groups),
            "groups": level(groups)}


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    on_project = [["project", "is", project]]
    count = [{"field": "id", "type": "count"}]

    def g(field, kind="exact", direction="asc"):
        return {"field": field, "type": kind, "direction": direction}

    answers = {
        "no grouping": outline(_lib.ask(sg.summarize, "Task", on_project, count)),
        "grouping []": outline(_lib.ask(sg.summarize, "Task", on_project, count, grouping=[])),
        "one: sg_status_list": outline(_lib.ask(sg.summarize, "Task", on_project, count, grouping=[g("sg_status_list")])),
        "one: step, two summaries": outline(_lib.ask(sg.summarize, 
            "Task", on_project, count + [{"field": "due_date", "type": "latest"}], grouping=[g("step")])),
        "two: entity, sg_status_list": outline(_lib.ask(sg.summarize, 
            "Task", on_project, count, grouping=[g("entity"), g("sg_status_list")])),
        "three: entity, step, sg_status_list": outline(_lib.ask(sg.summarize, 
            "Task", on_project, count, grouping=[g("entity"), g("step"), g("sg_status_list")])),
        "one: sg_status_list desc": outline(_lib.ask(sg.summarize, 
            "Task", on_project, count, grouping=[g("sg_status_list", direction="desc")]), keep=8),
        "one: sg_status_list asc": outline(_lib.ask(sg.summarize, 
            "Task", on_project, count, grouping=[g("sg_status_list")]), keep=8),
        "one: dotted entity.Shot.sg_sequence": outline(_lib.ask(sg.summarize, 
            "Task", on_project, count, grouping=[g("entity.Shot.sg_sequence")])),
        "one: due_date exact, with empties": outline(_lib.ask(sg.summarize, 
            "Task", on_project, count, grouping=[g("due_date")]), keep=3),
        "one: milestone (checkbox)": outline(_lib.ask(sg.summarize, "Task", on_project, count, grouping=[g("milestone")])),
        "no direction key": outline(_lib.ask(sg.summarize, 
            "Task", on_project, count, grouping=[{"field": "sg_status_list", "type": "exact"}])),
    }
    # each grouping type on a field it fits
    for kind in ("tens", "hundreds", "thousands", "tensofthousands", "hundredsofthousands", "millions"):
        answers["id " + kind] = outline(_lib.ask(sg.summarize, "Task", on_project, count, grouping=[g("id", kind)]))
    for kind in ("day", "week", "month", "quarter", "year", "clustered_date", "oneday", "fivedays"):
        answers["due_date " + kind] = outline(
            _lib.ask(sg.summarize, "Task", on_project, count, grouping=[g("due_date", kind)]), keep=3)
        answers["created_at " + kind] = outline(
            _lib.ask(sg.summarize, "Task", on_project, count, grouping=[g("created_at", kind)]), keep=2)
    answers["entity entitytype"] = outline(_lib.ask(sg.summarize, "Task", on_project, count, grouping=[g("entity", "entitytype")]), keep=4)
    answers["content firstletter"] = outline(_lib.ask(sg.summarize, "Task", on_project, count, grouping=[g("content", "firstletter")]), keep=3)
    _lib.emit("041_summarize_grouping", answers, env, sg)


if __name__ == "__main__":
    main()
