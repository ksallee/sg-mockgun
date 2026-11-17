"""api3 040: what summarize() returns for each summary type, with no grouping, over the sandbox project."""
import datetime

import _lib

# (entity type, field, data type) per summary type the client docstring lists, plus the REST-only one.
CASES = [
    ("Task", "id", "number", "record_count"),
    ("Task", "id", "number", "count"),
    ("Task", "due_date", "date", "count"),
    ("Task", "est_in_mins", "duration", "sum"),
    ("Task", "est_in_mins", "duration", "maximum"),
    ("Task", "est_in_mins", "duration", "minimum"),
    ("Task", "est_in_mins", "duration", "average"),
    ("Shot", "cut_duration", "number", "sum"),
    ("Shot", "cut_duration", "number", "average"),
    ("Version", "sg_movie_aspect_ratio", "float", "average"),
    ("Version", "sg_movie_aspect_ratio", "float", "maximum"),
    ("Task", "due_date", "date", "earliest"),
    ("Task", "due_date", "date", "latest"),
    ("Task", "created_at", "date_time", "earliest"),
    ("Task", "created_at", "date_time", "latest"),
    ("Task", "milestone", "checkbox", "checked"),
    ("Task", "milestone", "checkbox", "unchecked"),
    ("Task", "milestone", "checkbox", "percentage"),
    ("Task", "time_percent_of_est", "percent", "average"),
    ("Task", "time_percent_of_est", "percent", "percentage"),
    ("Task", "sg_status_list", "status_list", "status_percentage"),
    ("Task", "sg_status_list", "status_list", "status_percentage_as_float"),
    ("Task", "sg_status_list", "status_list", "status_list"),
    ("Task", "sg_status_list", "status_list", "count"),
    ("Task", "content", "text", "count"),
    ("Task", "entity", "entity", "count"),
    ("Task", "entity", "entity", "record_count"),
    ("Task", "task_assignees", "multi_entity", "count"),
    ("Task", "due_date", "date", "sum"),
    ("Task", "created_at", "date_time", "average"),
    ("Task", "content", "text", "earliest"),
    ("Task", "sg_status_list", "status_list", "record_count"),
]


def typed(answer):
    """The answer with the Python type of each summary value next to it."""
    if "ok" not in answer:
        return answer
    out = dict(answer["ok"])
    out["value_types"] = {k: type(v).__name__ for k, v in out["summaries"].items()}
    for k, v in out["summaries"].items():
        if isinstance(v, datetime.datetime):
            out["summaries"][k] = "datetime tzinfo=%s" % (v.tzinfo is not None)
    return out


def main():
    env = _lib.load_env()
    sg = _lib.client(env)
    project = _lib.sandbox(sg, env)
    on_project = [["project", "is", project]]
    answers = {}
    for entity_type, field, data_type, kind in CASES:
        key = "%s.%s (%s) %s" % (entity_type, field, data_type, kind)
        answers[key] = typed(_lib.ask(sg.summarize, entity_type, on_project, [{"field": field, "type": kind}]))
    # two fields in one call; two types on one field (finding 020: the last wins)
    answers["two fields"] = _lib.ask(sg.summarize, "Task", on_project, [
        {"field": "id", "type": "count"}, {"field": "due_date", "type": "latest"}])
    answers["id count then id maximum"] = _lib.ask(sg.summarize, "Task", on_project, [
        {"field": "id", "type": "count"}, {"field": "id", "type": "maximum"}])
    answers["id count then id count"] = _lib.ask(sg.summarize, "Task", on_project, [
        {"field": "id", "type": "count"}, {"field": "id", "type": "count"}])
    for value in ("fin", "ip", "hld", "wtg", "zzz_not_a_status"):
        for kind in ("status_percentage", "status_percentage_as_float"):
            answers["sg_status_list %s value %s" % (kind, value)] = typed(_lib.ask(
                sg.summarize, "Task", on_project, [{"field": "sg_status_list", "type": kind, "value": value}]))
    answers["status grouping counts, for the share"] = _lib.ask(
        sg.summarize, "Task", on_project, [{"field": "id", "type": "count"}],
        grouping=[{"field": "sg_status_list", "type": "exact", "direction": "asc"}])
    answers["empty summary_fields"] = _lib.ask(sg.summarize, "Task", on_project, [])
    answers["no row matches"] = _lib.ask(sg.summarize, "Task", on_project + [["id", "is", 0]], [
        {"field": "id", "type": "count"}, {"field": "due_date", "type": "latest"},
        {"field": "est_in_mins", "type": "average"}, {"field": "sg_status_list", "type": "status_list"}])
    answers["filter_operator any"] = _lib.ask(sg.summarize, "Task", on_project + [["id", "is", 0]], [
        {"field": "id", "type": "count"}], filter_operator="any")
    answers["dict filters"] = _lib.ask(sg.summarize, "Task", {"filter_operator": "all", "filters": on_project}, [
        {"field": "id", "type": "count"}])
    answers["include_archived_projects False"] = _lib.ask(sg.summarize, "Task", on_project, [
        {"field": "id", "type": "count"}], include_archived_projects=False)
    _lib.emit("040_summarize_types", answers, env, sg)


if __name__ == "__main__":
    main()
