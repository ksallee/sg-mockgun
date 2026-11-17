"""Pure Task Template rules: the Task a template task makes, the re-sync of a linked Task, the edge plan.

A template is a TaskTemplate row; its tasks are Task rows whose ``task_template`` links it, and its
edges are TaskDependency rows between them. Sources: api3 070, 071, findings 083, 084, 102, 105, 108.
"""

from .scheduling import Edge

# Task fields a template task never copies: links to the entity and the template, scheduling state,
# and fields the site sets itself.
_NOT_COPIED = frozenset([
    "project", "entity", "task_template", "template_task", "upstream_tasks", "downstream_tasks", "pinned",
    "dependency_violation", "cached_display_name", "color", "image", "filmstrip_image", "notes", "open_notes",
    "addressings_cc", "implicit", "splits", "sibling_tasks", "sg_versions",
])
_FILL_ONLY = frozenset(["start_date", "due_date", "task_assignees"])  # finding 102: kept when set
_KEPT = frozenset(["sg_status_list"])  # finding 102


def _link(value):
    if isinstance(value, dict) and "type" in value and "id" in value:
        return {"type": value["type"], "id": value["id"]}
    if isinstance(value, list):
        return [_link(v) for v in value]
    return value


def empty(value):
    """True for a value a template treats as unset: None, a checkbox's False, "" or []."""
    return value is None or value is False or value == "" or value == []


def copy_fields(task_schema):
    """The editable Task fields a template task copies onto a generated or linked Task."""
    return [f for f, info in task_schema.items() if info["editable"]["value"] and f not in _NOT_COPIED]


def new_task(template_task, fields, entity, project):
    """The create data of the Task ``template_task`` makes on ``entity`` (finding 083)."""
    data = {"project": _link(project), "entity": _link(entity),
            "template_task": {"type": "Task", "id": template_task["id"]}}
    for field in fields:
        if not empty(template_task.get(field)):
            data[field] = _link(template_task[field])
    return data


def resync(template_task, task, fields):
    """The fields a template write overwrites on a Task linked to ``template_task`` (finding 102).

    A set template value overwrites, a numeric 0 included. An empty one never clears. Status is kept.
    Dates and assignees fill only when empty. ``duration`` applies only to a Task with neither date.
    """
    changes = {}
    for field in fields:
        value = template_task.get(field)
        if field not in template_task or empty(value) or field in _KEPT:
            continue
        current = task.get(field)
        if field in _FILL_ONLY and not empty(current):
            continue
        if field == "duration" and (task.get("start_date") or task.get("due_date")):
            continue
        value = _link(value)
        if _link(current) != value:
            changes[field] = value
    return changes


def edge_plan(template_edges, linked, live_edges):
    """The edges a template write creates and erases among the Tasks linked to it (findings 102, 105, 107).

    ``template_edges`` are Edges between template task ids; ``linked`` maps a template task id to its
    Task id; ``live_edges`` are ``(row id, Edge)`` between Task ids. An edge the template has is created
    when missing and replaced when its type or offset differs, null and 0 apart. An edge the template
    lacks is erased when its downstream end is linked.
    """
    wanted = []
    for edge in template_edges:
        if edge.down in linked and edge.up in linked:
            wanted.append(Edge(linked[edge.down], linked[edge.up], edge.kind, edge.offset))
    by_pair = dict(((e.down, e.up), e) for e in wanted)
    targets = set(linked.values())
    kept, erase = set(), []
    for row_id, edge in live_edges:
        want = by_pair.get((edge.down, edge.up))
        if want is not None and (want.kind, want.offset) == (edge.kind, edge.offset):
            kept.add((edge.down, edge.up))
        elif want is not None or edge.down in targets:
            erase.append(row_id)
    return [e for e in wanted if (e.down, e.up) not in kept], erase
