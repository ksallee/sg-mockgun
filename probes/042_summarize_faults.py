"""api3 042: the Faults summarize() raises for a bad summary type, a bad field, a bad grouping and bad arguments."""
import _lib


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    on_project = [["project", "is", project]]
    count = [{"field": "id", "type": "count"}]

    def s(summaries, grouping=None, entity_type="Task", filters=None):
        return _lib.ask(sg.summarize, entity_type, on_project if filters is None else filters, summaries, grouping=grouping)

    def g(field, kind):
        return [{"field": field, "type": kind, "direction": "asc"}]

    answers = {
        "summary type nope": s([{"field": "id", "type": "nope"}]),
        "summary type missing": s([{"field": "id"}]),
        "summary field missing": s([{"type": "count"}]),
        "summary field not on type": s([{"field": "sg_not_a_field", "type": "count"}]),
        "summary field dotted": s([{"field": "entity.Shot.code", "type": "count"}]),
        "summary_fields not a list": _lib.ask(sg.summarize, "Task", on_project, {"field": "id", "type": "count"}),
        "entity type nope": s(count, entity_type="NotAType"),
        "filter on a field not on type": s(count, filters=[["sg_not_a_field", "is", 1]]),
        "grouping type nope": s(count, g("sg_status_list", "nope")),
        "grouping field not on type": s(count, g("sg_not_a_field", "exact")),
        "grouping direction sideways": s(count, [{"field": "sg_status_list", "type": "exact", "direction": "up"}]),
        "grouping not a list": _lib.ask(sg.summarize, "Task", on_project, count,
                                        grouping={"field": "sg_status_list", "type": "exact", "direction": "asc"}),
    }
    # The valid grouping types per data type, read off the Fault a wrong type raises.
    for field, data_type in (("id", "number"), ("est_in_mins", "duration"), ("time_percent_of_est", "percent"),
                             ("content", "text"), ("entity", "entity"), ("step", "entity"), ("milestone", "checkbox"),
                             ("sg_status_list", "status_list"), ("sg_priority_1", "list"),
                             ("task_assignees", "multi_entity")):
        answers["grouping %s (%s) millions-or-day" % (field, data_type)] = s(
            count, g(field, "day" if data_type in ("number", "duration", "percent") else "millions"))
    for field, data_type in (("est_in_mins", "duration"), ("duration", "duration")):
        for kind in ("oneday", "fivedays"):
            answers["grouping %s (%s) %s" % (field, data_type, kind)] = s(count, g(field, kind))
    _lib.emit("042_summarize_faults", answers, env, sg)


if __name__ == "__main__":
    main()
