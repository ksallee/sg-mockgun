"""Shared reads for probes 070 to 073: Tasks on an entity, their edges, a one-line view of a Task."""
import time

TASK_FIELDS = ["content", "step", "entity", "project", "template_task", "task_template", "sg_status_list",
               "start_date", "due_date", "duration", "pinned", "dependency_violation",
               "upstream_tasks", "downstream_tasks"]
DEP_FIELDS = ["task", "dependent_task", "dependency_type", "offset_days"]

# Template "TT Seed · Shot live" (5 Tasks, 5 edges) and "TT Seed · Asset on Shot" (2 Tasks, 1 edge).
# Both exist on the site and are read only. Neither has assignees, so no apply notifies a person.
TEMPLATE_CODES = ("TT Seed · Shot live", "TT Seed · Asset on Shot")


def template(sg, code):
    tt = sg.find_one("TaskTemplate", [["code", "is", code]], ["code", "entity_type"])
    if not tt:
        raise SystemExit("no TaskTemplate named %r" % code)
    return tt


def template_tasks(sg, tt):
    return sg.find("Task", [["task_template", "is", tt]], ["content", "step"], order=[{"field_name": "id"}])


def tasks_on(sg, entity, settle=0.0):
    if settle:
        time.sleep(settle)
    return sg.find("Task", [["entity", "is", entity]], TASK_FIELDS, order=[{"field_name": "id"}])


def deps_among(sg, tasks):
    if not tasks:
        return []
    return sg.find("TaskDependency", [["task", "in", [{"type": "Task", "id": t["id"]} for t in tasks]]],
                   DEP_FIELDS, order=[{"field_name": "id"}])


def adopt(made, tasks):
    """Register server-made Tasks for deletion; skip ones already registered."""
    known = set(made.rows)
    for t in tasks:
        if ("Task", t["id"]) not in known:
            made.add({"type": "Task", "id": t["id"]})


def line(t):
    tt = (t.get("template_task") or {}).get("id")
    return "%-10s tmpl_task=%-6s status=%-4s %s..%s dur=%s pinned=%s viol=%s" % (
        t["content"], tt, t["sg_status_list"], t["start_date"], t["due_date"], t["duration"],
        t["pinned"], t["dependency_violation"])


def dep_line(d, names):
    return "%s on %s %s offset=%s" % (names.get(d["task"]["id"], d["task"]["id"]),
                                      names.get(d["dependent_task"]["id"], d["dependent_task"]["id"]),
                                      d["dependency_type"], d["offset_days"])
